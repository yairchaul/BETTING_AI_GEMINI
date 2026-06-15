# -*- coding: utf-8 -*-
"""
MLBBacktestAuditor — auditor que cruza picks PENDIENTE contra resultados reales
para asignarles estado terminal (GANADA/PERDIDA) y cuota.

Diseño: .kiro/specs/backtesting-real-mlb/design.md (Componente 2)
Requisitos: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9

Esta tarea (4.1) solo implementa:
  - classify_pick(pick_text) -> PickType
  - match_game(pick, results) -> Optional[GameResult]
  - Helpers de fuzzy matching con umbral 85% (steering estrategia-fuzzy)

Las tareas 4.2 (evaluate por tipo) y 4.3 (audit_pending) extienden esta clase.
"""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from motors.mlb_backtest_models import (
    BacktestPick,
    GameResult,
    HomeRunRecord,
    PickType,
    StrikeoutRecord,
)

logger = logging.getLogger(__name__)

# Umbrales de fuzzy matching (steering: estrategia-fuzzy)
FUZZY_HIGH_THRESHOLD = 85   # >= 85% se acepta como match
FUZZY_REVIEW_LOW = 70       # 70-84% queda "Sujeto a revisión" -> PENDIENTE
FUZZY_REVIEW_HIGH = 84

# Cuotas por defecto cuando el pick no tiene cuota registrada
# (steering: mlb-auditoria-pro). HR es +250 = 3.50; el resto -110 ≈ 1.90.
DEFAULT_CUOTA_HR = 3.50
DEFAULT_CUOTA_OTROS = 1.90


# Sentinela de retorno de match_game cuando el match es ambiguo (70-84%):
# se retorna None y se marca el pick para revisión manual.
class MatchStatus:
    EXACT = "EXACT"           # >= 85% en ambos equipos + fecha
    REVIEW = "REVIEW"         # 70-84% en al menos un equipo
    NO_MATCH = "NO_MATCH"     # < 70% o fecha mismatch


@dataclass
class PickOutcome:
    """
    Resultado de evaluar un pick contra un GameResult.

    Atributos:
      - estado: "GANADA" | "PERDIDA" | "PENDIENTE"
      - cuota_usada: cuota real del pick o default según tipo (1.90/3.50)
      - motivo: razón legible del veredicto (para logs y auditoría)
    """
    estado: str
    cuota_usada: float
    motivo: str = ""


@dataclass
class AuditReport:
    """
    Resumen de una corrida de auditoría (audit_pending).

    Campos:
      - total_pendientes: # de picks PENDIENTE leídos en la ventana.
      - auditados_ganada / auditados_perdida: # de transiciones a estado terminal.
      - sin_resultado: picks sin GameResult emparejable (NO_MATCH).
      - revision: picks dejados PENDIENTE por fuzzy 70-84% o por línea/sentido inválidos.
      - omitidos_terminal: picks que ya estaban GANADA/PERDIDA y NO se tocaron
        (Req 2.3 — el estado terminal nunca se revierte).
      - detalles: lista de dicts con el resultado de cada UPDATE persistido.
    """
    total_pendientes: int = 0
    auditados_ganada: int = 0
    auditados_perdida: int = 0
    sin_resultado: int = 0
    revision: int = 0
    omitidos_terminal: int = 0
    detalles: List[dict] = field(default_factory=list)

    def resumen(self) -> str:
        """Resumen one-liner para logs / dashboards."""
        return (
            f"Pendientes={self.total_pendientes} "
            f"GANADA={self.auditados_ganada} "
            f"PERDIDA={self.auditados_perdida} "
            f"REVIEW={self.revision} "
            f"sin_match={self.sin_resultado} "
            f"omitidos_terminal={self.omitidos_terminal}"
        )


def _fuzzy_score(a: str, b: str) -> float:
    """
    Devuelve un score de similitud 0-100 entre `a` y `b`.

    Usa rapidfuzz.fuzz.WRatio si está disponible (regla steering). En su
    ausencia cae a un equivalente local (substring + partial ratio sobre
    `difflib.SequenceMatcher`) que aproxima el comportamiento de WRatio
    cuando el texto del pick contiene el nombre del equipo. Ambos extremos
    vacíos -> 0.
    """
    if not a or not b:
        return 0.0
    a_norm = (a or "").strip().lower()
    b_norm = (b or "").strip().lower()
    if not a_norm or not b_norm:
        return 0.0
    if a_norm == b_norm:
        return 100.0
    try:
        from rapidfuzz import fuzz  # type: ignore
        return float(fuzz.WRatio(a_norm, b_norm))
    except Exception:
        from difflib import SequenceMatcher

        # Identificar la cadena más corta y la más larga.
        if len(a_norm) <= len(b_norm):
            shorter, longer = a_norm, b_norm
        else:
            shorter, longer = b_norm, a_norm

        # Coincidencia de substring -> 100 (mimica fuzz.partial_ratio cuando
        # el nombre del equipo aparece tal cual dentro del texto del pick).
        if shorter and shorter in longer:
            return 100.0

        # Partial ratio: deslizar una ventana de longitud `len(shorter)` por
        # `longer` y tomar el mejor SequenceMatcher.ratio() de cada ventana.
        best = 0.0
        if shorter and len(longer) >= len(shorter):
            window = len(shorter)
            for i in range(len(longer) - window + 1):
                ratio = SequenceMatcher(None, shorter, longer[i:i + window]).ratio() * 100.0
                if ratio > best:
                    best = ratio

        # Floor: ratio completo entre ambas cadenas tal cual.
        full = SequenceMatcher(None, a_norm, b_norm).ratio() * 100.0
        return max(best, full)


