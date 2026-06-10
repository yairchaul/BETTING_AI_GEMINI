#!/usr/bin/env python3
"""
Prueba básica de los modelos de datos para backtesting de MLB.
"""

import sys
sys.path.insert(0, '.')

from motors.mlb_backtest_models import (
    HomeRunRecord,
    StrikeoutRecord,
    GameResult,
    BacktestPick,
    Metrics,
    Classification,
    PickType,
    validate_game_result_consistency,
    calculate_win_rate_roi
)


def test_home_run_record():
    """Prueba de creación de HomeRunRecord."""
    hr = HomeRunRecord(
        person_id=12345,
        full_name="Mike Trout",
        equipo="Los Angeles Angels",
        home_runs=2
    )
    assert hr.person_id == 12345
    assert hr.full_name == "Mike Trout"
    assert hr.equipo == "Los Angeles Angels"
    assert hr.home_runs == 2
    print("✓ HomeRunRecord creado correctamente")
    return True


def test_strikeout_record():
    """Prueba de creación de StrikeoutRecord."""
    k = StrikeoutRecord(
        person_id=67890,
        pitcher="Shohei Ohtani",
        equipo="Los Angeles Dodgers",
        strike_outs=8
    )
    assert k.person_id == 67890
    assert k.pitcher == "Shohei Ohtani"
    assert k.equipo == "Los Angeles Dodgers"
    assert k.strike_outs == 8
    print("✓ StrikeoutRecord creado correctamente")


def test_game_result_valid():
    """Prueba de creación de GameResult válido."""
    hr = HomeRunRecord(person_id=12345, full_name="Mike Trout", equipo="Angels", home_runs=2)
    k = StrikeoutRecord(person_id=67890, pitcher="Ohtani", equipo="Dodgers", strike_outs=8)
    
    game = GameResult(
        game_pk=2024001234,
        fecha="2024-06-01",
        away="Dodgers",
        home="Giants",
        away_score=5,
        home_score=3,
        winner="Dodgers",
        margin=2,
        total_runs=8,
        venue="Oracle Park",
        home_runs=[hr],
        strikeouts=[k]
    )
    assert game.game_pk == 2024001234
    assert game.total_runs == 8 == 5 + 3
    assert game.winner == "Dodgers"
    assert game.margin == 2
    print("✓ GameResult válido creado correctamente")


def test_game_result_invalid_total_runs():
    """Prueba de GameResult con total_runs incorrecto."""
    try:
        game = GameResult(
            game_pk=2024001235,
            fecha="2024-06-01",
            away="Dodgers",
            home="Giants",
            away_score=5,
            home_score=3,
            winner="Dodgers",
            margin=2,
            total_runs=7,  # ¡Incorrecto! debería ser 8
            venue="Oracle Park",
            home_runs=[],
            strikeouts=[]
        )
        print("✗ GameResult debería fallar con total_runs incorrecto")
        return False
    except ValueError as e:
        assert "total_runs" in str(e)
        print("✓ GameResult rechazado correctamente por total_runs incorrecto")
        return True


def test_game_result_invalid_winner():
    """Prueba de GameResult con winner incorrecto."""
    try:
        game = GameResult(
            game_pk=2024001236,
            fecha="2024-06-01",
            away="Dodgers",
            home="Giants",
            away_score=5,
            home_score=3,
            winner="Yankees",  # ¡Incorrecto! no es away ni home
            margin=2,
            total_runs=8,
            venue="Oracle Park",
            home_runs=[],
            strikeouts=[]
        )
        print("✗ GameResult debería fallar con winner incorrecto")
        return False
    except ValueError as e:
        assert "winner" in str(e)
        print("✓ GameResult rechazado correctamente por winner incorrecto")
        return True


def test_backtest_pick():
    """Prueba de creación de BacktestPick."""
    pick = BacktestPick(
        id=1001,
        fecha="2024-06-01",
        deporte="MLB",
        evento="Dodgers @ Giants",
        pick="Dodgers ML",
        cuota=1.90,
        estado="PENDIENTE"
    )
    assert pick.id == 1001
    assert pick.deporte == "MLB"
    assert pick.estado == "PENDIENTE"
    print("✓ BacktestPick creado correctamente")


def test_backtest_pick_invalid_deporte():
    """Prueba de BacktestPick con deporte incorrecto."""
    try:
        pick = BacktestPick(
            id=1002,
            fecha="2024-06-01",
            deporte="NBA",  # ¡Incorrecto! debería ser MLB
            evento="Dodgers @ Giants",
            pick="Dodgers ML",
            cuota=1.90,
            estado="PENDIENTE"
        )
        print("✗ BacktestPick debería fallar con deporte incorrecto")
        return False
    except ValueError as e:
        assert "deporte" in str(e)
        print("✓ BacktestPick rechazado correctamente por deporte incorrecto")
        return True


