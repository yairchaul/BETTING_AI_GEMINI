# -*- coding: utf-8 -*-
"""Tests del motor Over/Under de MLB recalibrado con backtest real.

Contexto (backtest 1220 juegos MLB 2026, líneas reales de cierre DraftKings):
  - El O/U viejo de motor_mlb_pro sacaba UNDER en 94% de los juegos porque su
    baseline de K/9 era 7.5 con la liga en 8.2 → 50.0% WR, ROI −4.5%.
  - Su confianza (hasta 75%) venía de una Poisson que subestima la varianza
    real de los totales (σ=4.5) → no correlacionaba con aciertos.
  - El recalibrado (_analizar_ou): ajuste centrado en la liga, Normal σ=4.5,
    push excluido y PASAR sin edge → 54.1% WR, ROI +3.3% en el mismo backtest.
"""
import pytest

from motors.motor_mlb_pro import (
    LIGA_ERA_REF,
    LIGA_K9_REF,
    OU_UMBRAL_PASAR,
    _analizar_ou,
)

LINEA = 8.5


class TestAnalizarOU:
    def test_abridores_promedio_pasa(self):
        # REGRESIÓN del sesgo UNDER: con abridores exactamente de liga el
        # ajuste debe ser 0 → proyección = línea → PASAR (antes: UNDER casi fijo)
        pick, conf, proy, _ = _analizar_ou(LINEA, LIGA_ERA_REF, LIGA_ERA_REF,
                                           LIGA_K9_REF, LIGA_K9_REF, 1.0)
        assert pick is None
        assert conf == 50
        assert proy == LINEA

    def test_duelo_de_ases_da_under(self):
        pick, conf, proy, _ = _analizar_ou(LINEA, 2.60, 2.80, 10.5, 10.0, 1.0)
        assert pick == "UNDER"
        assert proy < LINEA

    def test_abridores_malos_dan_over(self):
        pick, conf, proy, _ = _analizar_ou(LINEA, 5.60, 5.40, 7.0, 7.2, 1.0)
        assert pick == "OVER"
        assert proy > LINEA

    def test_confianza_honesta_techo_63(self):
        # σ=4.5 real: ni el edge máximo (±1.5 carreras) justifica más de 63%
        for era in (1.5, 4.2, 7.5):
            pick, conf, _, _ = _analizar_ou(LINEA, era, era, 8.2, 8.2, 1.18)
            assert conf <= 63

    def test_ajuste_acotado_a_1_5_carreras(self):
        _, _, proy, _ = _analizar_ou(LINEA, 9.9, 9.9, 5.0, 5.0, 1.18)
        assert proy <= LINEA + 1.5 + 1e-9
        _, _, proy_baja, _ = _analizar_ou(LINEA, 0.5, 0.5, 12.0, 12.0, 0.88)
        assert proy_baja >= LINEA - 1.5 - 1e-9

    def test_parque_bateador_empuja_over(self):
        _, _, proy_neutro, _ = _analizar_ou(11.5, LIGA_ERA_REF, LIGA_ERA_REF,
                                            LIGA_K9_REF, LIGA_K9_REF, 1.0)
        _, _, proy_coors, _ = _analizar_ou(11.5, LIGA_ERA_REF, LIGA_ERA_REF,
                                           LIGA_K9_REF, LIGA_K9_REF, 1.18)
        assert proy_coors > proy_neutro

    def test_linea_entera_excluye_push(self):
        # En línea 9.0 la masa de "total = 9" no debe regalarse al UNDER:
        # P(over)+P(under) normalizadas suman 100
        _, _, _, p_over = _analizar_ou(9.0, 5.5, 5.5, 8.2, 8.2, 1.0)
        assert 0.0 < p_over < 100.0

    def test_umbral_pasar(self):
        # Justo bajo el umbral → PASAR; claramente arriba → pick
        pick_chico, _, _, _ = _analizar_ou(LINEA, LIGA_ERA_REF + 0.1, LIGA_ERA_REF,
                                           LIGA_K9_REF, LIGA_K9_REF, 1.0)
        assert pick_chico is None
        pick_grande, _, _, _ = _analizar_ou(LINEA, 5.8, 5.8, 7.0, 7.0, 1.0)
        assert pick_grande is not None
        assert OU_UMBRAL_PASAR == 0.5


class TestMotorOverUnderV25:
    @pytest.fixture
    def mou(self):
        from motors.motor_over_under import MotorOverUnder
        return MotorOverUnder()

    def test_park_bonus_nombre_patrocinado(self, mou):
        # Los feeds traen 'UNIQLO Field at Dodger Stadium' → antes caía a 0.0
        assert mou._park_bonus("UNIQLO Field at Dodger Stadium") == \
            mou.PARK_FACTORS["Dodger Stadium"]

    def test_park_bonus_exacto_y_desconocido(self, mou):
        assert mou._park_bonus("Coors Field") == mou.PARK_FACTORS["Coors Field"]
        assert mou._park_bonus("Estadio Azteca") == 0.0
        assert mou._park_bonus("") == 0.0

    def test_confianza_acotada_y_estados_validos(self, mou, monkeypatch):
        # Sin DB ni modelo de carreras: núcleo heurístico puro
        import database_manager
        monkeypatch.setattr(database_manager.db, "get_team_stats_detailed",
                            lambda *a, **k: {}, raising=False)
        import motors.mlb_runs_model as runs_model
        monkeypatch.setattr(runs_model, "predecir", lambda *a, **k: None)
        partido = {
            "local": "Colorado Rockies", "visitante": "Los Angeles Dodgers",
            "venue": "Coors Field",
            "pitchers": {"local": {"era": 5.80}, "visitante": {"era": 3.10}},
            "odds": {"over_under": 11.5},
            "clima": {"temp": 70, "wind_speed": 0, "humedad": 50},
        }
        r = mou.calcular_total(partido)
        assert r["recomendacion"] in ("OVER", "UNDER", "PASAR")
        if r["recomendacion"] != "PASAR":
            # Techo honesto: 64 heurístico / 66 con refuerzo del modelo
            assert r["confianza"] <= 66

    def test_off_factor_estatico_centrado(self, mou):
        # La tabla estática debe promediar ≈ STATIC_RUNS_MEAN: si no, el factor
        # ofensivo vuelve a nacer sesgado (bug del clamp 0.85)
        media = sum(mou.TEAM_RUNS_AVG.values()) / len(mou.TEAM_RUNS_AVG)
        assert abs(media - mou.STATIC_RUNS_MEAN) < 0.05