def _safe_normalize(name: str) -> str:
    """Normaliza con utils/fuzzy_matching si está disponible; si no, lower-strip."""
    try:
        from utils.fuzzy_matching import normalizar_equipo
        return normalizar_equipo(name) or name
    except Exception:
        return (name or "").strip()


class MLBBacktestAuditor:
    """
    Auditor que cruza picks PENDIENTE de la tabla `backtesting` contra resultados
    reales (`GameResult`) y asigna estado terminal y cuota.
    """

    def __init__(
        self,
        db=None,
        results_path: str = "data/resultados_reales_15dias.json",
    ):
        # `db` puede ser None en tests; el caller debe inyectar DatabaseManager.
        self.db = db
        self.results_path = results_path

    # ------------------------------------------------------------------
    # classify_pick — Requirement 2.7
    # ------------------------------------------------------------------
    def classify_pick(self, pick_text: str) -> PickType:
        """
        Clasifica el texto del pick en un PickType.

        Heurísticas (orden de evaluación):
          1. STRIKEOUTS: contiene "K", "ponche", "strikeout(s)"
          2. HOME_RUN: contiene "HR", "home run", "jonrón", "homerun"
          3. HANDICAP: contiene un signo +/- seguido de número decimal (run line)
          4. OVER_UNDER: contiene "over"/"under" + número, o "más de"/"menos de"
          5. MONEYLINE: cae aquí por defecto si no encaja en lo anterior

        Devuelve siempre un PickType (nunca None). Los textos vacíos caen a
        MONEYLINE como default conservador (la auditoría posterior fallará
        con NO_MATCH si no se puede emparejar).
        """
        if not pick_text:
            return PickType.MONEYLINE

        text = pick_text.lower()

        # 1) Strikeouts: K(s) / ponches
        if re.search(r'\b(k|ks|strikeouts?|ponches?)\b', text):
            return PickType.STRIKEOUTS

        # 2) Home Run
        if re.search(r'\b(hr|home\s*runs?|jonr[oó]n)\b', text):
            return PickType.HOME_RUN

        # 3) Handicap (run line MLB +1.5 / -1.5 / +2.5 etc.)
        # Detectar patrones tipo "Yankees +1.5" o "Dodgers -1.5"
        if re.search(r'[+-]\s*\d+\.5\b', text):
            return PickType.HANDICAP

        # 4) Over/Under
        if re.search(r'\b(over|under|m[aá]s\s+de|menos\s+de|sobre|bajo)\s+\d', text):
            return PickType.OVER_UNDER
        # También "O 8.5" / "U 8.5" abreviados
        if re.search(r'\b[ou]\s+\d+\.?\d*\b', text):
            return PickType.OVER_UNDER

        # 5) Default: Moneyline (ganador del partido)
        return PickType.MONEYLINE

    # ------------------------------------------------------------------
    # match_game — Requirement 2.7, 2.8
    # ------------------------------------------------------------------
    def match_game(
        self,
        pick: BacktestPick,
        results: List[GameResult],
    ) -> Optional[GameResult]:
        """
        Empareja un pick con un GameResult por fecha + equipos normalizados.

        Reglas:
          - La fecha debe coincidir (YYYY-MM-DD).
          - Se compara el texto del pick contra `away` y `home` del GameResult,
            tras normalizar ambos lados con utils/fuzzy_matching.
          - Score >= 85% en al menos uno de los dos equipos => MATCH.
          - Score entre 70% y 84% => "Sujeto a revisión": retorna None.
            (Requirement 2.8 — el caller debe dejar el pick PENDIENTE.)
          - Score < 70% o sin fecha => None (NO_MATCH).

        Devuelve el GameResult emparejado o None.
        """
        candidate, status = self.match_game_with_status(pick, results)
        if status == MatchStatus.EXACT:
            return candidate
        return None

    def match_game_with_status(
        self,
        pick: BacktestPick,
        results: List[GameResult],
    ) -> Tuple[Optional[GameResult], str]:
        """
        Como match_game, pero devuelve también el estado del match para que
        el caller (audit_pending) pueda distinguir REVIEW de NO_MATCH.
        """
        if not pick or not results or not pick.fecha:
            return (None, MatchStatus.NO_MATCH)

        pick_text = (pick.pick or "") + " " + (pick.evento or "")
        pick_text_norm = _safe_normalize(pick_text)

        best: Optional[GameResult] = None
        best_score: float = 0.0
        any_review = False

        for result in results:
            if result.fecha != pick.fecha:
                continue

            # Comparar con ambos equipos normalizados
            home_norm = _safe_normalize(result.home)
            away_norm = _safe_normalize(result.away)

            score_home = _fuzzy_score(pick_text_norm, home_norm)
            score_away = _fuzzy_score(pick_text_norm, away_norm)
            # Tomar el máximo: el pick puede mencionar solo uno de los dos.
            score = max(score_home, score_away)

            if score >= FUZZY_HIGH_THRESHOLD and score > best_score:
                best = result
                best_score = score

            elif FUZZY_REVIEW_LOW <= score <= FUZZY_REVIEW_HIGH:
                any_review = True

        if best is not None:
            return (best, MatchStatus.EXACT)
        if any_review:
            return (None, MatchStatus.REVIEW)
        return (None, MatchStatus.NO_MATCH)

    # ------------------------------------------------------------------
    # evaluate — Requirements 2.1, 2.4, 2.5, 2.6, 2.8, 2.9
    # ------------------------------------------------------------------
    def evaluate(
        self,
        pick: BacktestPick,
        result: GameResult,
        fuzzy_status: str = "EXACT",
    ) -> "PickOutcome":
        """
        Evalúa un pick contra un GameResult y devuelve el outcome.

        Preconditions:
          - pick.estado == "PENDIENTE" (el caller no debe pasar terminales).
          - result emparejado con el pick (mismo partido).
          - fuzzy_status indica el resultado de match_game_with_status. Si es
            REVIEW (70-84%), retorna PENDIENTE (Requirement 2.8).

        Postconditions:
          - PickOutcome.estado in {GANADA, PERDIDA, PENDIENTE}.
          - cuota_usada nunca es None ni 0; usa default 1.90/3.50 si falta.
          - HOME_RUN se evalúa por personId con home_runs > 0 (Req 2.1).
          - STRIKEOUTS con TBD o línea 0 => PENDIENTE (Req 2.9).

        Esta función NUNCA muta el pick original.
        """
        # Sujeto a revisión (70-84%): conservar PENDIENTE (Req 2.8)
        if fuzzy_status == MatchStatus.REVIEW or fuzzy_status == "REVIEW":
            return PickOutcome(
                estado="PENDIENTE",
                cuota_usada=self._resolve_cuota(pick),
                motivo="Sujeto a revisión (fuzzy 70-84%)",
            )

        tipo = self.classify_pick(pick.pick or "")

        if tipo == PickType.MONEYLINE:
            return self._evaluate_moneyline(pick, result)
        if tipo == PickType.OVER_UNDER:
            return self._evaluate_over_under(pick, result)
        if tipo == PickType.HANDICAP:
            return self._evaluate_handicap(pick, result)
        if tipo == PickType.HOME_RUN:
            return self._evaluate_home_run(pick, result)
        if tipo == PickType.STRIKEOUTS:
            return self._evaluate_strikeouts(pick, result)

        # Tipo desconocido: dejar PENDIENTE (no debería llegar aquí porque
        # classify_pick siempre devuelve un PickType válido).
        return PickOutcome(
            estado="PENDIENTE",
            cuota_usada=self._resolve_cuota(pick),
            motivo=f"Tipo desconocido: {tipo}",
        )

    def _resolve_cuota(self, pick: BacktestPick) -> float:
        """
        Devuelve la cuota real si existe; default según tipo si no.

        Cuotas conservadoras (steering: mlb-auditoria-pro):
          - HOME_RUN -> 3.50 (+250)
          - HANDICAP / OVER_UNDER / MONEYLINE / STRIKEOUTS -> 1.90 (-110)
        """
        if pick.cuota is not None and pick.cuota > 0:
            return float(pick.cuota)
        tipo = self.classify_pick(pick.pick or "")
        return DEFAULT_CUOTA_HR if tipo == PickType.HOME_RUN else DEFAULT_CUOTA_OTROS

    # ------------------------------------------------------------------
    # Evaluadores por tipo
    # ------------------------------------------------------------------
    def _evaluate_moneyline(self, pick: BacktestPick, result: GameResult) -> "PickOutcome":
        """
        GANADA si y solo si el texto del pick referencia al `winner`
        (fuzzy>=85%) y NO referencia más fuertemente al perdedor.

        Solo se compara `pick.pick` (no `pick.evento`), porque `evento` suele
        contener AMBOS equipos ("A vs B") y produciría empate de scores.
        """
        cuota = self._resolve_cuota(pick)
        # Quitar etiquetas de mercado ("ML", "moneyline", "ganador") para que
        # el fuzzy compare nombre de equipo contra nombre de equipo.
        raw_text = (pick.pick or "")
        cleaned = re.sub(
            r'\b(ml|moneyline|money\s*line|ganador|gana)\b',
            '',
            raw_text,
            flags=re.IGNORECASE,
        ).strip()
        pick_text = _safe_normalize(cleaned) or cleaned
        if not pick_text:
            return PickOutcome("PERDIDA", cuota, motivo="Pick vacío")

        loser = result.away if result.winner == result.home else result.home
        winner_norm = _safe_normalize(result.winner)
        loser_norm = _safe_normalize(loser)

        score_winner = _fuzzy_score(pick_text, winner_norm)
        score_loser = _fuzzy_score(pick_text, loser_norm)

        if score_winner >= FUZZY_HIGH_THRESHOLD and score_winner > score_loser:
            return PickOutcome(
                "GANADA",
                cuota,
                motivo=f"Winner {result.winner} match {score_winner:.0f}%",
            )
        return PickOutcome(
            "PERDIDA",
            cuota,
            motivo=f"Pick no referencia al winner {result.winner}",
        )

    def _evaluate_over_under(self, pick: BacktestPick, result: GameResult) -> "PickOutcome":
        """
        Extrae sentido (over/under) y línea numérica del pick;
        compara contra `result.total_runs`.
        Si no se puede extraer la línea o el sentido, queda PENDIENTE.
        """
        cuota = self._resolve_cuota(pick)
        text = (pick.pick or "").lower()

        # Detectar sentido
        if re.search(r'\b(over|m[aá]s\s+de|sobre)\b', text):
            sentido = "over"
        elif re.search(r'\b(under|menos\s+de|bajo)\b', text):
            sentido = "under"
        else:
            return PickOutcome("PENDIENTE", cuota, motivo="No se pudo extraer sentido OU")

        # Extraer línea numérica (decimal o entero)
        m = re.search(r'(\d+(?:\.\d+)?)', text)
        if not m:
            return PickOutcome("PENDIENTE", cuota, motivo="No se pudo extraer línea OU")
        try:
            linea = float(m.group(1))
        except ValueError:
            return PickOutcome("PENDIENTE", cuota, motivo=f"Línea OU inválida: {m.group(1)}")

        # Push (tie): convención conservadora -> PERDIDA. MLB rara vez tiene
        # líneas enteras, pero por seguridad lo dejamos así.
        if result.total_runs == linea:
            return PickOutcome(
                "PERDIDA",
                cuota,
                motivo=f"Push {sentido.upper()} {linea} == total_runs {result.total_runs}",
            )

        if sentido == "over":
            outcome = "GANADA" if result.total_runs > linea else "PERDIDA"
        else:
            outcome = "GANADA" if result.total_runs < linea else "PERDIDA"

        return PickOutcome(
            outcome,
            cuota,
            motivo=f"{sentido.upper()} {linea} vs total_runs {result.total_runs}",
        )

    def _evaluate_handicap(self, pick: BacktestPick, result: GameResult) -> "PickOutcome":
        """
        Run Line MLB: identifica el equipo del pick y el handicap (+1.5/-1.5);
        GANADA si score(equipo) + handicap > score(rival).

        Solo se compara `pick.pick` (no `pick.evento`) para evitar empate de
        scores cuando ambos equipos aparecen en el evento.
        """
        cuota = self._resolve_cuota(pick)
        text = (pick.pick or "")

        # Extraer handicap (+1.5 / -1.5 / +2.5 ...)
        m = re.search(r'([+-])\s*(\d+(?:\.\d+)?)', text)
        if not m:
            return PickOutcome("PENDIENTE", cuota, motivo="No se pudo extraer handicap")
        signo = m.group(1)
        try:
            valor = float(m.group(2))
        except ValueError:
            return PickOutcome("PENDIENTE", cuota, motivo=f"Handicap inválido: {m.group(2)}")
        handicap = valor if signo == "+" else -valor

        # Identificar a qué equipo se refiere el pick (home o away).
        # Se elimina el patrón del handicap del texto para no contaminar el
        # fuzzy score (p.ej. "Yankees -1.5" -> "Yankees" antes de comparar).
        text_clean = re.sub(r'[+-]\s*\d+(?:\.\d+)?', '', text).strip()
        pick_text_norm = _safe_normalize(text_clean) or text_clean
        home_norm = _safe_normalize(result.home)
        away_norm = _safe_normalize(result.away)
        score_home = _fuzzy_score(pick_text_norm, home_norm)
        score_away = _fuzzy_score(pick_text_norm, away_norm)

        if score_home >= FUZZY_HIGH_THRESHOLD and score_home >= score_away:
            team_score = result.home_score
            rival_score = result.away_score
            team_name = result.home
        elif score_away >= FUZZY_HIGH_THRESHOLD and score_away > score_home:
            team_score = result.away_score
            rival_score = result.home_score
            team_name = result.away
        else:
            return PickOutcome(
                "PENDIENTE",
                cuota,
                motivo="No se identificó el equipo del handicap",
            )

        margen_ajustado = team_score + handicap - rival_score
        if margen_ajustado > 0:
            return PickOutcome(
                "GANADA",
                cuota,
                motivo=f"{team_name} {signo}{valor}: {team_score}+{handicap}>{rival_score}",
            )
        return PickOutcome(
            "PERDIDA",
            cuota,
            motivo=f"{team_name} {signo}{valor}: {team_score}+{handicap}<={rival_score}",
        )

    def _evaluate_home_run(self, pick: BacktestPick, result: GameResult) -> "PickOutcome":
        """
        GANADA si y solo si existe un personId en result.home_runs cuyo nombre
        coincide con el jugador del pick (fuzzy>=85%) y home_runs > 0
        (Requirement 2.1, Property 3).

        El nombre del jugador se extrae removiendo palabras clave de HR
        ("HR", "home run", "jonrón", "to hit", "home run prop").
        """
        cuota = self._resolve_cuota(pick)
        raw = (pick.pick or "")

        # Extraer nombre del jugador removiendo keywords
        nombre = re.sub(
            r'\b(hr|home\s*runs?|jonr[oó]n|to\s+hit|home\s+run\s+prop)\b',
            '',
            raw,
            flags=re.IGNORECASE,
        ).strip(' :-')
        if not nombre:
            return PickOutcome("PENDIENTE", cuota, motivo="No se pudo extraer jugador")

        nombre_norm = _safe_normalize(nombre)

        # Buscar en result.home_runs por nombre fuzzy + home_runs > 0
        best_score = 0.0
        matched = None
        for hr in result.home_runs:
            if hr.home_runs <= 0:
                continue  # invariante del modelo, defensa por si acaso
            score = _fuzzy_score(nombre_norm, hr.full_name)
            if score >= FUZZY_HIGH_THRESHOLD and score > best_score:
                matched = hr
                best_score = score

        if matched is not None:
            return PickOutcome(
                "GANADA",
                cuota,
                motivo=f"HR de {matched.full_name} (personId={matched.person_id}) confirmado",
            )
        return PickOutcome(
            "PERDIDA",
            cuota,
            motivo=f"{nombre} no figura en home_runs del juego",
        )

    def _evaluate_strikeouts(self, pick: BacktestPick, result: GameResult) -> "PickOutcome":
        """
        Compara K del pitcher contra la línea del pick. Sentido over/under.

        Si el pick contiene 'TBD' (pitcher no confirmado) o si la línea es 0 o
        no se puede extraer, deja PENDIENTE (Requirement 2.9 — k9==0 / TBD).
        """
        cuota = self._resolve_cuota(pick)
        text = (pick.pick or "")

        # Req 2.9: TBD => PENDIENTE
        if re.search(r'\btbd\b', text, re.IGNORECASE):
            return PickOutcome("PENDIENTE", cuota, motivo="Pitcher TBD: omitir auditoría")

        # Sentido (default over si no hay sentido explícito; común en props K)
        text_lower = text.lower()
        if re.search(r'\b(over|m[aá]s\s+de|sobre)\b', text_lower):
            sentido = "over"
        elif re.search(r'\b(under|menos\s+de|bajo)\b', text_lower):
            sentido = "under"
        else:
            sentido = "over"

        # Excluir el "9" de "K/9" antes de extraer la línea.
        text_for_line = re.sub(r'k\s*/\s*9', '', text, flags=re.IGNORECASE)
        m = re.search(r'(\d+(?:\.\d+)?)', text_for_line)
        if not m:
            return PickOutcome("PENDIENTE", cuota, motivo="No se pudo extraer línea K")
        try:
            linea = float(m.group(1))
        except ValueError:
            return PickOutcome("PENDIENTE", cuota, motivo=f"Línea K inválida: {m.group(1)}")
        if linea <= 0:
            return PickOutcome("PENDIENTE", cuota, motivo="Línea K es 0: omitir (Req 2.9)")

        # Extraer nombre del pitcher quitando keywords y números.
        nombre_pitcher = re.sub(
            r'\b(over|under|m[aá]s\s+de|menos\s+de|sobre|bajo|k|ks|strikeouts?|ponches?|\d+(?:\.\d+)?)\b',
            '',
            text,
            flags=re.IGNORECASE,
        ).strip(' :-')
        if not nombre_pitcher:
            return PickOutcome("PENDIENTE", cuota, motivo="No se pudo extraer pitcher")

        matched = None
        best_score = 0.0
        for ko in result.strikeouts:
            score = _fuzzy_score(nombre_pitcher, ko.pitcher)
            if score >= FUZZY_HIGH_THRESHOLD and score > best_score:
                matched = ko
                best_score = score

        if matched is None:
            # Pitcher no figura en boxscore: PERDIDA (no lanzó / no se encontró).
            return PickOutcome(
                "PERDIDA",
                cuota,
                motivo=f"Pitcher '{nombre_pitcher}' no figura en strikeouts del juego",
            )

        if sentido == "over":
            outcome = "GANADA" if matched.strike_outs > linea else "PERDIDA"
        else:
            outcome = "GANADA" if matched.strike_outs < linea else "PERDIDA"

        return PickOutcome(
            outcome,
            cuota,
            motivo=f"{matched.pitcher} K={matched.strike_outs} {sentido} {linea}",
        )

    # ------------------------------------------------------------------
    # Persistencia del audit trail — Task 9.1, Requirements 2.2, 2.3
    # ------------------------------------------------------------------
    def _persist_audit_trail(
        self,
        pick_id: int,
        game_pk: int,
        pick_type: PickType,
        resultado: str,
        cuota_usada: float,
        person_id: Optional[int] = None,
        cursor=None,
    ) -> bool:
        """
        Inserta una fila en `backtesting_audit` con la trazabilidad del cruce.

        INSERT OR REPLACE: si ya existía una fila para `pick_id`, se reemplaza.
        En la práctica solo se inserta una vez por pick_id, porque Req 2.3
        prohíbe revertir GANADA/PERDIDA en la tabla principal y `audit_pending`
        solo persiste cuando el UPDATE con `WHERE estado='PENDIENTE'` afectó
        una fila.

        Si se proporciona `cursor`, usa esa conexión (misma transacción que
        `audit_pending`); si no, abre su propia conexión.

        person_id es NULL para MONEYLINE/OVER_UNDER/HANDICAP, y el ID del
        bateador (HR) o pitcher (K) para los otros tipos.

        Returns:
            True si se ejecutó la inserción; False si la DB no está disponible
            o si los argumentos son inválidos.
        """
        if pick_id is None or pick_id <= 0:
            return False

        try:
            tipo_str = (
                pick_type.value if hasattr(pick_type, "value") else str(pick_type)
            )
            person_id_val = int(person_id) if person_id else None
            game_pk_val = int(game_pk) if game_pk else None
            row = (
                int(pick_id),
                game_pk_val,
                tipo_str,
                person_id_val,
                resultado,
                float(cuota_usada),
                datetime.now().isoformat(),
            )

            sql = (
                "INSERT OR REPLACE INTO backtesting_audit "
                "(pick_id, game_pk, pick_type, person_id, resultado, "
                " cuota_usada, auditado_en) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)"
            )

            if cursor is not None:
                cursor.execute(sql, row)
                return True

            if self.db is None:
                return False
            conn = self.db._connect()
            try:
                cur = conn.cursor()
                cur.execute(sql, row)
                conn.commit()
                return True
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"[_persist_audit_trail] pick_id={pick_id}: {e}")
            return False

    def _extract_person_id_for_audit(
        self,
        pick: BacktestPick,
        game: GameResult,
        pick_type: PickType,
    ) -> Optional[int]:
        """
        Devuelve el `personId` MLB asociado al pick para escribir en el audit trail:

          * HOME_RUN  -> personId del bateador conectado (si match fuzzy>=85%).
          * STRIKEOUTS -> personId del pitcher evaluado (si match fuzzy>=85%).
          * MONEYLINE / OVER_UNDER / HANDICAP -> None.

        No lanza: retorna None si no hay match suficiente.
        """
        raw = (pick.pick or "")
        if not raw:
            return None

        if pick_type == PickType.HOME_RUN:
            nombre = re.sub(
                r'\b(hr|home\s*runs?|jonr[oó]n|to\s+hit|home\s+run\s+prop)\b',
                '',
                raw,
                flags=re.IGNORECASE,
            ).strip(' :-')
            if not nombre:
                return None
            nombre_norm = _safe_normalize(nombre)
            best_pid: Optional[int] = None
            best_score: float = 0.0
            for hr in game.home_runs:
                if hr.home_runs <= 0:
                    continue
                score = _fuzzy_score(nombre_norm, hr.full_name)
                if score >= FUZZY_HIGH_THRESHOLD and score > best_score:
                    best_pid = hr.person_id
                    best_score = score
            return best_pid

        if pick_type == PickType.STRIKEOUTS:
            nombre_pitcher = re.sub(
                r'\b(over|under|m[aá]s\s+de|menos\s+de|sobre|bajo|k|ks|'
                r'strikeouts?|ponches?|\d+(?:\.\d+)?)\b',
                '',
                raw,
                flags=re.IGNORECASE,
            ).strip(' :-')
            if not nombre_pitcher:
                return None
            best_pid_k: Optional[int] = None
            best_score_k: float = 0.0
            for ko in game.strikeouts:
                score = _fuzzy_score(nombre_pitcher, ko.pitcher)
                if score >= FUZZY_HIGH_THRESHOLD and score > best_score_k:
                    best_pid_k = ko.person_id
                    best_score_k = score
            return best_pid_k

        return None

    # ------------------------------------------------------------------
    # load_results — utilidad para cargar GameResult[] desde JSON
    # ------------------------------------------------------------------
    def load_results(self) -> List[GameResult]:
        """
        Lee `self.results_path` y rehidrata a `list[GameResult]`.

        Comportamiento defensivo:
          - Si el archivo no existe -> [] (no lanza).
          - Si el archivo está corrupto -> [] (no lanza, log warning).
          - Si una entrada tiene `partial=True` (degradación del scraper)
            se omite: no es un resultado completo y `GameResult` exigiría
            invariantes que un partial no garantiza.
          - Una entrada inválida individual no aborta la carga: se loguea
            en debug y se continúa con el resto.
        """
        if not os.path.exists(self.results_path):
            return []

        try:
            with open(self.results_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.warning(
                f"[load_results] No se pudo leer {self.results_path}: {e}"
            )
            return []

        if not isinstance(data, list):
            return []

        # Solo estos campos son aceptados por GameResult.__init__.
        valid_keys = {
            "game_pk", "fecha", "away", "home", "away_score", "home_score",
            "winner", "margin", "total_runs", "venue", "status",
        }

        out: List[GameResult] = []
        for entry in data:
            if not isinstance(entry, dict):
                continue
            if entry.get("partial"):
                continue
            try:
                hr_list = [
                    HomeRunRecord(**h)
                    for h in entry.get("home_runs", [])
                    if isinstance(h, dict)
                ]
                k_list = [
                    StrikeoutRecord(**k)
                    for k in entry.get("strikeouts", [])
                    if isinstance(k, dict)
                ]
                kwargs = {k: v for k, v in entry.items() if k in valid_keys}
                kwargs["home_runs"] = hr_list
                kwargs["strikeouts"] = k_list
                out.append(GameResult(**kwargs))
            except Exception as e:
                logger.debug(
                    f"[load_results] Skip entry game_pk={entry.get('game_pk')}: {e}"
                )
                continue
        return out

    # ------------------------------------------------------------------
    # audit_pending — Requirements 2.2, 2.3
    # ------------------------------------------------------------------
    def audit_pending(self, dias: int = 15) -> AuditReport:
        """
        Audita todos los picks MLB en estado PENDIENTE de los últimos N días.

        Preconditions:
          - self.db es un DatabaseManager válido (o un objeto con `_connect()`
            que devuelva una conexión sqlite3 sobre la tabla `backtesting`).
          - El archivo `self.results_path` cubre al menos esta ventana.

        Postconditions:
          - Cada pick PENDIENTE auditado queda con estado terminal
            (GANADA/PERDIDA) y cuota no nula, salvo:
              * REVIEW (fuzzy 70-84%) -> sigue PENDIENTE (Req 2.8).
              * Línea/sentido OU/K inválidos o pitcher TBD -> PENDIENTE (Req 2.9).
              * Sin GameResult emparejable -> PENDIENTE.
          - Un pick GANADA/PERDIDA NUNCA se modifica (Req 2.3): la cláusula
            UPDATE incluye `WHERE estado = 'PENDIENTE'`.
          - Devuelve un AuditReport con los conteos.
        """
        report = AuditReport()
        if self.db is None:
            return report

        # 1) Cargar resultados reales (si no hay, no se puede auditar nada).
        results = self.load_results()
        if not results:
            return report

        # 2) Calcular ventana de fechas.
        fecha_min = (datetime.now() - timedelta(days=dias)).strftime("%Y-%m-%d")

        # 3) Leer picks PENDIENTE de MLB en la ventana.
        try:
            conn = self.db._connect()
        except Exception as e:
            logger.error(f"[audit_pending] No se pudo abrir DB: {e}")
            return report

        try:
            cursor = conn.cursor()
            # Defensa: asegurar que la tabla `backtesting_audit` existe en
            # bases de datos antiguas creadas antes de Task 9.1. Idempotente.
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS backtesting_audit (
                    pick_id      INTEGER PRIMARY KEY,
                    game_pk      INTEGER,
                    pick_type    TEXT,
                    person_id    INTEGER,
                    resultado    TEXT,
                    cuota_usada  REAL,
                    auditado_en  TEXT
                )
                """
            )
            cursor.execute(
                """
                SELECT id, fecha, deporte, evento, pick, cuota, estado
                FROM backtesting
                WHERE deporte = 'MLB'
                  AND estado = 'PENDIENTE'
                  AND fecha >= ?
                """,
                (fecha_min,),
            )
            rows = cursor.fetchall()
            report.total_pendientes = len(rows)

            # 4) Iterar y auditar uno a uno.
            for row in rows:
                pick_id, fecha, deporte, evento, pick_text, cuota_db, estado_db = row

                # Defensa: si por alguna razón el estado ya no es PENDIENTE
                # (otra corrida, race condition), respetar el terminal (Req 2.3).
                if estado_db != "PENDIENTE":
                    report.omitidos_terminal += 1
                    continue

                pick = BacktestPick(
                    id=pick_id,
                    fecha=fecha,
                    deporte=deporte,
                    evento=evento or "",
                    pick=pick_text or "",
                    cuota=cuota_db,
                    estado=estado_db,
                )

                # 4a) Match con un GameResult.
                game, status = self.match_game_with_status(pick, results)

                if status == MatchStatus.NO_MATCH:
                    report.sin_resultado += 1
                    continue

                if status == MatchStatus.REVIEW:
                    # Mantener PENDIENTE (Req 2.8). No se persiste cambio.
                    report.revision += 1
                    continue

                # status == EXACT pero por defensa, asegurar game no nulo.
                if game is None:
                    report.sin_resultado += 1
                    continue

                # 4b) Evaluar.
                outcome = self.evaluate(pick, game, fuzzy_status=status)

                if outcome.estado == "PENDIENTE":
                    # OU/K con línea inválida, pitcher TBD, etc.
                    report.revision += 1
                    continue

                # 4c) Persistir SOLO si sigue PENDIENTE en la DB. La cláusula
                # `AND estado = 'PENDIENTE'` es la implementación canónica del
                # Req 2.3: nunca sobrescribimos un estado terminal.
                cursor.execute(
                    """
                    UPDATE backtesting
                    SET estado = ?, cuota = ?
                    WHERE id = ?
                      AND estado = 'PENDIENTE'
                    """,
                    (outcome.estado, float(outcome.cuota_usada), pick_id),
                )

                if cursor.rowcount > 0:
                    if outcome.estado == "GANADA":
                        report.auditados_ganada += 1
                    else:
                        report.auditados_perdida += 1

                    # Task 9.1: persistir trazabilidad en backtesting_audit
                    # usando el MISMO cursor (misma transacción) para que el
                    # commit final agrupe ambas escrituras de forma atómica.
                    pick_type_eval = self.classify_pick(pick.pick or "")
                    person_id_eval = self._extract_person_id_for_audit(
                        pick, game, pick_type_eval
                    )
                    self._persist_audit_trail(
                        pick_id=pick_id,
                        game_pk=game.game_pk,
                        pick_type=pick_type_eval,
                        resultado=outcome.estado,
                        cuota_usada=outcome.cuota_usada,
                        person_id=person_id_eval,
                        cursor=cursor,
                    )

                    report.detalles.append({
                        "id": pick_id,
                        "estado": outcome.estado,
                        "cuota_usada": float(outcome.cuota_usada),
                        "motivo": outcome.motivo,
                    })
                else:
                    # Otra corrida lo cambió antes que nosotros.
                    report.omitidos_terminal += 1

            conn.commit()
        except Exception as e:
            logger.error(f"[audit_pending] Error: {e}")
            try:
                conn.rollback()
            except Exception:
                pass
        finally:
            try:
                conn.close()
            except Exception:
                pass

        return report


__all__ = [
    "MLBBacktestAuditor",
    "MatchStatus",
    "PickOutcome",
    "AuditReport",
    "FUZZY_HIGH_THRESHOLD",
    "FUZZY_REVIEW_LOW",
    "FUZZY_REVIEW_HIGH",
    "DEFAULT_CUOTA_HR",
    "DEFAULT_CUOTA_OTROS",
]
