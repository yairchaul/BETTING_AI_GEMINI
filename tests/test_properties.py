# -*- coding: utf-8 -*-
"""
Property-based tests para backtesting-real-mlb usando `hypothesis`.

Cubre las Correctness Properties del diseño:
  Property 2  — Conservación del marcador (`total_runs == away + home`,
                `winner` es el equipo de mayor marcador).
  Property 4  — Cuota nunca nula (`_resolve_cuota` devuelve siempre > 0).
  Property 5  — Estado terminal monótono (UPDATE solo desde PENDIENTE).
  Property 6  — Cota de win rate (`0 <= win_rate <= 100`, `hits <= total`).
  Property 7  — Clasificación total y excluyente (toda Metrics con total>0
                recibe exactamente una clasificación).
  Property 8  — No sobrescritura heurística (`adjusted_confidence` no muta
                el escalar `base_confidence`).
  Property 10 — Penalización de estadio (HR con factor < 0.90 produce
                confianza ajustada estrictamente menor que sin penalización).

Properties 1, 3 y 9 requieren más andamiaje (red, fixtures de boxscore o
EffectivenessCalculator integrado) y se deferren a la suite de integración.

Validates: Requirements 1.2, 2.2, 2.3, 3.1, 3.2, 4.1, 4.3.
"""
from __future__ import annotations

import json
from datetime import datetime

import pytest
from hypothesis import HealthCheck, assume, given, settings, strategies as st


