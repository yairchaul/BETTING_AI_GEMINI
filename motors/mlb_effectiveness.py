# -*- coding: utf-8 -*-
"""
EffectivenessCalculator — calcula métricas de efectividad por tipo de pick
y por equipo a partir de la tabla `backtesting`, tras la auditoría.

Diseño: .kiro/specs/backtesting-real-mlb/design.md (Componente 3)
Requisitos: 3.1, 3.2 (esta tarea); 3.3..3.9 en Task 6.2.

Esta tarea (6.1) implementa el cómputo:
  - compute_by_pick_type(dias) -> dict[PickType, Metrics]
  - compute_by_team(dias) -> dict[str, Metrics]

Reglas de cálculo (consistentes con mlb_real_backtester.py):
  - hits = picks GANADA
  - profit por pick: GANADA -> (cuota - 1.0); PERDIDA -> -1.0
  - win_rate = hits/total * 100
  - roi = profit/total * 100
  - last_10: lista de 'W'/'L' del más reciente al más antiguo
"""
from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from motors.mlb_backtest_models import Classification, Metrics, PickType
from motors.mlb_backtest_auditor import (
    MLBBacktestAuditor,
    FUZZY_HIGH_THRESHOLD,
    _fuzzy_score,
    _safe_normalize,
)

logger = logging.getLogger(__name__)


def _empty_metrics() -> Metrics:
    return Metrics(total=0, hits=0, win_rate=0.0, profit=0.0, roi=0.0, last_10=[])


def _build_metrics(rows: List[Tuple[str, Optional[float]]]) -> Metrics:
    """
    Construye un Metrics a partir de filas (estado, cuota) ordenadas
    de MÁS RECIENTE A MÁS ANTIGUO. Solo cuenta filas con estado terminal.

    rows: lista de tuplas (estado, cuota). estado ∈ {GANADA, PERDIDA}.
    """
    total = 0
    hits = 0
    profit = 0.0
    last_10: List[str] = []

    for estado, cuota in rows:
        if estado not in ("GANADA", "PERDIDA"):
            continue
        total += 1
        if estado == "GANADA":
            hits += 1
            # Default cuota si por algún motivo viene None/0:
            try:
                c = float(cuota) if (cuota is not None and float(cuota) > 0) else 1.90
            except (TypeError, ValueError):
                c = 1.90
            profit += (c - 1.0)
            if len(last_10) < 10:
                last_10.append('W')
        else:
            profit -= 1.0
            if len(last_10) < 10:
                last_10.append('L')

    if total == 0:
        return _empty_metrics()
    win_rate = hits / total * 100.0
    roi = profit / total * 100.0
    return Metrics(
        total=total,
        hits=hits,
        win_rate=win_rate,
        profit=profit,
        roi=roi,
        last_10=last_10,
    )


def _split_evento(evento: str) -> List[str]:
    """
    Divide un string de evento ("Away vs Home" o "Away @ Home") en sus dos
    equipos. Si no se puede dividir, retorna [].

    Acepta: " vs ", " VS ", " @ ", " - ".
    """
    if not evento:
        return []
    parts = re.split(r'\s+(?:vs|VS|@|-)\s+', evento.strip(), maxsplit=1)
    if len(parts) != 2:
        return []
    a, b = parts[0].strip(), parts[1].strip()
    if not a or not b:
        return []
    return [a, b]