def test_metrics():
    """Prueba de creación de Metrics."""
    metrics = Metrics(
        total=10,
        hits=6,
        win_rate=60.0,
        profit=4.5,
        roi=45.0,
        last_10=['W', 'L', 'W', 'W', 'L', 'W', 'W', 'L', 'W', 'W']
    )
    assert metrics.total == 10
    assert metrics.hits == 6
    assert metrics.win_rate == 60.0
    assert metrics.roi == 45.0
    assert len(metrics.last_10) == 10
    print("✓ Metrics creado correctamente")


def test_metrics_invalid_hits():
    """Prueba de Metrics con hits > total."""
    try:
        metrics = Metrics(
            total=5,
            hits=7,  # ¡Incorrecto! hits no puede ser mayor que total
            win_rate=140.0,
            profit=4.5,
            roi=90.0,
            last_10=['W', 'W', 'W', 'W', 'W']
        )
        print("✗ Metrics debería fallar con hits > total")
        return False
    except ValueError as e:
        assert "hits" in str(e)
        print("✓ Metrics rechazado correctamente por hits > total")
        return True


def test_enums():
    """Prueba de los enums Classification y PickType."""
    assert Classification.ELITE.value == "ELITE"
    assert Classification.CONFIANZA.value == "CONFIANZA"
    assert Classification.RIESGO.value == "RIESGO"
    assert Classification.EVITAR.value == "EVITAR"
    
    assert PickType.HOME_RUN.value == "HOME_RUN"
    assert PickType.MONEYLINE.value == "MONEYLINE"
    assert PickType.OVER_UNDER.value == "OVER_UNDER"
    assert PickType.STRIKEOUTS.value == "STRIKEOUTS"
    assert PickType.HANDICAP.value == "HANDICAP"
    print("✓ Enums creados correctamente")


def test_validate_game_result_consistency():
    """Prueba de validación de consistencia de game_pk."""
    hr1 = HomeRunRecord(person_id=1, full_name="A", equipo="Team", home_runs=1)
    hr2 = HomeRunRecord(person_id=2, full_name="B", equipo="Team", home_runs=1)
    
    # Lista sin duplicados
    games1 = [
        GameResult(
            game_pk=1, fecha="2024-06-01", away="A", home="B",
            away_score=3, home_score=2, winner="A", margin=1,
            total_runs=5, venue="Park", home_runs=[hr1]
        ),
        GameResult(
            game_pk=2, fecha="2024-06-02", away="C", home="D",
            away_score=4, home_score=3, winner="C", margin=1,
            total_runs=7, venue="Park", home_runs=[hr2]
        )
    ]
    assert validate_game_result_consistency(games1)
    
    # Lista con duplicados
    games2 = [
        GameResult(
            game_pk=1, fecha="2024-06-01", away="A", home="B",
            away_score=3, home_score=2, winner="A", margin=1,
            total_runs=5, venue="Park", home_runs=[hr1]
        ),
        GameResult(
            game_pk=1, fecha="2024-06-01", away="A", home="B",  # Mismo game_pk
            away_score=3, home_score=2, winner="A", margin=1,
            total_runs=5, venue="Park", home_runs=[hr1]
        )
    ]
    assert not validate_game_result_consistency(games2)
    print("✓ Validación de consistencia funciona correctamente")


def test_calculate_win_rate_roi():
    """Prueba de cálculo de win_rate y ROI."""
    # Caso normal
    win_rate, roi = calculate_win_rate_roi(hits=6, total=10, profit=4.5)
    assert win_rate == 60.0
    assert roi == 45.0
    
    # Caso sin picks
    win_rate, roi = calculate_win_rate_roi(hits=0, total=0, profit=0)
    assert win_rate == 0.0
    assert roi == 0.0
    
    # Caso con pérdida
    win_rate, roi = calculate_win_rate_roi(hits=4, total=10, profit=-2.0)
    assert win_rate == 40.0
    assert roi == -20.0
    print("✓ Cálculo de win_rate y ROI funciona correctamente")


def main():
    """Ejecutar todas las pruebas."""
    print("=== Pruebas de modelos de datos para backtesting de MLB ===\n")
    
    tests = [
        test_home_run_record,
        test_strikeout_record,
        test_game_result_valid,
        test_game_result_invalid_total_runs,
        test_game_result_invalid_winner,
        test_backtest_pick,
        test_backtest_pick_invalid_deporte,
        test_metrics,
        test_metrics_invalid_hits,
        test_enums,
        test_validate_game_result_consistency,
        test_calculate_win_rate_roi,
    ]
    
    passed = 0
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ {test.__name__} falló con error: {e}")
    
    print(f"\n=== Resumen: {passed}/{len(tests)} pruebas pasaron ===")
    
    if passed == len(tests):
        print("¡Todas las pruebas pasaron correctamente!")
        return 0
    else:
        print(f"{len(tests) - passed} pruebas fallaron")
        return 1


if __name__ == "__main__":
    sys.exit(main())