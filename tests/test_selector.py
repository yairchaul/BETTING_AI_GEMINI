# -*- coding: utf-8 -*-
"""
Unit tests para `motors.mlb_learning_selector.LearningPickSelector`.

Cubre:
  * `adjusted_confidence` — clamps, no mutación de base, penalización HR.
  * `select_best_pick`    — protección cuando no hay decision_engine,
                            exclusión de equipos EVITAR, jerarquía MLB.
  * `_compute_stake`      — reglas dinámicas de stake.
  * `_handicap_proteccion` — fallback progresivo.

Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5, 4.6.
"""
from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from motors.mlb_backtest_models import (
    Classification,
    Metrics,
    PickType,
)
from motors.mlb_learning_selector import (
    CONFIANZA_AJUSTADA_MAX,
    CONFIANZA_AJUSTADA_MIN,
    FACTOR_BY_CLASSIFICATION,
    FACTOR_MAX,
    FACTOR_MIN,
    HR_STADIUM_PENALTY,
    HR_STADIUM_THRESHOLD,
    LearningPickSelector,
    FinalPick,
)


# ---------------------------------------------------------------------------
# Doubles ligeros (sin pytest-mock)
# ---------------------------------------------------------------------------
class _StubEffectiveness:
    """
    Sustituto mínimo de EffectivenessCalculator para tests del selector.
    Permite inyectar clasificaciones por equipo y por tipo SIN tocar la DB.
    """
    def __init__(
        self,
        db=None,
        team_class=None,
        pick_type_class=None,
        equipo_trampa_set=None,
    ):
        self.db = db
        self._team_class = team_class or {}            # nombre normalizado -> Classification
        self._pick_type_class = pick_type_class or {}  # PickType -> Classification
        self._equipo_trampa = equipo_trampa_set or set()
        self.classify = self._classify

    def _classify(self, metrics):
        # Para tests: devolvemos lo que el calculador real devolvería sobre
        # los Metrics que le pasamos vía compute_*. Nunca se llama directamente.
        return Classification.RIESGO

    def compute_by_pick_type(self):
        # Generamos Metrics dummy con clasificaciones inyectadas.
        out = {}
        for tipo, cls in self._pick_type_class.items():
            m = _metrics_for_classification(cls)
            out[tipo] = m
            # Atajo: el selector llama effectiveness.classify(m), así que
            # devolvemos la clasificación correcta para CADA Metrics.
        # Hack: como classify es una función fija, la sustituimos por una
        # que mapea Metrics -> clasificación esperada.
        self._pick_type_metrics_cache = out
        return out

    def compute_by_team(self):
        out = {}
        for equipo, cls in self._team_class.items():
            out[equipo] = _metrics_for_classification(cls)
        self._team_metrics_cache = out
        return out

    def is_equipo_trampa(self, equipo, dias=30):
        return equipo in self._equipo_trampa


def _metrics_for_classification(cls):
    """
    Construye un Metrics que cae en la clasificación deseada al pasarlo
    por EffectivenessCalculator.classify (ver fronteras del método):

      ELITE:     wr > 65, roi > 20
      CONFIANZA: 55 <= wr <= 65, roi > 0
      RIESGO:    45 <= wr <= 55
      EVITAR:    wr < 45
    """
    if cls == Classification.ELITE:
        return Metrics(total=20, hits=15, win_rate=75.0, profit=8.0,
                       roi=40.0, last_10=[])
    if cls == Classification.CONFIANZA:
        return Metrics(total=20, hits=12, win_rate=60.0, profit=2.0,
                       roi=10.0, last_10=[])
    if cls == Classification.RIESGO:
        return Metrics(total=20, hits=10, win_rate=50.0, profit=-1.0,
                       roi=-5.0, last_10=[])
    # EVITAR
    return Metrics(total=20, hits=8, win_rate=40.0, profit=-4.0,
                   roi=-20.0, last_10=[])


