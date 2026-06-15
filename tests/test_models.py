# -*- coding: utf-8 -*-
"""
Unit tests para `motors.mlb_backtest_models`.

Cubre las invariantes declaradas en `__post_init__` de los dataclasses:
    GameResult, BacktestPick, Metrics, HomeRunRecord.

Validates: Requirements 1.2 (conservación del marcador), 3.1 (cota WR/total).
"""
from __future__ import annotations

import pytest

from motors.mlb_backtest_models import (
    BacktestPick,
    Classification,
    GameResult,
    HomeRunRecord,
    Metrics,
    PickType,
    StrikeoutRecord,
    calculate_win_rate_roi,
    validate_game_result_consistency,
)


# ---------------------------------------------------------------------------
# GameResult — invariantes del marcador
# ---------------------------------------------------------------------------
class TestGameResult:
    def test_valid_construction(self):
        gr = GameResult(
            game_pk=1, fecha="2025-06-01",
            away="A", home="B",
            away_score=5, home_score=3,
            winner="A", margin=2, total_runs=8,
            venue="X", home_runs=[], strikeouts=[],
            status="Final",
        )
        assert gr.game_pk == 1
        assert gr.total_runs == gr.away_score + gr.home_score
        assert gr.margin == abs(gr.away_score - gr.home_score)

    def test_total_runs_must_equal_sum(self):
        with pytest.raises(ValueError, match="total_runs"):
            GameResult(
                game_pk=1, fecha="2025-06-01",
                away="A", home="B",
                away_score=5, home_score=3,
                winner="A", margin=2, total_runs=99,  # inconsistente
                venue="X", home_runs=[], strikeouts=[],
            )

    def test_winner_must_be_higher_scoring_team(self):
        # winner = "A" pero "A" tiene menos carreras => debe fallar
        with pytest.raises(ValueError, match="no es mayor"):
            GameResult(
                game_pk=2, fecha="2025-06-01",
                away="A", home="B",
                away_score=2, home_score=5,
                winner="A", margin=3, total_runs=7,
                venue="X", home_runs=[], strikeouts=[],
            )

    def test_winner_must_be_one_of_the_teams(self):
        with pytest.raises(ValueError, match="winner"):
            GameResult(
                game_pk=3, fecha="2025-06-01",
                away="A", home="B",
                away_score=5, home_score=3,
                winner="C", margin=2, total_runs=8,  # C no es ninguno
                venue="X", home_runs=[], strikeouts=[],
            )

    def test_margin_must_match_abs_diff(self):
        with pytest.raises(ValueError, match="margin"):
            GameResult(
                game_pk=4, fecha="2025-06-01",
                away="A", home="B",
                away_score=5, home_score=3,
                winner="A", margin=99, total_runs=8,  # margin incorrecto
                venue="X", home_runs=[], strikeouts=[],
            )

    def test_negative_score_rejected(self):
        with pytest.raises(ValueError, match="away_score"):
            GameResult(
                game_pk=5, fecha="2025-06-01",
                away="A", home="B",
                away_score=-1, home_score=3,
                winner="B", margin=4, total_runs=2,
                venue="X", home_runs=[], strikeouts=[],
            )

    def test_game_pk_must_be_positive_int(self):
        with pytest.raises(ValueError, match="game_pk"):
            GameResult(
                game_pk=0, fecha="2025-06-01",
                away="A", home="B",
                away_score=5, home_score=3,
                winner="A", margin=2, total_runs=8,
                venue="X", home_runs=[], strikeouts=[],
            )

    def test_home_run_record_with_zero_hr_rejected(self):
        # HomeRunRecord no se valida en su __post_init__ (no tiene), pero
        # GameResult sí valida: home_runs >= 1 cuando aparece en la lista.
        with pytest.raises(ValueError, match="home_runs"):
            GameResult(
                game_pk=6, fecha="2025-06-01",
                away="A", home="B",
                away_score=5, home_score=3,
                winner="A", margin=2, total_runs=8,
                venue="X",
                home_runs=[
                    HomeRunRecord(person_id=1, full_name="X", equipo="A", home_runs=0)
                ],
                strikeouts=[],
            )