class EffectivenessCalculator:
    """
    Calcula métricas de efectividad sobre la tabla `backtesting`.

    No persiste nada en Task 6.1; la persistencia llega en 6.2/9.2.
    """

    def __init__(
        self,
        db=None,
        cache_dir: str = "data/backtesting_cache",
        auditor: Optional[MLBBacktestAuditor] = None,
    ):
        self.db = db
        self.cache_dir = cache_dir
        # Reutilizamos el auditor para classify_pick (consistencia 100% con la auditoría).
        self._auditor = auditor or MLBBacktestAuditor(db=db)
        # Caché interno de los resultados del último compute_*.
        self._last_pick_type_metrics: Dict[PickType, Metrics] = {}
        self._last_team_metrics: Dict[str, Metrics] = {}

    # ------------------------------------------------------------------
    # compute_by_pick_type — Requirements 3.1, 3.2
    # ------------------------------------------------------------------
    def compute_by_pick_type(self, dias: int = 15) -> Dict[PickType, Metrics]:
        """
        Calcula Metrics por PickType para los últimos N días de la tabla
        `backtesting` (deporte='MLB', estado terminal). Las filas se agrupan
        usando el mismo `classify_pick` del auditor para garantizar que las
        métricas reflejan exactamente lo que se auditó.

        Returns:
            Dict[PickType, Metrics]. Si no hay picks, devuelve un dict vacío.
        """
        if self.db is None:
            return {}
        cutoff = (datetime.now() - timedelta(days=dias)).strftime("%Y-%m-%d")

        # Agrupamos en memoria: {PickType: list[(estado, cuota)]}, conservando
        # el orden de fecha desc + id desc (más reciente primero).
        grouped: Dict[PickType, List[Tuple[str, Optional[float]]]] = {}
        try:
            conn = self.db._connect()
            try:
                cur = conn.cursor()
                cur.execute(
                    "SELECT pick, estado, cuota "
                    "FROM backtesting "
                    "WHERE deporte = 'MLB' "
                    "  AND estado IN ('GANADA', 'PERDIDA') "
                    "  AND fecha >= ? "
                    "ORDER BY fecha DESC, id DESC",
                    (cutoff,),
                )
                rows = cur.fetchall()
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"[compute_by_pick_type] DB error: {e}")
            return {}

        for pick_text, estado, cuota in rows:
            tipo = self._auditor.classify_pick(pick_text or "")
            grouped.setdefault(tipo, []).append((estado, cuota))

        result: Dict[PickType, Metrics] = {
            tipo: _build_metrics(filas) for tipo, filas in grouped.items()
        }
        self._last_pick_type_metrics = result
        return result

    # ------------------------------------------------------------------
    # compute_by_team — Requirements 3.1, 3.2
    # ------------------------------------------------------------------
    def compute_by_team(self, dias: int = 15) -> Dict[str, Metrics]:
        """
        Calcula Metrics por equipo MLB en los últimos N días. La asignación
        de "equipo" usa el campo `evento` (formato esperado: "Away vs Home")
        y compara fuzzy contra el texto del pick para identificar a qué
        equipo se refiere.

        Implementación pragmática: si el pick referencia con fuzzy>=85% al
        home, contabilizamos al home; si referencia al away, contabilizamos
        al away; si no se puede determinar, contabilizamos a AMBOS equipos
        del evento (ej: Over/Under sin equipo) — esto refleja "el partido
        rindió bien para mi sistema" más que "el equipo X rindió bien".

        Returns:
            Dict[equipo_normalizado, Metrics].
        """
        if self.db is None:
            return {}
        cutoff = (datetime.now() - timedelta(days=dias)).strftime("%Y-%m-%d")

        try:
            conn = self.db._connect()
            try:
                cur = conn.cursor()
                cur.execute(
                    "SELECT evento, pick, estado, cuota "
                    "FROM backtesting "
                    "WHERE deporte = 'MLB' "
                    "  AND estado IN ('GANADA', 'PERDIDA') "
                    "  AND fecha >= ? "
                    "ORDER BY fecha DESC, id DESC",
                    (cutoff,),
                )
                rows = cur.fetchall()
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"[compute_by_team] DB error: {e}")
            return {}

        grouped: Dict[str, List[Tuple[str, Optional[float]]]] = {}

        for evento, pick_text, estado, cuota in rows:
            evento = evento or ""
            pick_text = pick_text or ""
            equipos_evento = _split_evento(evento)
            if not equipos_evento:
                continue

            # Determinar a qué equipo apunta el pick
            pick_norm = _safe_normalize(pick_text)
            scored = []
            for equipo in equipos_evento:
                eq_norm = _safe_normalize(equipo)
                score = _fuzzy_score(pick_norm, eq_norm)
                scored.append((equipo, score))

            best_equipo, best_score = max(scored, key=lambda x: x[1])
            if best_score >= FUZZY_HIGH_THRESHOLD:
                # Pick referencia a un equipo específico.
                equipo_key = _safe_normalize(best_equipo) or best_equipo
                grouped.setdefault(equipo_key, []).append((estado, cuota))
            else:
                # Pick neutro (Over/Under): contabiliza para ambos equipos.
                for equipo in equipos_evento:
                    equipo_key = _safe_normalize(equipo) or equipo
                    grouped.setdefault(equipo_key, []).append((estado, cuota))

        result: Dict[str, Metrics] = {
            equipo: _build_metrics(filas) for equipo, filas in grouped.items()
        }
        self._last_team_metrics = result
        return result

    # ------------------------------------------------------------------
    # classify — Requirements 3.3, 3.4, 3.5, 3.6, 3.7
    # ------------------------------------------------------------------
    def classify(self, metrics: Metrics) -> Classification:
        """
        Asigna una Classification a un Metrics (Requirement 3.3, 3.4, 3.5, 3.6, 3.7).

        Reglas (steering: backtesting-priorities, mlb-auditoria-pro):
          - EVITAR: WR < 45% O ROI < -15%   (regla más restrictiva, evaluada primero)
          - ÉLITE: WR > 65% Y ROI > +20%
          - CONFIANZA: 55% <= WR <= 65% Y ROI > 0
          - RIESGO: 45% <= WR <= 55% (cualquier ROI)

        Si total == 0, devolvemos EVITAR conservadoramente (sin datos = sin confianza).

        El orden de evaluación importa: EVITAR primero (descarte rápido),
        luego ÉLITE (la cota superior), luego CONFIANZA, luego RIESGO.
        Si nada aplica (zona "muerta" entre fronteras), cae a RIESGO conservador.
        """
        if metrics.total == 0:
            return Classification.EVITAR

        wr = metrics.win_rate
        roi = metrics.roi

        # 1) EVITAR — Req 3.7
        if wr < 45.0 or roi < -15.0:
            return Classification.EVITAR

        # 2) ÉLITE — Req 3.4
        if wr > 65.0 and roi > 20.0:
            return Classification.ELITE

        # 3) CONFIANZA — Req 3.5  (55 <= WR <= 65 y ROI positivo)
        if 55.0 <= wr <= 65.0 and roi > 0.0:
            return Classification.CONFIANZA

        # 4) RIESGO — Req 3.6  (45 <= WR <= 55, cualquier ROI no descartado)
        if 45.0 <= wr <= 55.0:
            return Classification.RIESGO

        # Caso residual: WR > 65 pero ROI <= 20  -> RIESGO conservador
        # WR entre 55 y 65 pero ROI <= 0       -> RIESGO conservador
        return Classification.RIESGO

    # ------------------------------------------------------------------
    # is_equipo_trampa — Requirement 3.8
    # ------------------------------------------------------------------
    def is_equipo_trampa(self, equipo: str, dias: int = 30) -> bool:
        """
        Determina si un equipo es Equipo_Trampa según steering mlb-auditoria-pro:
        win rate < 40% en los últimos 10 picks que lo involucran.

        Lee la tabla `backtesting` directamente (orden por fecha desc + id desc),
        toma los 10 picks terminales más recientes que mencionan al equipo en
        `evento` o en `pick` con fuzzy >= 85%.

        Returns:
            True si win rate de los últimos 10 picks < 40%, False en caso contrario.
            Si no hay suficientes picks (< 10) cae a False (no marcamos sin datos).
        """
        if not equipo or self.db is None:
            return False

        cutoff = (datetime.now() - timedelta(days=dias)).strftime("%Y-%m-%d")

        try:
            conn = self.db._connect()
            try:
                cur = conn.cursor()
                cur.execute(
                    "SELECT evento, pick, estado "
                    "FROM backtesting "
                    "WHERE deporte = 'MLB' "
                    "  AND estado IN ('GANADA', 'PERDIDA') "
                    "  AND fecha >= ? "
                    "ORDER BY fecha DESC, id DESC",
                    (cutoff,),
                )
                rows = cur.fetchall()
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"[is_equipo_trampa] DB error: {e}")
            return False

        equipo_norm = _safe_normalize(equipo)
        last_10: List[str] = []  # 'W' o 'L', máximo 10

        for evento, pick_text, estado in rows:
            if len(last_10) >= 10:
                break
            # Verificar si el equipo aparece en el evento o pick
            evento_norm = _safe_normalize(evento or "")
            pick_norm = _safe_normalize(pick_text or "")
            score_evento = _fuzzy_score(equipo_norm, evento_norm)
            score_pick = _fuzzy_score(equipo_norm, pick_norm)
            if max(score_evento, score_pick) < FUZZY_HIGH_THRESHOLD:
                continue
            last_10.append('W' if estado == "GANADA" else 'L')

        if len(last_10) < 10:
            # Sin suficiente historial: no marcamos como trampa.
            return False

        wins = sum(1 for r in last_10 if r == 'W')
        win_rate = wins / 10.0 * 100.0
        return win_rate < 40.0

    # ------------------------------------------------------------------
    # persist — Requirement 3.9
    # ------------------------------------------------------------------
    def persist(self, dias: int = 15) -> Dict[str, str]:
        """
        Persiste las métricas calculadas en el directorio de caché.

        Si las métricas aún no se han computado en esta instancia, las computa
        primero. El directorio ``cache_dir`` se crea si no existe. Las escrituras
        son atómicas (archivo temporal + ``os.replace``).

        Args:
            dias: ventana de días para los cálculos. Default 15 (steering
                  backtesting-priorities: ventana de 15 días).

        Returns:
            dict con las rutas escritas:
                ``{"pick_type": "...", "team": "..."}``
        """
        # Computar si no está cacheado en esta instancia.
        if not self._last_pick_type_metrics:
            self.compute_by_pick_type(dias=dias)
        if not self._last_team_metrics:
            self.compute_by_team(dias=dias)

        # Crear directorio si no existe.
        os.makedirs(self.cache_dir, exist_ok=True)

        pt_path = os.path.join(self.cache_dir, "pick_type_performance.json")
        team_path = os.path.join(self.cache_dir, "team_performance.json")

        # Serializar pick_type metrics con clasificación.
        pt_payload: Dict[str, object] = {
            pick_type.value: self._metrics_to_dict(
                metrics, classification=self.classify(metrics)
            )
            for pick_type, metrics in self._last_pick_type_metrics.items()
        }
        pt_payload["_metadata"] = {
            "computed_at": datetime.now().isoformat(),
            "window_days": dias,
            "total_pick_types": len(self._last_pick_type_metrics),
        }

        # Serializar team metrics con clasificación y flag Equipo_Trampa.
        team_payload: Dict[str, object] = {
            equipo: {
                **self._metrics_to_dict(metrics, classification=self.classify(metrics)),
                "is_equipo_trampa": self.is_equipo_trampa(equipo),
            }
            for equipo, metrics in self._last_team_metrics.items()
        }
        team_payload["_metadata"] = {
            "computed_at": datetime.now().isoformat(),
            "window_days": dias,
            "total_teams": len(self._last_team_metrics),
        }

        # Escribir atómicamente (tmp + replace).
        self._write_json_atomic(pt_path, pt_payload)
        self._write_json_atomic(team_path, team_payload)

        logger.info(
            f"[persist] Wrote {len(self._last_pick_type_metrics)} pick types and "
            f"{len(self._last_team_metrics)} teams to {self.cache_dir}"
        )

        return {"pick_type": pt_path, "team": team_path}

    @staticmethod
    def _metrics_to_dict(metrics: Metrics, classification=None) -> Dict[str, object]:
        """Convierte Metrics a dict serializable JSON, opcionalmente con clasificación."""
        d: Dict[str, object] = {
            "total": metrics.total,
            "hits": metrics.hits,
            "win_rate": round(metrics.win_rate, 2),
            "profit": round(metrics.profit, 2),
            "roi": round(metrics.roi, 2),
            "last_10": list(metrics.last_10),
        }
        if classification is not None:
            d["classification"] = (
                classification.value if hasattr(classification, "value") else str(classification)
            )
        return d

    @staticmethod
    def _write_json_atomic(path: str, payload) -> None:
        """Escribe JSON atómicamente: archivo temporal + ``os.replace``."""
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2, default=str)
        os.replace(tmp, path)

    def load_from_cache(self) -> Dict[str, dict]:
        """
        Lee los JSONs del ``cache_dir`` y devuelve los diccionarios crudos.

        Returns:
            ``{"pick_type": {...}, "team": {...}}``. Si los archivos no existen,
            devuelve los keys con valor ``{}`` para no romper a los callers.
        """
        out: Dict[str, dict] = {"pick_type": {}, "team": {}}
        pt_path = os.path.join(self.cache_dir, "pick_type_performance.json")
        team_path = os.path.join(self.cache_dir, "team_performance.json")

        for key, path in (("pick_type", pt_path), ("team", team_path)):
            if not os.path.exists(path):
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    out[key] = json.load(f)
            except Exception as e:
                logger.warning(f"[load_from_cache] cannot read {path}: {e}")

        return out


__all__ = [
    "EffectivenessCalculator",
]
