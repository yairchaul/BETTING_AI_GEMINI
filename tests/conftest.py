# -*- coding: utf-8 -*-
"""
Configuración compartida de pytest para la suite de backtesting-real-mlb.

Este archivo:
  - Inserta la raíz del proyecto en `sys.path` para que `motors/`, `scrapers/`
    y `utils/` resuelvan sin instalar el paquete.
  - Define fixtures comunes para tests unitarios, property tests e integración:
      * `temp_db`        — DatabaseManager apuntando a un SQLite temporal.
      * `sample_game_result`        — GameResult Yankees @ Red Sox (Aaron Judge HR).
      * `sample_game_result_dodgers` — GameResult sin HR para el lado contrario.
      * `results_list`   — lista lista para `match_game`.
      * `sample_pick_*`  — BacktestPick por tipo (ML/OU/HCAP/HR/K/TBD).

Toda la suite corre OFFLINE: nunca toca red. Los tests del scraper inyectan un
fake `statsapi` con `monkeypatch`, los del auditor escriben/leen un SQLite
temporal vía la fixture `temp_db`, y los del selector usan rutas a JSON dentro
de `tmp_path`.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Asegurar que la raíz del repo está en sys.path antes de importar nada del
# proyecto. tests/ y root cuelgan de la misma carpeta.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def temp_db(tmp_path):
    """DatabaseManager sobre un SQLite efímero en `tmp_path`."""
    from utils.database_manager import DatabaseManager
    db_path = tmp_path / "test_betting_stats.db"
    return DatabaseManager(db_path=str(db_path))


@pytest.fixture
def sample_game_result():
    """
    Resultado real de Yankees @ Red Sox: Yankees ganan 8-3, Aaron Judge HR,
    Gerrit Cole 10 K. Fecha: 2025-06-01, estadio Fenway Park.
    """
    from motors.mlb_backtest_models import (
        GameResult,
        HomeRunRecord,
        StrikeoutRecord,
    )
    return GameResult(
        game_pk=12345,
        fecha="2025-06-01",
        away="New York Yankees",
        home="Boston Red Sox",
        away_score=8,
        home_score=3,
        winner="New York Yankees",
        margin=5,
        total_runs=11,
        venue="Fenway Park",
        home_runs=[
            HomeRunRecord(
                person_id=592450,
                full_name="Aaron Judge",
                equipo="New York Yankees",
                home_runs=1,
            )
        ],
        strikeouts=[
            StrikeoutRecord(
                person_id=543037,
                pitcher="Gerrit Cole",
                equipo="New York Yankees",
                strike_outs=10,
            )
        ],
        status="Final",
    )


@pytest.fixture
def sample_game_result_dodgers():
    """Dodgers @ Giants: Dodgers ganan 5-3 sin HRs registrados (caso negativo)."""
    from motors.mlb_backtest_models import GameResult
    return GameResult(
        game_pk=22222,
        fecha="2025-06-02",
        away="Los Angeles Dodgers",
        home="San Francisco Giants",
        away_score=5,
        home_score=3,
        winner="Los Angeles Dodgers",
        margin=2,
        total_runs=8,
        venue="Oracle Park",
        home_runs=[],
        strikeouts=[],
        status="Final",
    )


@pytest.fixture
def results_list(sample_game_result, sample_game_result_dodgers):
    """Lista de GameResult para alimentar `MLBBacktestAuditor.match_game`."""
    return [sample_game_result, sample_game_result_dodgers]


@pytest.fixture
def make_pick():
    """Factory que crea BacktestPick con valores default razonables."""
    from motors.mlb_backtest_models import BacktestPick

    def _build(
        pick: str,
        evento: str = "New York Yankees vs Boston Red Sox",
        fecha: str = "2025-06-01",
        cuota=None,
        estado: str = "PENDIENTE",
        pick_id: int = 1,
    ) -> BacktestPick:
        return BacktestPick(
            id=pick_id,
            fecha=fecha,
            deporte="MLB",
            evento=evento,
            pick=pick,
            cuota=cuota,
            estado=estado,
        )

    return _build