# ---------------------------------------------------------------------------
# BacktestPick — estado / deporte
# ---------------------------------------------------------------------------
class TestBacktestPick:
    def test_default_pendiente(self):
        p = BacktestPick(
            id=1, fecha="2025-06-01", deporte="MLB",
            evento="A vs B", pick="A ML",
        )
        assert p.estado == "PENDIENTE"
        assert p.cuota is None

    def test_invalid_state_rejected(self):
        with pytest.raises(ValueError, match="estado"):
            BacktestPick(
                id=1, fecha="2025-06-01", deporte="MLB",
                evento="A vs B", pick="A ML",
                estado="DESCONOCIDA",
            )

    def test_non_mlb_sport_rejected(self):
        with pytest.raises(ValueError, match="MLB"):
            BacktestPick(
                id=1, fecha="2025-06-01", deporte="NBA",
                evento="A vs B", pick="A ML",
            )


# ---------------------------------------------------------------------------
# Metrics — cota de hits/win_rate/last_10
# ---------------------------------------------------------------------------
class TestMetrics:
    def test_valid_metrics(self):
        m = Metrics(total=10, hits=6, win_rate=60.0, profit=4.5, roi=45.0,
                    last_10=['W', 'L', 'W'])
        assert m.win_rate == 60.0

    def test_hits_cannot_exceed_total(self):
        with pytest.raises(ValueError, match="hits"):
            Metrics(total=5, hits=6, win_rate=120.0, profit=1.0, roi=20.0, last_10=[])

    def test_win_rate_out_of_range(self):
        with pytest.raises(ValueError, match="win_rate"):
            Metrics(total=10, hits=5, win_rate=120.0, profit=1.0, roi=20.0, last_10=[])

    def test_last_10_size_capped(self):
        with pytest.raises(ValueError, match="last_10"):
            Metrics(
                total=10, hits=5, win_rate=50.0, profit=0.0, roi=0.0,
                last_10=['W'] * 11,
            )

    def test_last_10_invalid_letter(self):
        with pytest.raises(ValueError, match="last_10"):
            Metrics(
                total=10, hits=5, win_rate=50.0, profit=0.0, roi=0.0,
                last_10=['W', 'X'],
            )


# ---------------------------------------------------------------------------
# Helpers — validate_game_result_consistency / calculate_win_rate_roi
# ---------------------------------------------------------------------------
class TestHelpers:
    def test_consistency_no_duplicates(self):
        g1 = GameResult(
            game_pk=1, fecha="2025-06-01",
            away="A", home="B", away_score=2, home_score=1,
            winner="A", margin=1, total_runs=3,
            venue="X", home_runs=[], strikeouts=[],
        )
        g2 = GameResult(
            game_pk=2, fecha="2025-06-01",
            away="C", home="D", away_score=4, home_score=1,
            winner="C", margin=3, total_runs=5,
            venue="Y", home_runs=[], strikeouts=[],
        )
        assert validate_game_result_consistency([g1, g2]) is True

    def test_consistency_detects_duplicates(self):
        g1 = GameResult(
            game_pk=1, fecha="2025-06-01",
            away="A", home="B", away_score=2, home_score=1,
            winner="A", margin=1, total_runs=3,
            venue="X", home_runs=[], strikeouts=[],
        )
        # Mismo game_pk -> duplicado
        g2 = GameResult(
            game_pk=1, fecha="2025-06-01",
            away="C", home="D", away_score=4, home_score=1,
            winner="C", margin=3, total_runs=5,
            venue="Y", home_runs=[], strikeouts=[],
        )
        assert validate_game_result_consistency([g1, g2]) is False

    def test_calculate_win_rate_roi_zero_total(self):
        wr, roi = calculate_win_rate_roi(hits=0, total=0, profit=0.0)
        assert wr == 0.0
        assert roi == 0.0

    def test_calculate_win_rate_roi_basic(self):
        wr, roi = calculate_win_rate_roi(hits=6, total=10, profit=4.5)
        assert wr == 60.0
        assert roi == 45.0


# ---------------------------------------------------------------------------
# Enums sanity
# ---------------------------------------------------------------------------
def test_classification_values():
    assert {c.value for c in Classification} == {
        "ELITE", "CONFIANZA", "RIESGO", "EVITAR"
    }


def test_pick_type_values():
    assert {p.value for p in PickType} == {
        "HOME_RUN", "MONEYLINE", "OVER_UNDER", "STRIKEOUTS", "HANDICAP"
    }


def test_strikeout_record_basic():
    k = StrikeoutRecord(
        person_id=543037, pitcher="Gerrit Cole",
        equipo="New York Yankees", strike_outs=10,
    )
    assert k.strike_outs == 10
    assert k.pitcher == "Gerrit Cole"