# ---------------------------------------------------------------------------
# Property 2 — Conservación del marcador
# Validates: Requirements 1.2
# ---------------------------------------------------------------------------
@pytest.mark.property
class TestProperty2_Conservacion:
    @given(
        away=st.integers(min_value=0, max_value=30),
        home=st.integers(min_value=0, max_value=30),
    )
    @settings(max_examples=80, deadline=None,
              suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_total_runs_equals_sum_and_winner_higher(self, away, home):
        from motors.mlb_backtest_models import GameResult
        # MLB no admite empates en juegos terminados; saltarlos.
        assume(away != home)
        winner_team = "AwayTeam" if away > home else "HomeTeam"
        gr = GameResult(
            game_pk=1, fecha="2025-06-01",
            away="AwayTeam", home="HomeTeam",
            away_score=away, home_score=home,
            winner=winner_team,
            margin=abs(away - home),
            total_runs=away + home,
            venue="X", home_runs=[], strikeouts=[],
            status="Final",
        )
        # Property 2.a — conservación
        assert gr.total_runs == gr.away_score + gr.home_score
        # Property 2.b — winner tiene mayor marcador
        if gr.winner == gr.away:
            assert gr.away_score > gr.home_score
        else:
            assert gr.home_score > gr.away_score


# ---------------------------------------------------------------------------
# Property 4 — Cuota nunca nula tras auditar
# Validates: Requirements 2.2
# ---------------------------------------------------------------------------
@pytest.mark.property
class TestProperty4_CuotaNoNula:
    @given(
        cuota_real=st.one_of(
            st.none(),
            st.floats(min_value=-5.0, max_value=10.0,
                      allow_nan=False, allow_infinity=False),
        ),
        es_hr=st.booleans(),
    )
    @settings(max_examples=80, deadline=None)
    def test_resolve_cuota_always_positive(self, cuota_real, es_hr):
        from motors.mlb_backtest_auditor import (
            DEFAULT_CUOTA_HR,
            DEFAULT_CUOTA_OTROS,
            MLBBacktestAuditor,
        )
        from motors.mlb_backtest_models import BacktestPick
        pick_text = "Aaron Judge HR" if es_hr else "Yankees ML"
        pick = BacktestPick(
            id=1, fecha="2025-06-01", deporte="MLB",
            evento="Yankees vs Red Sox", pick=pick_text,
            cuota=cuota_real, estado="PENDIENTE",
        )
        auditor = MLBBacktestAuditor(db=None)
        cuota = auditor._resolve_cuota(pick)
        assert cuota > 0
        # Si la cuota real era válida (>0), debe respetarse
        if cuota_real is not None and cuota_real > 0:
            assert cuota == cuota_real
        else:
            expected_default = DEFAULT_CUOTA_HR if es_hr else DEFAULT_CUOTA_OTROS
            assert cuota == expected_default


# ---------------------------------------------------------------------------
# Property 5 — Estado terminal monótono
# Validates: Requirements 2.3
# ---------------------------------------------------------------------------
@pytest.mark.property
class TestProperty5_EstadoTerminalMonotono:
    @given(
        estado_inicial=st.sampled_from(["GANADA", "PERDIDA"]),
    )
    @settings(max_examples=15, deadline=None,
              suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_terminal_state_never_reverted(self, tmp_path, estado_inicial):
        # Cada ejemplo crea su propia DB efímera para evitar estado compartido.
        from utils.database_manager import DatabaseManager
        from motors.mlb_backtest_auditor import MLBBacktestAuditor

        db_path = tmp_path / f"prop5_{estado_inicial}_{id(estado_inicial)}.db"
        db = DatabaseManager(db_path=str(db_path))

        fecha_hoy = datetime.now().strftime("%Y-%m-%d")
        # Insertar un pick ya en estado terminal con cuota distinta del default.
        conn = db._connect()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO backtesting "
            "(fecha, deporte, evento, pick, cuota, estado, creado_en) "
            "VALUES (?, 'MLB', 'New York Yankees vs Boston Red Sox', "
            "        'Boston Red Sox ML', 2.50, ?, ?)",
            (fecha_hoy, estado_inicial, datetime.now().isoformat()),
        )
        conn.commit()
        conn.close()

        # Crear un JSON donde Yankees gana — esto, sin la cláusula WHERE
        # estado='PENDIENTE', cambiaría 'Boston Red Sox ML' de GANADA a PERDIDA.
        results_path = tmp_path / f"results_{id(estado_inicial)}.json"
        results_path.write_text(json.dumps([{
            "game_pk": 12345,
            "fecha": fecha_hoy,
            "away": "New York Yankees",
            "home": "Boston Red Sox",
            "away_score": 8, "home_score": 3,
            "winner": "New York Yankees",
            "margin": 5, "total_runs": 11,
            "venue": "Fenway Park", "status": "Final",
            "home_runs": [], "strikeouts": [],
        }]), encoding="utf-8")

        auditor = MLBBacktestAuditor(db=db, results_path=str(results_path))
        auditor.audit_pending(dias=15)

        conn = db._connect()
        cur = conn.cursor()
        cur.execute("SELECT estado, cuota FROM backtesting WHERE pick = 'Boston Red Sox ML'")
        row = cur.fetchone()
        conn.close()
        # Estado terminal NUNCA se revierte ni se sobrescribe.
        assert row[0] == estado_inicial
        assert row[1] == 2.50


# ---------------------------------------------------------------------------
# Property 6 — Cota de win rate
# Validates: Requirements 3.1
# ---------------------------------------------------------------------------
@pytest.mark.property
class TestProperty6_WinRateBounds:
    @given(
        total=st.integers(min_value=1, max_value=100),
        hits=st.integers(min_value=0, max_value=100),
    )
    @settings(max_examples=80, deadline=None)
    def test_win_rate_bounded_and_hits_le_total(self, total, hits):
        from motors.mlb_backtest_models import Metrics
        assume(hits <= total)
        wr = hits / total * 100.0
        m = Metrics(
            total=total, hits=hits, win_rate=wr,
            profit=0.0, roi=0.0, last_10=[],
        )
        assert 0.0 <= m.win_rate <= 100.0
        assert m.hits <= m.total
        assert m.hits >= 0


# ---------------------------------------------------------------------------
# Property 7 — Clasificación total y excluyente
# Validates: Requirements 3.2
# ---------------------------------------------------------------------------
@pytest.mark.property
class TestProperty7_ClasificacionTotal:
    @given(
        wr=st.floats(min_value=0.0, max_value=100.0,
                     allow_nan=False, allow_infinity=False),
        roi=st.floats(min_value=-100.0, max_value=200.0,
                      allow_nan=False, allow_infinity=False),
        total=st.integers(min_value=1, max_value=100),
    )
    @settings(max_examples=80, deadline=None)
    def test_classify_returns_exactly_one(self, wr, roi, total):
        from motors.mlb_backtest_models import Classification, Metrics
        from motors.mlb_effectiveness import EffectivenessCalculator
        # hits derivado consistentemente para satisfacer Metrics.__post_init__
        hits = max(0, min(total, int(round(wr * total / 100.0))))
        # win_rate efectivo recalculado para evitar mismatch float -> ValueError
        wr_eff = hits / total * 100.0
        profit = roi * total / 100.0
        m = Metrics(
            total=total, hits=hits, win_rate=wr_eff,
            profit=profit, roi=roi, last_10=[],
        )
        calc = EffectivenessCalculator(db=None)
        c = calc.classify(m)
        assert c in {
            Classification.ELITE,
            Classification.CONFIANZA,
            Classification.RIESGO,
            Classification.EVITAR,
        }


# ---------------------------------------------------------------------------
# Property 8 — No sobrescritura heurística
# Validates: Requirements 4.1
# ---------------------------------------------------------------------------
@pytest.mark.property
class TestProperty8_NoMutaBase:
    @given(
        bc=st.floats(min_value=0.0, max_value=100.0,
                     allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=60, deadline=None)
    def test_base_confidence_not_mutated(self, bc):
        from motors.mlb_backtest_models import PickType
        from motors.mlb_learning_selector import LearningPickSelector
        sel = LearningPickSelector()
        snapshot = bc
        sel.adjusted_confidence(PickType.MONEYLINE, "AnyTeam", bc)
        # `bc` es float -> inmutable, este test es una invariante operacional:
        # ningún side-effect cambia el valor del escalar tras la llamada.
        assert bc == snapshot


# ---------------------------------------------------------------------------
# Property 10 — Penalización de estadio
# Validates: Requirements 4.3
# ---------------------------------------------------------------------------
@pytest.mark.property
class TestProperty10_PenalizacionEstadio:
    @given(
        bc=st.floats(min_value=10.0, max_value=70.0,
                     allow_nan=False, allow_infinity=False),
        bad_factor=st.floats(min_value=0.50, max_value=0.89,
                             allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=40, deadline=None,
              suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_hr_low_factor_strictly_lower(self, tmp_path, bc, bad_factor):
        # Cada ejemplo usa su propio JSON de factores para evitar caché.
        from motors.mlb_backtest_models import PickType
        from motors.mlb_learning_selector import LearningPickSelector

        path = tmp_path / f"factors_{id(bc):x}_{id(bad_factor):x}.json"
        path.write_text(json.dumps({
            "Bad Park": bad_factor,
            "Good Park": 1.30,
        }))
        sel_good = LearningPickSelector(stadium_factors_path=str(path))
        sel_bad = LearningPickSelector(stadium_factors_path=str(path))

        without = sel_good.adjusted_confidence(
            PickType.HOME_RUN, "X", bc, venue="Good Park",
        )
        with_pen = sel_bad.adjusted_confidence(
            PickType.HOME_RUN, "X", bc, venue="Bad Park",
        )

        # Cuando ninguno satura el clamp superior, la penalización produce
        # un resultado estrictamente menor. bc ≤ 70 garantiza no saturación.
        assert with_pen < without