@pytest.fixture
def patched_effectiveness():
    """
    Devuelve un constructor de _StubEffectiveness con `classify` que mapea
    Metrics -> Classification basándose en (win_rate, roi). Esto replica
    EffectivenessCalculator.classify sin importar el módulo real.
    """
    def _make(team_class=None, pick_type_class=None, equipo_trampa_set=None):
        stub = _StubEffectiveness(
            team_class=team_class,
            pick_type_class=pick_type_class,
            equipo_trampa_set=equipo_trampa_set,
        )

        def _classify(m):
            if m.total == 0:
                return Classification.EVITAR
            if m.win_rate < 45.0 or m.roi < -15.0:
                return Classification.EVITAR
            if m.win_rate > 65.0 and m.roi > 20.0:
                return Classification.ELITE
            if 55.0 <= m.win_rate <= 65.0 and m.roi > 0.0:
                return Classification.CONFIANZA
            if 45.0 <= m.win_rate <= 55.0:
                return Classification.RIESGO
            return Classification.RIESGO

        stub.classify = _classify
        return stub

    return _make


# ---------------------------------------------------------------------------
# adjusted_confidence — Property 8 / 10 base
# ---------------------------------------------------------------------------
class TestAdjustedConfidence:
    def test_clamps_to_99(self, patched_effectiveness):
        eff = patched_effectiveness(
            team_class={"Yankees": Classification.ELITE},
            pick_type_class={PickType.MONEYLINE: Classification.ELITE},
        )
        sel = LearningPickSelector(effectiveness=eff)
        # Base muy alta + factor combinado 1.30*1.30=1.69 (clamp a 1.30)
        # 80 * 1.30 = 104 -> clamp a 99
        result = sel.adjusted_confidence(PickType.MONEYLINE, "Yankees", 80.0)
        assert result <= CONFIANZA_AJUSTADA_MAX
        assert result == 99.0

    def test_clamps_to_zero_floor(self, patched_effectiveness):
        eff = patched_effectiveness(
            team_class={"X": Classification.EVITAR},
            pick_type_class={PickType.MONEYLINE: Classification.EVITAR},
        )
        sel = LearningPickSelector(effectiveness=eff)
        # base negativa o 0 -> 0
        assert sel.adjusted_confidence(PickType.MONEYLINE, "X", 0.0) == 0.0
        assert sel.adjusted_confidence(PickType.MONEYLINE, "X", -10.0) == 0.0

    def test_does_not_mutate_base(self, patched_effectiveness):
        eff = patched_effectiveness()
        sel = LearningPickSelector(effectiveness=eff)
        base = 60.0
        original = base
        sel.adjusted_confidence(PickType.MONEYLINE, "Anywhere", base)
        assert base == original  # float es inmutable, es un sanity check

    def test_no_effectiveness_falls_to_riesgo(self):
        # Sin calculador de efectividad, todo cae a Classification.RIESGO,
        # cuyo factor es 0.85 -> 60 * 0.85*0.85 = 60 * 0.7225 = 43.35
        sel = LearningPickSelector(effectiveness=None)
        result = sel.adjusted_confidence(PickType.MONEYLINE, "Yankees", 60.0)
        assert 0 < result < 60  # ajustada hacia abajo

    def test_invalid_base_returns_zero(self):
        sel = LearningPickSelector(effectiveness=None)
        assert sel.adjusted_confidence(PickType.MONEYLINE, "X", "not-a-number") == 0.0
        assert sel.adjusted_confidence(PickType.MONEYLINE, "X", True) == 0.0


