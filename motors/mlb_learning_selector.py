# -*- coding: utf-8 -*-
"""
LearningPickSelector — capa de aprendizaje sobre el motor heurístico que
ajusta la confianza de los candidatos por su histórico real (efectividad).

Diseño: .kiro/specs/backtesting-real-mlb/design.md (Componente 4)
Requisitos: 4.1, 4.3 (esta tarea); 4.2, 4.4, 4.5, 4.6 en Task 7.2.

Reglas críticas (Property 8 - No sobrescritura heurística):
  - NUNCA muta `base_confidence` ni las salidas de motores heurísticos.
  - `confianza_ajustada` se DERIVA por multiplicación, sin reescribir.
  - El selector no recalcula heurística; consume sus salidas.

Reglas de penalización (Property 10 - Penalización de estadio):
  - Si pick_type == HOME_RUN y `factor_hr(venue) < 0.90`, se aplica un
    factor adicional estrictamente < 1.0 para que la confianza ajustada
    sea estrictamente menor que la versión sin penalización.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from motors.mlb_backtest_models import Classification, Metrics, PickType
from motors.mlb_effectiveness import EffectivenessCalculator

logger = logging.getLogger(__name__)


# Factores de ajuste por clasificación (steering: backtesting-priorities)
# Rango total combinado por design: [0.5, 1.3] (clamp aplicado después de
# multiplicar factor_tipo * factor_equipo).
FACTOR_BY_CLASSIFICATION = {
    Classification.ELITE: 1.30,      # cota superior del rango
    Classification.CONFIANZA: 1.10,
    Classification.RIESGO: 0.85,
    Classification.EVITAR: 0.50,     # cota inferior del rango
}

# Cotas del factor combinado tras clamp.
FACTOR_MIN = 0.50
FACTOR_MAX = 1.30

# Penalización de estadio para HR cuando factor_hr(venue) < 0.90
# (steering: mlb-auditoria-pro). Estrictamente < 1.0 para garantizar
# Property 10.
HR_STADIUM_PENALTY = 0.85
HR_STADIUM_THRESHOLD = 0.90

# Cota máxima de confianza ajustada (design: retorno en [0, 99]).
CONFIANZA_AJUSTADA_MAX = 99.0
CONFIANZA_AJUSTADA_MIN = 0.0


# Jerarquía base MLB para desempate cuando dos candidatos tienen igual
# `confianza_ajustada` (steering: reglas-mlb).
# STRIKEOUTS > HOME_RUN > MONEYLINE > OVER_UNDER > HANDICAP (último, es protección).
HIERARCHY_TIEBREAK = {
    PickType.STRIKEOUTS: 4,
    PickType.HOME_RUN: 3,
    PickType.MONEYLINE: 2,
    PickType.OVER_UNDER: 1,
    PickType.HANDICAP: 0,
}


# Mapeo desde las claves que devuelve MotorDecisionInteligente.todas_opciones
# hacia nuestros PickType internos.
DECISION_ENGINE_TYPE_MAP = {
    "HOME RUN": PickType.HOME_RUN,
    "MONEYLINE": PickType.MONEYLINE,
    "OVER/UNDER": PickType.OVER_UNDER,
    "HANDICAP": PickType.HANDICAP,
    "STRIKEOUTS": PickType.STRIKEOUTS,
}


@dataclass
class FinalPick:
    """Resultado del selector — pick final con confianza ajustada y stake."""
    id: Optional[int]                 # ID único vinculado a tabla `backtesting` (None si no se persistió)
    pick_type: PickType
    pick: str
    equipo: str
    confianza_base: float
    confianza_ajustada: float
    stake: str                        # "1u" | "2u" | "3u" | "4u"
    razon: str
    es_proteccion: bool = False       # True si es Handicap progresivo de fallback
    metadata: Dict[str, Any] = field(default_factory=dict)


class LearningPickSelector:
    """
    Decisor final que ajusta la confianza heurística con la efectividad real.

    Esta clase es una capa por encima de los motores heurísticos
    (MotorDecisionInteligente, predictor_hr, predictor_ponches, motor_over_under).
    NUNCA recalcula heurística; solo deriva ajustes basados en el histórico
    persistido por EffectivenessCalculator.

    Task 7.1 implementa solo `adjusted_confidence` y el esqueleto de la clase.
    `select_best_pick` (Task 7.2) usará esta misma instancia.
    """

    def __init__(
        self,
        effectiveness: Optional[EffectivenessCalculator] = None,
        decision_engine=None,
        stadium_factors_path: str = "data/factor_estadios.json",
    ):
        """
        Args:
            effectiveness: instancia de EffectivenessCalculator (opcional;
                si no se pasa, las clasificaciones caen a RIESGO neutral).
            decision_engine: instancia de MotorDecisionInteligente (Task 7.2).
            stadium_factors_path: ruta al JSON con factores de HR por estadio
                (formato esperado: {"Coors Field": 1.30, "Oracle Park": 0.85, ...}).
        """
        self.effectiveness = effectiveness
        self.decision_engine = decision_engine
        self.stadium_factors_path = stadium_factors_path
        # Cachés lazy (se llenan en el primer uso para evitar I/O al construir)
        self._stadium_factors: Optional[dict] = None
        self._pick_type_metrics: Optional[dict] = None
        self._team_metrics: Optional[dict] = None

    # ------------------------------------------------------------------
    # adjusted_confidence — Requirements 4.1, 4.3 (Property 8, 10)
    # ------------------------------------------------------------------
    def adjusted_confidence(
        self,
        pick_type: PickType,
        equipo: str,
        base_confidence: float,
        venue: Optional[str] = None,
    ) -> float:
        """
        Devuelve la confianza ajustada SIN mutar `base_confidence`.

        Algoritmo:
          1. Obtener Classification del pick_type (histórico real).
          2. Obtener Classification del equipo.
          3. factor = FACTOR_BY_CLASSIFICATION[clase_tipo]
                    * FACTOR_BY_CLASSIFICATION[clase_equipo]
          4. factor = clamp(factor, [0.5, 1.3])  -- design: rango combinado
          5. Si pick_type == HOME_RUN y factor_hr(venue) < 0.90:
                factor *= HR_STADIUM_PENALTY     -- Property 10
          6. ajustada = clamp(base_confidence * factor, [0, 99])

        Property 8 (No sobrescritura heurística): la función es PURA respecto
        a `base_confidence` — no la modifica, solo deriva el resultado.
        Esto está garantizado por:
          - los `float` de Python son inmutables;
          - nunca se reasigna a `base_confidence` ni a un campo del caller.

        Property 10 (Penalización de estadio): para HR con factor_hr < 0.90,
        el factor multiplicativo se reduce por HR_STADIUM_PENALTY (< 1.0),
        por lo que el resultado es estrictamente menor que el de la misma
        llamada sin penalización (siempre que `base_confidence * factor` no
        haya saturado en CONFIANZA_AJUSTADA_MAX en ambos casos).

        Args:
            pick_type: tipo del pick (PickType).
            equipo: nombre del equipo (para clasificación histórica).
            base_confidence: confianza heurística base, esperada en [0, 100].
            venue: estadio del partido (para penalización HR; opcional).

        Returns:
            Confianza ajustada en [0, 99].
        """
        # Inputs defensivos: tipos no numéricos / negativos -> 0.0
        if not isinstance(base_confidence, (int, float)) or isinstance(base_confidence, bool):
            return CONFIANZA_AJUSTADA_MIN
        bc = float(base_confidence)
        if bc <= 0.0:
            return CONFIANZA_AJUSTADA_MIN

        # 1-2) Clasificaciones del tipo y del equipo
        clase_tipo = self._classify_pick_type(pick_type)
        clase_equipo = self._classify_team(equipo)

        # 3) Factor combinado por multiplicación
        factor_tipo = FACTOR_BY_CLASSIFICATION.get(clase_tipo, 1.0)
        factor_equipo = FACTOR_BY_CLASSIFICATION.get(clase_equipo, 1.0)
        factor = factor_tipo * factor_equipo

        # 4) Clamp del factor combinado a [0.5, 1.3] (design)
        factor = max(FACTOR_MIN, min(FACTOR_MAX, factor))

        # 5) Penalización de estadio para HR (Property 10)
        if pick_type == PickType.HOME_RUN and venue:
            stadium_factor = self._stadium_factor(venue)
            if stadium_factor is not None and stadium_factor < HR_STADIUM_THRESHOLD:
                factor *= HR_STADIUM_PENALTY

        # 6) Calcular confianza ajustada y aplicar clamp final [0, 99]
        adjusted = bc * factor
        return max(CONFIANZA_AJUSTADA_MIN, min(CONFIANZA_AJUSTADA_MAX, adjusted))

    # ------------------------------------------------------------------
    # Helpers privados — clasificación
    # ------------------------------------------------------------------
    def _classify_pick_type(self, pick_type: PickType) -> Classification:
        """Devuelve la Classification para un PickType según histórico."""
        if self.effectiveness is None or pick_type is None:
            return Classification.RIESGO  # neutro sin datos
        if self._pick_type_metrics is None:
            try:
                self._pick_type_metrics = self.effectiveness.compute_by_pick_type()
            except Exception as e:
                logger.error(f"[_classify_pick_type] error: {e}")
                self._pick_type_metrics = {}
        m = self._pick_type_metrics.get(pick_type)
        if m is None or m.total == 0:
            return Classification.RIESGO
        try:
            return self.effectiveness.classify(m)
        except Exception as e:
            logger.debug(f"[_classify_pick_type] classify error: {e}")
            return Classification.RIESGO

    def _classify_team(self, equipo: str) -> Classification:
        """Devuelve la Classification para un equipo según histórico."""
        if not equipo or self.effectiveness is None:
            return Classification.RIESGO
        if self._team_metrics is None:
            try:
                self._team_metrics = self.effectiveness.compute_by_team()
            except Exception as e:
                logger.error(f"[_classify_team] error: {e}")
                self._team_metrics = {}

        # Búsqueda exacta primero, luego fuzzy (umbral 85% del steering).
        m: Optional[Metrics] = self._team_metrics.get(equipo)
        if m is None:
            try:
                from motors.mlb_backtest_auditor import _fuzzy_score, FUZZY_HIGH_THRESHOLD
                best_score = 0.0
                best_metrics: Optional[Metrics] = None
                for k, v in self._team_metrics.items():
                    score = _fuzzy_score(equipo, k)
                    if score >= FUZZY_HIGH_THRESHOLD and score > best_score:
                        best_metrics = v
                        best_score = score
                m = best_metrics
            except Exception as e:
                logger.debug(f"[_classify_team] fuzzy error: {e}")

        if m is None or m.total == 0:
            return Classification.RIESGO
        try:
            return self.effectiveness.classify(m)
        except Exception as e:
            logger.debug(f"[_classify_team] classify error: {e}")
            return Classification.RIESGO

    # ------------------------------------------------------------------
    # Helpers privados — factor de estadio
    # ------------------------------------------------------------------
    def _stadium_factor(self, venue: str) -> Optional[float]:
        """
        Devuelve el factor de HR del estadio (e.g. Coors Field=1.30,
        Oracle Park=0.85). Retorna None si no hay datos.
        """
        if self._stadium_factors is None:
            self._stadium_factors = self._load_stadium_factors()
        if not venue or not self._stadium_factors:
            return None

        # Búsqueda exacta primero
        if venue in self._stadium_factors:
            try:
                return float(self._stadium_factors[venue])
            except (TypeError, ValueError):
                return None

        # Búsqueda fuzzy (umbral 85%)
        try:
            from motors.mlb_backtest_auditor import _fuzzy_score, FUZZY_HIGH_THRESHOLD
            best_score = 0.0
            best_value: Optional[float] = None
            for stadium, factor in self._stadium_factors.items():
                score = _fuzzy_score(venue, stadium)
                if score >= FUZZY_HIGH_THRESHOLD and score > best_score:
                    try:
                        best_value = float(factor)
                        best_score = score
                    except (TypeError, ValueError):
                        continue
            return best_value
        except Exception:
            return None

    def _load_stadium_factors(self) -> dict:
        """Carga el JSON de factores; devuelve {} si no existe o está corrupto."""
        if not self.stadium_factors_path or not os.path.exists(self.stadium_factors_path):
            return {}
        try:
            with open(self.stadium_factors_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except Exception as e:
            logger.warning(
                f"[_load_stadium_factors] cannot read {self.stadium_factors_path}: {e}"
            )
        return {}

    # ------------------------------------------------------------------
    # select_best_pick — Requirements 4.2, 4.4, 4.5, 4.6
    # ------------------------------------------------------------------
    def select_best_pick(self, analisis_completo: Dict[str, Any]) -> "FinalPick":
        """
        Selecciona el pick final por partido aplicando exclusiones, jerarquía
        y stake dinámico sobre los candidatos del MotorDecisionInteligente.

        Args:
            analisis_completo: dict que contiene al menos:
                - "partido": dict con keys "visitante", "local",
                   opcionalmente "venue"/"estadio".
                - "resultado_heuristico": dict para MotorDecisionInteligente.
                - "candidatos_hr": lista de dicts (puede ser vacía).
                - "clima": dict opcional.

        Algoritmo:
            1. Llamar a self.decision_engine.decidir_mejor_apuesta(...) y leer
               `todas_opciones` (NO recalcula heurística — Property 8).
            2. Construir lista de candidatos con (pick_type, pick, equipo,
               confianza_base).
            3. Calcular confianza_ajustada via adjusted_confidence().
            4. Excluir equipos EVITAR / Equipo_Trampa (Property 9).
            5. Ordenar por (confianza_ajustada DESC, jerarquía DESC) y elegir
               el primero. Empate de confianza -> jerarquía MLB
               (STRIKEOUTS > HOME_RUN > MONEYLINE > OVER_UNDER > HANDICAP).
            6. Si todos quedan excluidos -> Handicap progresivo de protección
               (Requirement 4.5, steering logica-dinamica).
            7. Stake dinámico según confianza_ajustada y clasificación del
               equipo (steering backtesting-priorities).
            8. Persistir en tabla `backtesting` y devolver FinalPick con `id`.

        Returns:
            FinalPick (siempre — nunca None).

        Property 9: el pick final NUNCA pertenece a un equipo EVITAR/TRAMPA.
        """
        # Sin motor heurístico: devolver protección como sentinela seguro.
        if self.decision_engine is None:
            return self._handicap_proteccion(
                analisis_completo, motivo="Sin motor heurístico"
            )

        partido = analisis_completo.get("partido", {}) or {}
        resultado_h = analisis_completo.get("resultado_heuristico", {}) or {}
        candidatos_hr = analisis_completo.get("candidatos_hr", []) or []
        clima = analisis_completo.get("clima")

        # 1) Llamar al motor heurístico — NO recalculamos heurística.
        try:
            decision = self.decision_engine.decidir_mejor_apuesta(
                partido, resultado_h, candidatos_hr, clima=clima,
            )
        except Exception as e:
            logger.error(f"[select_best_pick] Motor heurístico falló: {e}")
            return self._handicap_proteccion(
                analisis_completo, motivo=f"Motor falló: {e}"
            )

        todas = (decision or {}).get("todas_opciones", {}) or {}
        if not todas:
            return self._handicap_proteccion(
                analisis_completo, motivo="Sin opciones del motor"
            )

        # 2) Construir candidatos a partir de `todas_opciones`.
        venue = partido.get("venue") or partido.get("estadio") or ""
        candidatos: List[Dict[str, Any]] = []
        for tipo_str, datos in todas.items():
            pick_type = DECISION_ENGINE_TYPE_MAP.get(tipo_str)
            if pick_type is None or not isinstance(datos, dict):
                continue
            pick_text = datos.get("pick", "") or ""
            if not pick_text or pick_text in ("N/A", "None"):
                continue
            # Confianza base: usamos `punt` (puntuación interna del motor) como
            # proxy de confianza heurística por tipo. Para el MEJOR pick, el
            # motor expone también `confianza` global, pero no por opción.
            try:
                base_conf = float(datos.get("punt", 0))
            except (TypeError, ValueError):
                base_conf = 0.0
            equipo = self._extract_team(pick_text, partido)
            candidatos.append({
                "pick_type": pick_type,
                "pick": pick_text,
                "equipo": equipo,
                "base_conf": base_conf,
            })

        if not candidatos:
            return self._handicap_proteccion(
                analisis_completo, motivo="Sin candidatos válidos"
            )

        # 3) Calcular confianza_ajustada por candidato (Property 8: no muta base).
        for c in candidatos:
            c["adj_conf"] = self.adjusted_confidence(
                c["pick_type"], c["equipo"], c["base_conf"], venue=venue,
            )

        # 4) Excluir EVITAR / Equipo_Trampa (Property 9).
        candidatos_validos = [
            c for c in candidatos if not self._is_excluded(c["equipo"])
        ]
        if not candidatos_validos:
            return self._handicap_proteccion(
                analisis_completo, motivo="Todos excluidos por EVITAR/TRAMPA"
            )

        # 5) Ordenar por (confianza_ajustada DESC, jerarquía DESC).
        candidatos_validos.sort(
            key=lambda c: (
                c["adj_conf"],
                HIERARCHY_TIEBREAK.get(c["pick_type"], 0),
            ),
            reverse=True,
        )
        elegido = candidatos_validos[0]

        # 6) Stake dinámico (steering: backtesting-priorities + mlb-auditoria-pro).
        stake = self._compute_stake(
            elegido["adj_conf"], self._classify_team(elegido["equipo"])
        )

        # 7) Persistir en tabla `backtesting` para obtener `id` único
        #    (steering: integridad-datos -> "Cada pick generado debe tener un
        #    ID único vinculado a la tabla `backtesting`").
        pick_id = self._persist_backtesting(partido, elegido["pick"])

        return FinalPick(
            id=pick_id,
            pick_type=elegido["pick_type"],
            pick=elegido["pick"],
            equipo=elegido["equipo"],
            confianza_base=elegido["base_conf"],
            confianza_ajustada=elegido["adj_conf"],
            stake=stake,
            razon=(
                f"Mejor candidato ajustado "
                f"(jerarquía: {elegido['pick_type'].value})"
            ),
            es_proteccion=False,
            metadata={"motor_decision": decision},
        )

    # ------------------------------------------------------------------
    # Helpers de selección
    # ------------------------------------------------------------------
    def _extract_team(self, pick_text: str, partido: Dict[str, Any]) -> str:
        """
        Identifica el equipo del pick comparando `pick_text` contra
        visitante/local con fuzzy matching (umbral 85% — steering estrategia-fuzzy).

        Devuelve el nombre del equipo o "" si no se identifica (p.ej. para
        OVER/UNDER que no apunta a un equipo concreto).
        """
        if not pick_text:
            return ""
        visitante = partido.get("visitante", "") or partido.get("away", "") or ""
        local = partido.get("local", "") or partido.get("home", "") or ""
        try:
            from motors.mlb_backtest_auditor import (
                FUZZY_HIGH_THRESHOLD,
                _fuzzy_score,
                _safe_normalize,
            )
        except ImportError:
            # Fallback conservador si auditor no está disponible.
            return ""

        pick_norm = _safe_normalize(pick_text)
        score_v = _fuzzy_score(pick_norm, _safe_normalize(visitante)) if visitante else 0.0
        score_l = _fuzzy_score(pick_norm, _safe_normalize(local)) if local else 0.0
        if score_v >= FUZZY_HIGH_THRESHOLD and score_v >= score_l:
            return visitante
        if score_l >= FUZZY_HIGH_THRESHOLD:
            return local
        # Sin equipo claro (p.ej. "OVER 8.5"): "" — no contamina exclusiones.
        return ""

    def _is_excluded(self, equipo: str) -> bool:
        """
        Devuelve True si el equipo está clasificado como EVITAR o si el
        EffectivenessCalculator lo marca como Equipo_Trampa.

        Si `equipo` está vacío (p.ej. OU sin equipo) -> False: no se excluye.
        """
        if not equipo:
            return False
        try:
            if self._classify_team(equipo) == Classification.EVITAR:
                return True
        except Exception as e:
            logger.debug(f"[_is_excluded] classify error: {e}")
        if self.effectiveness is not None:
            try:
                if self.effectiveness.is_equipo_trampa(equipo):
                    return True
            except Exception as e:
                logger.debug(f"[_is_excluded] is_equipo_trampa error: {e}")
        return False

    def _compute_stake(
        self,
        adj_conf: float,
        team_class: Classification,
    ) -> str:
        """
        Stake dinámico según confianza ajustada + clasificación del equipo
        (steering: backtesting-priorities -> "REGLAS DE STAKE DINÁMICO").

        Reglas:
          - team_class == EVITAR             -> "1u" (defensa redundante)
          - conf > 75 + ELITE                -> "4u"
          - 65 <= conf <= 75 + ELITE/CONFIANZA -> "3u"
          - 55 <= conf <= 65                 -> "2u"
          - else                             -> "1u"
        """
        if team_class == Classification.EVITAR:
            return "1u"
        if adj_conf > 75 and team_class == Classification.ELITE:
            return "4u"
        if 65 <= adj_conf <= 75 and team_class in (
            Classification.ELITE, Classification.CONFIANZA,
        ):
            return "3u"
        if 55 <= adj_conf <= 65:
            return "2u"
        return "1u"

    def _handicap_proteccion(
        self,
        analisis: Dict[str, Any],
        motivo: str = "",
    ) -> "FinalPick":
        """
        Devuelve un Handicap progresivo de protección de capital cuando todos
        los candidatos quedan excluidos o el motor no puede decidir
        (Requirement 4.5, steering logica-dinamica).

        Reglas progresivas según confianza heurística base:
          - confianza < 50%   -> "+3.5"
          - 50% <= conf < 55% -> "+2.5"
          - >= 55%            -> "+1.5"
        """
        partido = analisis.get("partido", {}) or {}
        resultado_h = analisis.get("resultado_heuristico", {}) or {}
        visitante = partido.get("visitante", "") or partido.get("away", "") or ""
        local = partido.get("local", "") or partido.get("home", "") or ""
        pick_ml = resultado_h.get("pick", "") or visitante or local

        try:
            conf_base = float(resultado_h.get("confianza", 50))
        except (TypeError, ValueError):
            conf_base = 50.0

        if conf_base < 50:
            hcap = "+3.5"
        elif conf_base < 55:
            hcap = "+2.5"
        else:
            hcap = "+1.5"

        pick_text = (
            f"{pick_ml} {hcap}".strip() if pick_ml else f"Handicap {hcap}"
        )
        pick_id = self._persist_backtesting(partido, pick_text)

        return FinalPick(
            id=pick_id,
            pick_type=PickType.HANDICAP,
            pick=pick_text,
            equipo=pick_ml,
            confianza_base=conf_base,
            confianza_ajustada=min(CONFIANZA_AJUSTADA_MAX, conf_base + 15.0),
            stake="1u",
            razon=f"Handicap progresivo de protección. {motivo}".strip(),
            es_proteccion=True,
            metadata={"protection_reason": motivo},
        )

    def _persist_backtesting(
        self,
        partido: Dict[str, Any],
        pick_text: str,
    ) -> Optional[int]:
        """
        Inserta el pick en la tabla `backtesting` con cuota default 1.90 y
        devuelve el `id` auto-incremental (lastrowid).

        Si la DB no está disponible o hay error, devuelve None y el FinalPick
        queda con id=None (no rompe el flujo). Cuota default consistente con
        steering mlb-auditoria-pro: 1.90 (-110) para Handicaps/OU/MoneyLine.
        """
        if self.effectiveness is None or self.effectiveness.db is None:
            return None
        db = self.effectiveness.db
        try:
            from datetime import datetime
            evento = (
                f"{partido.get('visitante', '')} vs {partido.get('local', '')}"
            ).strip()
            conn = db._connect()
            try:
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO backtesting "
                    "(fecha, deporte, evento, pick, cuota, estado, creado_en) "
                    "VALUES (?, 'MLB', ?, ?, 1.90, 'PENDIENTE', ?)",
                    (
                        datetime.now().strftime("%Y-%m-%d"),
                        evento,
                        pick_text,
                        datetime.now().isoformat(),
                    ),
                )
                conn.commit()
                return cur.lastrowid
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"[_persist_backtesting] error: {e}")
            return None


__all__ = [
    "LearningPickSelector",
    "FinalPick",
    "FACTOR_BY_CLASSIFICATION",
    "FACTOR_MIN",
    "FACTOR_MAX",
    "HR_STADIUM_PENALTY",
    "HR_STADIUM_THRESHOLD",
    "CONFIANZA_AJUSTADA_MAX",
    "CONFIANZA_AJUSTADA_MIN",
    "HIERARCHY_TIEBREAK",
    "DECISION_ENGINE_TYPE_MAP",
]
