# -*- coding: utf-8 -*-
"""
Unit tests para `motors.mlb_effectiveness.EffectivenessCalculator`.

Cubre:
  * `compute_by_pick_type` — agrupación por PickType.
  * `compute_by_team`      — agrupación por equipo.
  * `classify`             — fronteras ÉLITE / CONFIANZA / RIESGO / EVITAR.
  * `is_equipo_trampa`     — < 40% en últimos 10 picks.
  * `persist` / `load_from_cache` — round-trip de los JSON de caché.

Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9.
"""
from __future__ import annotations

import json
import os
from datetime import datetime

import pytest

from motors.mlb_backtest_models import Classification, Metrics, PickType
from motors.mlb_effectiveness import EffectivenessCalculator


# ---------------------------------------------------------------------------
# Helpers para sembrar la tabla `backtesting`
# ---------------------------------------------------------------------------
def _seed_pick(db, fecha, evento, pick, estado, cuota=1.90):
    conn = db._connect()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO backtesting "
        "(fecha, deporte, evento, pick, cuota, estado, creado_en) "
        "VALUES (?, 'MLB', ?, ?, ?, ?, ?)",
        (fecha, evento, pick, cuota, estado, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# classify — fronteras
# ---------------------------------------------------------------------------
class TestClassify:
    @pytest.fixture
    def calc(self):
        return EffectivenessCalculator(db=None)

    def _m(self, win_rate, roi, total=20):
        hits = int(round(win_rate * total / 100.0))
        # Garantizar invariante hits<=total para Metrics.__post_init__
        hits = min(hits, total)
        profit = roi * total / 100.0
        return Metrics(
            total=total, hits=hits, win_rate=win_rate,
            profit=profit, roi=roi, last_10=[],
        )

    def test_classify_total_zero_returns_evitar(self, calc):
        m = Metrics(total=0, hits=0, win_rate=0.0, profit=0.0, roi=0.0, last_10=[])
        assert calc.classify(m) == Classification.EVITAR

    def test_classify_evitar_low_win_rate(self, calc):
        # WR < 45 -> EVITAR
        assert calc.classify(self._m(40.0, 5.0)) == Classification.EVITAR

    def test_classify_evitar_low_roi(self, calc):
        # ROI < -15 -> EVITAR (incluso con WR alto)
        assert calc.classify(self._m(80.0, -20.0)) == Classification.EVITAR

    def test_classify_elite(self, calc):
        # WR > 65 y ROI > 20 -> ÉLITE
        assert calc.classify(self._m(70.0, 25.0)) == Classification.ELITE

    def test_classify_confianza(self, calc):
        # 55 <= WR <= 65 y ROI > 0 -> CONFIANZA
        assert calc.classify(self._m(60.0, 10.0)) == Classification.CONFIANZA

    def test_classify_riesgo(self, calc):
        # 45 <= WR <= 55 -> RIESGO
        assert calc.classify(self._m(50.0, -5.0)) == Classification.RIESGO

    # Fronteras
    def test_classify_boundary_64_9_wr_is_confianza(self, calc):
        assert calc.classify(self._m(64.9, 5.0)) == Classification.CONFIANZA

    def test_classify_boundary_65_1_wr_with_low_roi_is_riesgo(self, calc):
        # WR > 65 pero ROI <= 20 -> caso residual = RIESGO
        assert calc.classify(self._m(65.1, 5.0)) == Classification.RIESGO

    def test_classify_boundary_65_1_wr_with_high_roi_is_elite(self, calc):
        assert calc.classify(self._m(65.1, 25.0)) == Classification.ELITE

    def test_classify_roi_19_vs_21(self, calc):
        # WR > 65 pero ROI 19 -> RIESGO; con 21 -> ÉLITE
        assert calc.classify(self._m(70.0, 19.0)) == Classification.RIESGO
        assert calc.classify(self._m(70.0, 21.0)) == Classification.ELITE

    def test_classify_boundary_45_inclusive(self, calc):
        # 45.0 inclusive -> RIESGO (no EVITAR)
        assert calc.classify(self._m(45.0, -10.0)) == Classification.RIESGO

    def test_classify_boundary_55_inclusive(self, calc):
        # 55.0 con ROI positivo -> CONFIANZA
        assert calc.classify(self._m(55.0, 5.0)) == Classification.CONFIANZA


# ---------------------------------------------------------------------------
# compute_by_pick_type / compute_by_team
# ---------------------------------------------------------------------------
class TestCompute:
    def test_compute_by_pick_type_basic(self, temp_db):
        fecha = datetime.now().strftime("%Y-%m-%d")
        evento = "New York Yankees vs Boston Red Sox"
        # 4 picks: 2 ML (1W, 1L), 2 HR (1W, 1L)
        _seed_pick(temp_db, fecha, evento, "Yankees ML", "GANADA", 1.90)
        _seed_pick(temp_db, fecha, evento, "Red Sox ML", "PERDIDA", 1.90)
        _seed_pick(temp_db, fecha, evento, "Aaron Judge HR", "GANADA", 3.50)
        _seed_pick(temp_db, fecha, evento, "Mookie Betts HR", "PERDIDA", 3.50)

        calc = EffectivenessCalculator(db=temp_db)
        result = calc.compute_by_pick_type()

        assert PickType.MONEYLINE in result
        assert PickType.HOME_RUN in result
        ml = result[PickType.MONEYLINE]
        hr = result[PickType.HOME_RUN]
        assert ml.total == 2 and ml.hits == 1
        assert ml.win_rate == 50.0
        assert hr.total == 2 and hr.hits == 1
        assert hr.win_rate == 50.0

    def test_compute_by_pick_type_excludes_pendientes(self, temp_db):
        fecha = datetime.now().strftime("%Y-%m-%d")
        _seed_pick(temp_db, fecha, "A vs B", "A ML", "PENDIENTE")
        _seed_pick(temp_db, fecha, "A vs B", "A ML", "GANADA")
        calc = EffectivenessCalculator(db=temp_db)
        result = calc.compute_by_pick_type()
        # Solo el GANADA cuenta
        assert result[PickType.MONEYLINE].total == 1

    def test_compute_by_team_referenced_pick(self, temp_db):
        fecha = datetime.now().strftime("%Y-%m-%d")
        evento = "New York Yankees vs Boston Red Sox"
        _seed_pick(temp_db, fecha, evento, "New York Yankees ML", "GANADA")
        _seed_pick(temp_db, fecha, evento, "New York Yankees -1.5", "PERDIDA")

        calc = EffectivenessCalculator(db=temp_db)
        result = calc.compute_by_team()

        # Yankees aparece como key (los Red Sox no, porque ningún pick los menciona)
        keys = list(result.keys())
        assert any("Yankees" in k for k in keys)


# ---------------------------------------------------------------------------
# is_equipo_trampa
# ---------------------------------------------------------------------------
class TestEquipoTrampa:
    def test_no_history_returns_false(self, temp_db):
        calc = EffectivenessCalculator(db=temp_db)
        assert calc.is_equipo_trampa("Yankees") is False

    def test_low_winrate_marks_trampa(self, temp_db):
        fecha = datetime.now().strftime("%Y-%m-%d")
        evento = "New York Yankees vs Boston Red Sox"
        # 10 picks Yankees: 3 W, 7 L -> WR 30% < 40% -> TRAMPA
        for i in range(3):
            _seed_pick(temp_db, fecha, evento, "New York Yankees ML", "GANADA")
        for i in range(7):
            _seed_pick(temp_db, fecha, evento, "New York Yankees ML", "PERDIDA")
        calc = EffectivenessCalculator(db=temp_db)
        assert calc.is_equipo_trampa("New York Yankees") is True

    def test_good_winrate_not_trampa(self, temp_db):
        fecha = datetime.now().strftime("%Y-%m-%d")
        evento = "New York Yankees vs Boston Red Sox"
        # 10 picks: 6 W, 4 L -> WR 60% > 40% -> NO trampa
        for i in range(6):
            _seed_pick(temp_db, fecha, evento, "New York Yankees ML", "GANADA")
        for i in range(4):
            _seed_pick(temp_db, fecha, evento, "New York Yankees ML", "PERDIDA")
        calc = EffectivenessCalculator(db=temp_db)
        assert calc.is_equipo_trampa("New York Yankees") is False


# ---------------------------------------------------------------------------
# persist / load_from_cache
# ---------------------------------------------------------------------------
class TestPersist:
    def test_persist_writes_two_files(self, temp_db, tmp_path):
        fecha = datetime.now().strftime("%Y-%m-%d")
        evento = "New York Yankees vs Boston Red Sox"
        _seed_pick(temp_db, fecha, evento, "Yankees ML", "GANADA", 1.90)
        _seed_pick(temp_db, fecha, evento, "Red Sox ML", "PERDIDA", 1.90)

        cache_dir = tmp_path / "cache"
        calc = EffectivenessCalculator(db=temp_db, cache_dir=str(cache_dir))
        paths = calc.persist()

        assert os.path.exists(paths["pick_type"])
        assert os.path.exists(paths["team"])

        # Validar que el contenido es un JSON parseable y tiene metadata
        with open(paths["pick_type"], "r", encoding="utf-8") as f:
            pt = json.load(f)
        assert "_metadata" in pt
        assert pt["_metadata"]["window_days"] == 15

    def test_load_from_cache_roundtrip(self, temp_db, tmp_path):
        fecha = datetime.now().strftime("%Y-%m-%d")
        _seed_pick(temp_db, fecha, "A vs B", "A ML", "GANADA")
        cache_dir = tmp_path / "cache"
        calc = EffectivenessCalculator(db=temp_db, cache_dir=str(cache_dir))
        calc.persist()

        loaded = calc.load_from_cache()
        assert "pick_type" in loaded
        assert "team" in loaded
        # Debe contener al menos una clase de pick
        non_meta_keys = [k for k in loaded["pick_type"] if not k.startswith("_")]
        assert len(non_meta_keys) >= 1

    def test_load_from_cache_missing_files_returns_empty(self, tmp_path):
        calc = EffectivenessCalculator(db=None, cache_dir=str(tmp_path / "noexiste"))
        loaded = calc.load_from_cache()
        assert loaded == {"pick_type": {}, "team": {}}