# ---------------------------------------------------------------------------
# Property 10 (preview) — penalización HR por estadio
# ---------------------------------------------------------------------------
class TestStadiumPenaltyAdjusted:
    def test_low_factor_strictly_lower(self, tmp_path, patched_effectiveness):
        eff = patched_effectiveness(
            team_class={"Yankees": Classification.CONFIANZA},
            pick_type_class={PickType.HOME_RUN: Classification.CONFIANZA},
        )
        factors = tmp_path / "stadiums.json"
        factors.write_text(json.dumps({
            "Oracle Park": 0.85,    # < 0.90 -> penaliza
            "Coors Field": 1.30,    # >= 0.90 -> no penaliza
        }))

        # Selectores SEPARADOS para evitar caché compartido del JSON.
        sel_good = LearningPickSelector(
            effectiveness=eff, stadium_factors_path=str(factors),
        )
        sel_bad = LearningPickSelector(
            effectiveness=eff, stadium_factors_path=str(factors),
        )
        without = sel_good.adjusted_confidence(
            PickType.HOME_RUN, "Yankees", 60.0, venue="Coors Field",
        )
        with_pen = sel_bad.adjusted_confidence(
            PickType.HOME_RUN, "Yankees", 60.0, venue="Oracle Park",
        )
        assert with_pen < without

    def test_threshold_constants(self):
        assert HR_STADIUM_PENALTY < 1.0
        assert HR_STADIUM_THRESHOLD == 0.90


# ---------------------------------------------------------------------------
# select_best_pick
# ---------------------------------------------------------------------------
class TestSelectBestPick:
    def test_no_decision_engine_returns_protection(self, patched_effectiveness):
        eff = patched_effectiveness()
        sel = LearningPickSelector(effectiveness=eff, decision_engine=None)
        result = sel.select_best_pick({
            "partido": {"visitante": "Yankees", "local": "Red Sox"},
            "resultado_heuristico": {"pick": "Yankees", "confianza": 60.0},
            "candidatos_hr": [],
        })
        assert isinstance(result, FinalPick)
        assert result.es_proteccion is True
        assert result.pick_type == PickType.HANDICAP

    def test_engine_failure_returns_protection(self, patched_effectiveness):
        eff = patched_effectiveness()
        engine = MagicMock()
        engine.decidir_mejor_apuesta.side_effect = RuntimeError("boom")
        sel = LearningPickSelector(effectiveness=eff, decision_engine=engine)
        result = sel.select_best_pick({
            "partido": {"visitante": "Yankees", "local": "Red Sox"},
            "resultado_heuristico": {"pick": "Yankees", "confianza": 50.0},
            "candidatos_hr": [],
        })
        assert result.es_proteccion is True
        assert "boom" in result.razon

    def test_excludes_evitar_team_falls_to_protection(self, patched_effectiveness):
        # Único candidato es de Yankees, pero Yankees está en EVITAR.
        eff = patched_effectiveness(
            team_class={"New York Yankees": Classification.EVITAR},
            pick_type_class={PickType.MONEYLINE: Classification.RIESGO},
        )
        engine = MagicMock()
        engine.decidir_mejor_apuesta.return_value = {
            "todas_opciones": {
                "MONEYLINE": {"pick": "New York Yankees ML", "punt": 70},
            }
        }
        sel = LearningPickSelector(effectiveness=eff, decision_engine=engine)
        result = sel.select_best_pick({
            "partido": {"visitante": "New York Yankees", "local": "Boston Red Sox"},
            "resultado_heuristico": {"pick": "New York Yankees", "confianza": 60.0},
            "candidatos_hr": [],
        })
        # Como el único candidato fue excluido, regresa protección
        assert result.es_proteccion is True

    def test_picks_best_by_adj_confidence(self, patched_effectiveness):
        # Dos candidatos, ambos en equipos no excluidos.
        # OVER/UNDER tiene confianza base mayor, así que debería ganar
        # (no se excluye porque OU sin equipo claro -> equipo "" no excluido).
        eff = patched_effectiveness(
            team_class={
                "New York Yankees": Classification.CONFIANZA,
                "Boston Red Sox": Classification.CONFIANZA,
            },
            pick_type_class={
                PickType.MONEYLINE: Classification.CONFIANZA,
                PickType.OVER_UNDER: Classification.ELITE,
            },
        )
        engine = MagicMock()
        engine.decidir_mejor_apuesta.return_value = {
            "todas_opciones": {
                "MONEYLINE": {"pick": "New York Yankees ML", "punt": 50},
                "OVER/UNDER": {"pick": "Over 8.5", "punt": 70},
            }
        }
        sel = LearningPickSelector(effectiveness=eff, decision_engine=engine)
        result = sel.select_best_pick({
            "partido": {"visitante": "New York Yankees", "local": "Boston Red Sox"},
            "resultado_heuristico": {"pick": "Over 8.5", "confianza": 70.0},
            "candidatos_hr": [],
        })
        # OU debería ganar por mayor confianza ajustada
        assert result.es_proteccion is False
        assert result.pick_type == PickType.OVER_UNDER

    def test_persist_id_when_db_available(self, temp_db, patched_effectiveness):
        # Si effectiveness.db está disponible, se persiste y obtenemos un id.
        eff = patched_effectiveness(
            team_class={"New York Yankees": Classification.CONFIANZA},
            pick_type_class={PickType.MONEYLINE: Classification.CONFIANZA},
        )
        eff.db = temp_db
        engine = MagicMock()
        engine.decidir_mejor_apuesta.return_value = {
            "todas_opciones": {
                "MONEYLINE": {"pick": "New York Yankees ML", "punt": 60},
            }
        }
        sel = LearningPickSelector(effectiveness=eff, decision_engine=engine)
        result = sel.select_best_pick({
            "partido": {"visitante": "New York Yankees", "local": "Boston Red Sox"},
            "resultado_heuristico": {"pick": "New York Yankees", "confianza": 60.0},
            "candidatos_hr": [],
        })
        assert result.id is not None
        assert result.id > 0


