# -*- coding: utf-8 -*-
"""Tests del calificador de picks con línea (box_score_resolver).

Regresión del bug: un total que EMPATA la línea entera (ej. OVER 9.0 con 9
carreras) se marcaba "perdido" para ambos lados. Debe ser push (devolución),
excluido del win-rate por pick_memory.stats().
"""
import pytest

from motors.box_score_resolver import _estado_de, _grade_linea, _grade_ufc


class TestGradeLinea:
    def test_over_gana(self):
        assert _grade_linea(10, 8.5, True) is True

    def test_over_pierde(self):
        assert _grade_linea(7, 8.5, True) is False

    def test_under_gana(self):
        assert _grade_linea(7, 8.5, False) is True

    def test_under_pierde(self):
        assert _grade_linea(10, 8.5, False) is False

    def test_push_linea_entera_over(self):
        # BUG original: OVER 9.0 con total 9 se marcaba perdido
        assert _grade_linea(9, 9.0, True) == "push"

    def test_push_linea_entera_under(self):
        assert _grade_linea(9, 9.0, False) == "push"

    def test_linea_fraccionaria_nunca_push(self):
        for total in range(0, 20):
            assert _grade_linea(total, 8.5, True) != "push"


class TestEstadoDe:
    def test_true_ganado(self):
        assert _estado_de(True) == "ganado"

    def test_false_perdido(self):
        assert _estado_de(False) == "perdido"

    def test_push(self):
        assert _estado_de("push") == "push"

    def test_push_no_se_confunde_con_true(self):
        # "push" es truthy: el mapeo debe distinguirlo ANTES del if genérico
        assert _estado_de("push") != "ganado"


class TestUfcRoundsPush:
    def test_over_rounds_gana(self):
        pelea = {"ganador_real": "A", "round_final": 3, "rounds_programados": 3}
        assert _grade_ufc("ROUNDS", "OVER 2.5 rounds", pelea) is True

    def test_under_rounds_gana(self):
        pelea = {"ganador_real": "A", "round_final": 1, "rounds_programados": 3}
        assert _grade_ufc("ROUNDS", "UNDER 2.5 rounds", pelea) is True

    def test_rounds_linea_entera_push(self):
        pelea = {"ganador_real": "A", "round_final": 2, "rounds_programados": 3}
        assert _grade_ufc("ROUNDS", "OVER 2 rounds", pelea) == "push"
