# -*- coding: utf-8 -*-
"""
Unit tests para `motors.mlb_backtest_auditor`.

Cubre:
  * `classify_pick`     — clasificación textual a PickType (Req 2.7).
  * `match_game`        — emparejamiento por fecha + equipos (Req 2.7, 2.8).
  * `evaluate`          — los 5 tipos de pick (Req 2.1, 2.4, 2.5, 2.6, 2.9).
  * `_resolve_cuota`    — defaults 1.90 / 3.50 (Req 2.2).
  * `audit_pending`     — flujo end-to-end con SQLite temporal y Req 2.3
    (estado terminal nunca se sobrescribe).

Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta

import pytest

from motors.mlb_backtest_auditor import (
    DEFAULT_CUOTA_HR,
    DEFAULT_CUOTA_OTROS,
    FUZZY_HIGH_THRESHOLD,
    MatchStatus,
    MLBBacktestAuditor,
    PickOutcome,
)
from motors.mlb_backtest_models import (
    BacktestPick,
    GameResult,
    HomeRunRecord,
    PickType,
    StrikeoutRecord,
)


# ---------------------------------------------------------------------------
# classify_pick
# ---------------------------------------------------------------------------
class TestClassifyPick:
    @pytest.fixture
    def auditor(self):
        return MLBBacktestAuditor(db=None)

    @pytest.mark.parametrize("text,expected", [
        ("Yankees ML", PickType.MONEYLINE),
        ("Red Sox moneyline", PickType.MONEYLINE),
        ("Over 8.5", PickType.OVER_UNDER),
        ("Under 7.5 runs", PickType.OVER_UNDER),
        ("Más de 9.0", PickType.OVER_UNDER),
        ("Yankees +1.5", PickType.HANDICAP),
        ("Dodgers -1.5", PickType.HANDICAP),
        ("Aaron Judge HR", PickType.HOME_RUN),
        ("Mike Trout home run", PickType.HOME_RUN),
        ("Shohei jonrón", PickType.HOME_RUN),
        ("Gerrit Cole Over 7.5 K", PickType.STRIKEOUTS),
        ("Snell ponches +6.5", PickType.STRIKEOUTS),
    ])
    def test_classifies_text(self, auditor, text, expected):
        assert auditor.classify_pick(text) == expected

    def test_empty_defaults_to_moneyline(self, auditor):
        assert auditor.classify_pick("") == PickType.MONEYLINE


# ---------------------------------------------------------------------------
# match_game
# ---------------------------------------------------------------------------
class TestMatchGame:
    @pytest.fixture
    def auditor(self):
        return MLBBacktestAuditor(db=None)

    def test_exact_match(self, auditor, results_list, make_pick):
        pick = make_pick(
            "New York Yankees ML",
            evento="New York Yankees vs Boston Red Sox",
            fecha="2025-06-01",
        )
        gr = auditor.match_game(pick, results_list)
        assert gr is not None
        assert gr.game_pk == 12345

    def test_date_mismatch_returns_none(self, auditor, results_list, make_pick):
        pick = make_pick(
            "New York Yankees ML",
            evento="New York Yankees vs Boston Red Sox",
            fecha="2099-01-01",  # fecha que no existe
        )
        assert auditor.match_game(pick, results_list) is None

    def test_no_match_returns_none(self, auditor, results_list, make_pick):
        pick = make_pick(
            "Houston Astros ML",
            evento="Houston Astros vs Texas Rangers",
            fecha="2025-06-01",
        )
        gr = auditor.match_game(pick, results_list)
        assert gr is None

    def test_match_with_status_exact(self, auditor, results_list, make_pick):
        pick = make_pick(
            "New York Yankees ML",
            evento="New York Yankees vs Boston Red Sox",
            fecha="2025-06-01",
        )
        gr, status = auditor.match_game_with_status(pick, results_list)
        assert status == MatchStatus.EXACT
        assert gr.game_pk == 12345


# ---------------------------------------------------------------------------
# evaluate — 5 tipos
# ---------------------------------------------------------------------------
class TestEvaluate:
    @pytest.fixture
    def auditor(self):
        return MLBBacktestAuditor(db=None)

    # ---- MONEYLINE ----
    def test_moneyline_winner_wins(self, auditor, sample_game_result, make_pick):
        pick = make_pick("New York Yankees ML")
        out = auditor.evaluate(pick, sample_game_result)
        assert out.estado == "GANADA"
        assert out.cuota_usada == DEFAULT_CUOTA_OTROS

    def test_moneyline_loser_loses(self, auditor, sample_game_result, make_pick):
        pick = make_pick("Boston Red Sox ML")
        out = auditor.evaluate(pick, sample_game_result)
        assert out.estado == "PERDIDA"

    # ---- OVER / UNDER ----
    def test_over_above_line_wins(self, auditor, sample_game_result, make_pick):
        # total=11, línea 8.5 -> Over GANADA
        pick = make_pick("Over 8.5", evento="Yankees vs Red Sox")
        out = auditor.evaluate(pick, sample_game_result)
        assert out.estado == "GANADA"

    def test_over_below_line_loses(self, auditor, sample_game_result, make_pick):
        pick = make_pick("Over 12.5")
        out = auditor.evaluate(pick, sample_game_result)
        assert out.estado == "PERDIDA"

    def test_under_below_line_wins(self, auditor, sample_game_result, make_pick):
        pick = make_pick("Under 12.5")
        out = auditor.evaluate(pick, sample_game_result)
        assert out.estado == "GANADA"

    def test_over_push_loses(self, auditor, sample_game_result, make_pick):
        # Línea 11 igual a total_runs -> push -> conservativo PERDIDA
        pick = make_pick("Over 11")
        out = auditor.evaluate(pick, sample_game_result)
        assert out.estado == "PERDIDA"
        assert "Push" in out.motivo

    def test_ou_no_sentido_pendiente_direct(self, auditor, sample_game_result, make_pick):
        # Sin sentido (over/under) extraíble: el evaluador OU directo deja PENDIENTE.
        pick = make_pick("8.5 runs")
        out = auditor._evaluate_over_under(pick, sample_game_result)
        assert out.estado == "PENDIENTE"
        assert "sentido" in out.motivo.lower()

    # ---- HANDICAP / RUN LINE ----
    def test_handicap_plus_15_covers_loss_by_1(self, auditor, make_pick):
        # Equipo perdió por 1 carrera -> +1.5 GANADA
        gr = GameResult(
            game_pk=999, fecha="2025-06-03",
            away="Yankees", home="Red Sox",
            away_score=3, home_score=4,
            winner="Red Sox", margin=1, total_runs=7,
            venue="X", home_runs=[], strikeouts=[],
        )
        pick = make_pick("Yankees +1.5", evento="Yankees vs Red Sox", fecha="2025-06-03")
        out = auditor.evaluate(pick, gr)
        assert out.estado == "GANADA"

    def test_handicap_minus_15_loses_when_win_by_1(self, auditor, make_pick):
        # Equipo ganó por 1 carrera -> -1.5 PERDIDA
        gr = GameResult(
            game_pk=998, fecha="2025-06-03",
            away="Yankees", home="Red Sox",
            away_score=4, home_score=3,
            winner="Yankees", margin=1, total_runs=7,
            venue="X", home_runs=[], strikeouts=[],
        )
        pick = make_pick("Yankees -1.5", evento="Yankees vs Red Sox", fecha="2025-06-03")
        out = auditor.evaluate(pick, gr)
        assert out.estado == "PERDIDA"

    def test_handicap_minus_15_wins_when_win_by_2_or_more(self, auditor, sample_game_result, make_pick):
        # Yankees ganaron 8-3 (margen 5) -> -1.5 GANADA
        pick = make_pick("New York Yankees -1.5")
        out = auditor.evaluate(pick, sample_game_result)
        assert out.estado == "GANADA"

    # ---- HOME RUN ----
    def test_hr_winner_by_personid(self, auditor, sample_game_result, make_pick):
        pick = make_pick("Aaron Judge HR")
        out = auditor.evaluate(pick, sample_game_result)
        assert out.estado == "GANADA"
        assert out.cuota_usada == DEFAULT_CUOTA_HR
        assert "592450" in out.motivo

    def test_hr_player_did_not_homer(self, auditor, sample_game_result, make_pick):
        pick = make_pick("Mike Trout HR")
        out = auditor.evaluate(pick, sample_game_result)
        assert out.estado == "PERDIDA"

    def test_hr_no_homers_in_game(self, auditor, sample_game_result_dodgers, make_pick):
        pick = make_pick("Mookie Betts HR",
                         evento="Los Angeles Dodgers vs San Francisco Giants",
                         fecha="2025-06-02")
        out = auditor.evaluate(pick, sample_game_result_dodgers)
        assert out.estado == "PERDIDA"

    # ---- STRIKEOUTS ----
    def test_k_over_line_wins(self, auditor, sample_game_result, make_pick):
        # Cole = 10 K, línea 7.5 -> Over GANADA
        pick = make_pick("Gerrit Cole Over 7.5 K")
        out = auditor.evaluate(pick, sample_game_result)
        assert out.estado == "GANADA"

    def test_k_over_line_loses(self, auditor, sample_game_result, make_pick):
        pick = make_pick("Gerrit Cole Over 12.5 K")
        out = auditor.evaluate(pick, sample_game_result)
        assert out.estado == "PERDIDA"

    def test_k_under_line_wins(self, auditor, sample_game_result, make_pick):
        pick = make_pick("Gerrit Cole Under 12.5 K")
        out = auditor.evaluate(pick, sample_game_result)
        assert out.estado == "GANADA"

    def test_k_pitcher_tbd_pendiente(self, auditor, sample_game_result, make_pick):
        # Req 2.9: TBD => PENDIENTE
        pick = make_pick("TBD Over 6.5 K")
        out = auditor.evaluate(pick, sample_game_result)
        assert out.estado == "PENDIENTE"
        assert "TBD" in out.motivo

    def test_k_line_zero_pendiente(self, auditor, sample_game_result, make_pick):
        # Req 2.9: línea 0 => PENDIENTE (k9==0 equivalente)
        pick = make_pick("Cole Over 0 K")
        out = auditor.evaluate(pick, sample_game_result)
        assert out.estado == "PENDIENTE"

    # ---- REVIEW (fuzzy 70-84%) ----
    def test_review_status_keeps_pendiente(self, auditor, sample_game_result, make_pick):
        pick = make_pick("Yankees ML")
        out = auditor.evaluate(pick, sample_game_result, fuzzy_status=MatchStatus.REVIEW)
        assert out.estado == "PENDIENTE"
        assert "revisión" in out.motivo.lower() or "revision" in out.motivo.lower()


# ---------------------------------------------------------------------------
# _resolve_cuota — defaults
# ---------------------------------------------------------------------------
class TestResolveCuota:
    @pytest.fixture
    def auditor(self):
        return MLBBacktestAuditor(db=None)

    def test_uses_real_cuota_when_present(self, auditor, make_pick):
        pick = make_pick("Yankees ML", cuota=2.10)
        assert auditor._resolve_cuota(pick) == 2.10

    def test_default_hr_when_missing(self, auditor, make_pick):
        pick = make_pick("Aaron Judge HR")
        assert auditor._resolve_cuota(pick) == DEFAULT_CUOTA_HR

    def test_default_others_when_missing(self, auditor, make_pick):
        pick = make_pick("Yankees ML")
        assert auditor._resolve_cuota(pick) == DEFAULT_CUOTA_OTROS


# ---------------------------------------------------------------------------
# audit_pending — flujo end-to-end con SQLite temporal
# ---------------------------------------------------------------------------
class TestAuditPending:
    @pytest.fixture
    def fecha_hoy(self):
        return datetime.now().strftime("%Y-%m-%d")

    @pytest.fixture
    def db_with_picks(self, temp_db, fecha_hoy):
        """
        Inserta 4 picks PENDIENTE de hoy en la tabla `backtesting`:
          1) Yankees ML       -> esperado GANADA (Yankees ganaron 8-3)
          2) Red Sox ML       -> esperado PERDIDA
          3) Aaron Judge HR   -> esperado GANADA (HR confirmado)
          4) Over 12.5        -> esperado PERDIDA (total=11)
        """
        conn = temp_db._connect()
        cur = conn.cursor()
        for pick_text in [
            "New York Yankees ML",
            "Boston Red Sox ML",
            "Aaron Judge HR",
            "Over 12.5",
        ]:
            cur.execute(
                "INSERT INTO backtesting "
                "(fecha, deporte, evento, pick, cuota, estado, creado_en) "
                "VALUES (?, 'MLB', 'New York Yankees vs Boston Red Sox', ?, "
                "        NULL, 'PENDIENTE', ?)",
                (fecha_hoy, pick_text, datetime.now().isoformat()),
            )
        conn.commit()
        conn.close()
        return temp_db

    @pytest.fixture
    def results_json(self, tmp_path, fecha_hoy):
        """Crea un JSON de resultados que el auditor pueda leer (load_results)."""
        path = tmp_path / "resultados.json"
        payload = [
            {
                "game_pk": 12345,
                "fecha": fecha_hoy,
                "away": "New York Yankees",
                "home": "Boston Red Sox",
                "away_score": 8,
                "home_score": 3,
                "winner": "New York Yankees",
                "margin": 5,
                "total_runs": 11,
                "venue": "Fenway Park",
                "status": "Final",
                "home_runs": [
                    {
                        "person_id": 592450,
                        "full_name": "Aaron Judge",
                        "equipo": "New York Yankees",
                        "home_runs": 1,
                    }
                ],
                "strikeouts": [],
            }
        ]
        path.write_text(json.dumps(payload), encoding="utf-8")
        return str(path)

    def test_load_results_reads_json(self, results_json):
        auditor = MLBBacktestAuditor(db=None, results_path=results_json)
        results = auditor.load_results()
        assert len(results) == 1
        assert results[0].game_pk == 12345

    def test_load_results_missing_file_returns_empty(self, tmp_path):
        auditor = MLBBacktestAuditor(
            db=None, results_path=str(tmp_path / "noexiste.json"),
        )
        assert auditor.load_results() == []

    def test_load_results_skips_partial(self, tmp_path):
        path = tmp_path / "partial.json"
        path.write_text(json.dumps([{"game_pk": 1, "partial": True}]), encoding="utf-8")
        auditor = MLBBacktestAuditor(db=None, results_path=str(path))
        assert auditor.load_results() == []

    def test_audit_pending_e2e(self, db_with_picks, results_json):
        auditor = MLBBacktestAuditor(db=db_with_picks, results_path=results_json)
        report = auditor.audit_pending(dias=15)

        assert report.total_pendientes == 4
        # Yankees ML + Aaron Judge HR
        assert report.auditados_ganada == 2
        # Red Sox ML + Over 12.5
        assert report.auditados_perdida == 2

        # Verificar persistencia en DB
        conn = db_with_picks._connect()
        cur = conn.cursor()
        cur.execute(
            "SELECT pick, estado, cuota FROM backtesting ORDER BY id"
        )
        rows = cur.fetchall()
        conn.close()

        estados = {pick: estado for pick, estado, _ in rows}
        cuotas = {pick: cuota for pick, _, cuota in rows}

        assert estados["New York Yankees ML"] == "GANADA"
        assert estados["Boston Red Sox ML"] == "PERDIDA"
        assert estados["Aaron Judge HR"] == "GANADA"
        assert estados["Over 12.5"] == "PERDIDA"

        # Cuotas default aplicadas (Req 2.2)
        assert cuotas["Aaron Judge HR"] == DEFAULT_CUOTA_HR
        assert cuotas["New York Yankees ML"] == DEFAULT_CUOTA_OTROS
        assert cuotas["Over 12.5"] == DEFAULT_CUOTA_OTROS

    def test_audit_pending_does_not_overwrite_terminal(self, temp_db, results_json, fecha_hoy):
        """Req 2.3: una vez GANADA/PERDIDA, audit_pending no la modifica."""
        # Insertar un pick ya GANADA con cuota 2.50
        conn = temp_db._connect()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO backtesting "
            "(fecha, deporte, evento, pick, cuota, estado, creado_en) "
            "VALUES (?, 'MLB', 'New York Yankees vs Boston Red Sox', "
            "        'Boston Red Sox ML', 2.50, 'GANADA', ?)",
            (fecha_hoy, datetime.now().isoformat()),
        )
        conn.commit()
        conn.close()

        auditor = MLBBacktestAuditor(db=temp_db, results_path=results_json)
        auditor.audit_pending(dias=15)

        conn = temp_db._connect()
        cur = conn.cursor()
        cur.execute("SELECT estado, cuota FROM backtesting WHERE pick = 'Boston Red Sox ML'")
        row = cur.fetchone()
        conn.close()
        # NO debe haber sido cambiada de GANADA a PERDIDA
        assert row[0] == "GANADA"
        assert row[1] == 2.50

    def test_audit_pending_writes_audit_trail(self, db_with_picks, results_json):
        auditor = MLBBacktestAuditor(db=db_with_picks, results_path=results_json)
        auditor.audit_pending(dias=15)

        conn = db_with_picks._connect()
        cur = conn.cursor()
        cur.execute(
            "SELECT pick_id, pick_type, person_id, resultado FROM backtesting_audit"
        )
        rows = cur.fetchall()
        conn.close()
        # Debe haber al menos 4 inserts (los 4 picks fueron auditados)
        assert len(rows) == 4
        # El pick HR debe traer person_id != NULL
        hr_rows = [r for r in rows if r[1] == "HOME_RUN"]
        assert len(hr_rows) == 1
        assert hr_rows[0][2] == 592450
        assert hr_rows[0][3] == "GANADA"