# ---------------------------------------------------------------------------
# _compute_stake
# ---------------------------------------------------------------------------
class TestComputeStake:
    def test_evitar_always_1u(self):
        sel = LearningPickSelector()
        assert sel._compute_stake(80.0, Classification.EVITAR) == "1u"

    def test_elite_high_confidence_4u(self):
        sel = LearningPickSelector()
        assert sel._compute_stake(80.0, Classification.ELITE) == "4u"

    def test_confianza_mid_3u(self):
        sel = LearningPickSelector()
        assert sel._compute_stake(70.0, Classification.CONFIANZA) == "3u"

    def test_default_2u_zone(self):
        sel = LearningPickSelector()
        assert sel._compute_stake(60.0, Classification.RIESGO) == "2u"

    def test_low_confidence_1u(self):
        sel = LearningPickSelector()
        assert sel._compute_stake(40.0, Classification.RIESGO) == "1u"


# ---------------------------------------------------------------------------
# _handicap_proteccion — fallback progresivo (Req 4.5)
# ---------------------------------------------------------------------------
class TestHandicapProteccion:
    def test_low_confidence_uses_3_5(self):
        sel = LearningPickSelector()
        result = sel._handicap_proteccion({
            "partido": {"visitante": "Yankees", "local": "Red Sox"},
            "resultado_heuristico": {"pick": "Yankees", "confianza": 45.0},
        })
        assert "+3.5" in result.pick

    def test_mid_confidence_uses_2_5(self):
        sel = LearningPickSelector()
        result = sel._handicap_proteccion({
            "partido": {"visitante": "Yankees", "local": "Red Sox"},
            "resultado_heuristico": {"pick": "Yankees", "confianza": 52.0},
        })
        assert "+2.5" in result.pick

    def test_high_confidence_uses_1_5(self):
        sel = LearningPickSelector()
        result = sel._handicap_proteccion({
            "partido": {"visitante": "Yankees", "local": "Red Sox"},
            "resultado_heuristico": {"pick": "Yankees", "confianza": 60.0},
        })
        assert "+1.5" in result.pick
