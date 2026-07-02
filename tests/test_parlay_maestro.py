# -*- coding: utf-8 -*-
"""Tests del PARLAY MAESTRO (motors/parlay_maestro.py).

Propiedad central: con legs independientes EV+1 = Π(p·cuota), así que el mejor
parlay de k legs es el top-k por edge. Estos tests fijan esa selección exacta,
la honestidad de precios (cuotas estimadas acotadas) y el grading del backtest.
"""
import json

import pytest

import motors.parlay_maestro as pm


@pytest.fixture(autouse=True)
def tasas_deterministas():
    """Calibración con tasas fijas (no depende del JSON del repo)."""
    original = pm._tasas_cache
    pm._tasas_cache = {
        "MLB · MONEYLINE": {"win_rate": 60.0, "total": 40},
        "MLB · PONCHES (K)": {"win_rate": 87.5, "total": 56},
        "SOCCER · 1X2/Goles": {"win_rate": 66.7, "total": 21},
    }
    yield
    pm._tasas_cache = original


def leg(evento="E1", sport="⚾ MLB", mercado="MONEYLINE", prob=65,
        cuota=1.9, cuota_real=False, pick="Gana X"):
    return {"evento": evento, "sport": sport, "mercado": mercado,
            "prob": prob, "cuota": cuota, "cuota_real": cuota_real, "pick": pick}


class TestCalibracion:
    def test_mezcla_60_real_40_modelo(self):
        # MONEYLINE MLB: tasa real 60 → 0.4·70 + 0.6·60 = 64
        assert pm.calibrar_prob(leg(prob=70)) == pytest.approx(64.0)

    def test_sin_tasa_real_encoge_al_prior(self):
        # UFC sin tasa: 0.7·92 + 0.3·55 = 80.9 (no 92)
        l = leg(sport="🥊 UFC", mercado="GANADOR", prob=92)
        assert pm.calibrar_prob(l) == pytest.approx(80.9)

    def test_cap_90(self):
        l = leg(sport="⚾ MLB", mercado="PONCHES (K)", prob=99)
        assert pm.calibrar_prob(l) <= 90.0

    def test_runline_pasa_tal_cual(self):
        l = leg(mercado="RUNLINE", prob=70)
        assert pm.calibrar_prob(l) == 70.0


class TestCuotaEfectiva:
    def test_cuota_real_se_respeta(self):
        l = leg(prob=65, cuota=3.5, cuota_real=True)
        assert pm.cuota_efectiva(l) == 3.5

    def test_cuota_estimada_se_acota_a_precio_justo(self):
        # prob calibrada 84% con cuota inventada 1.80 → cuota justa 1/0.84·1.10 ≈ 1.31
        l = leg(mercado="RUNLINE", prob=84, cuota=1.80)
        assert pm.cuota_efectiva(l) < 1.35
        # y el edge queda cerca de 1, no en 1.5 de fantasía
        assert pm.edge_leg(l) < 1.05

    def test_cuota_estimada_baja_no_se_toca(self):
        # cuota estimada MENOR a la justa no se infla
        l = leg(prob=50, cuota=1.5)
        assert pm.cuota_efectiva(l) == 1.5


class TestSeleccion:
    def _pool(self):
        # 4 eventos, edges decrecientes vía prob; cuotas reales para no acotar
        return [
            leg("E1", prob=80, cuota=1.9, cuota_real=True, pick="A"),
            leg("E2", prob=70, cuota=1.9, cuota_real=True, pick="B"),
            leg("E3", prob=60, cuota=1.9, cuota_real=True, pick="C"),
            leg("E4", prob=50, cuota=1.9, cuota_real=True, pick="D"),
            # leg peor del MISMO evento E1: debe deduplicarse
            leg("E1", prob=40, cuota=1.9, cuota_real=True, pick="A-peor"),
        ]

    def test_dedupe_mejor_leg_por_evento(self):
        legs = pm._mejor_leg_por_evento(self._pool(), pm.edge_leg)
        assert len(legs) == 4
        picks = {l["pick"] for l in legs}
        assert "A" in picks and "A-peor" not in picks

    def test_frontera_es_top_k_por_edge(self):
        frontera = pm.frontera_por_edge(self._pool(), n_sims=500)
        # k=2 debe ser exactamente las 2 legs de mayor edge (A y B)
        k2 = frontera[0]
        assert k2["n_legs"] == 2
        assert {l["pick"] for l in k2["legs"]} == {"A", "B"}
        # la cuota crece con k
        cuotas = [f["cuota"] for f in frontera]
        assert cuotas == sorted(cuotas)

    def test_seleccionar_objetivos(self):
        sel = pm.seleccionar(self._pool(), n_sims=1500, seed=7)
        assert not sel.get("error")
        via = sel["mas_viable"]
        assert via and via["cuota"] >= 2.0     # duplica o más
        pago = sel["mejor_pago"]
        assert pago and pago["prob"] >= pm.PROB_PISO_PAGO
        # mejor jugada por partido: rankeada por edge desc y sin eventos repetidos
        partidos = sel["mejor_por_partido"]
        assert len(partidos) == 4
        edges = [j["edge"] for j in partidos]
        assert edges == sorted(edges, reverse=True)

    def test_sin_valor_mejor_ev_es_none_con_nota(self):
        # todas las legs con edge < 1 (prob baja, cuota real corta)
        pool = [leg(f"E{i}", prob=45, cuota=1.5, cuota_real=True, pick=f"P{i}")
                for i in range(4)]
        sel = pm.seleccionar(pool, n_sims=800, seed=7)
        assert sel["mejor_ev"] is None
        assert sel["nota"]

    def test_pool_insuficiente(self):
        assert pm.seleccionar([leg("E1")]).get("error")


class TestKelly:
    def test_kelly_clasico(self):
        # p=0.6, cuota 2.0 → f = (1.2-1)/1 = 0.2
        assert pm.kelly_fraccion(0.6, 2.0) == pytest.approx(0.2)

    def test_kelly_sin_valor_es_cero(self):
        assert pm.kelly_fraccion(0.4, 2.0) == 0.0


class TestBacktest:
    def test_grading_gana_pierde_push(self, tmp_path):
        """2 días: uno donde las mejores legs ganan (con un push que solo quita
        cuota) y otro donde una leg pierde."""
        def p(fecha, evento, pick, estado, prob=75, cuota=1.9):
            return {"fecha_evento": fecha, "deporte": "MLB", "liga": "⚾ MLB",
                    "evento": evento, "mercado": "MONEYLINE", "pick": pick,
                    "confianza": prob, "cuota": cuota, "estado": estado}
        hist = (
            [p("2026-07-01", f"J{i}", f"G{i}", "ganado") for i in range(3)] +
            [p("2026-07-01", "J3", "G3", "push")] +
            [p("2026-07-02", f"K{i}", f"H{i}", "ganado") for i in range(3)] +
            [p("2026-07-02", "K3", "H3", "perdido", prob=90, cuota=3.0)]
        )
        hp = tmp_path / "hist.json"
        hp.write_text(json.dumps(hist), encoding="utf-8")
        rep = pm.backtest_maestro(history_path=str(hp), min_picks_dia=4,
                                  out_path=str(tmp_path / "out.json"))
        assert rep["por_objetivo"]["mas_viable"]["n"] >= 1
        # día 1: todo gana/push → los parlays del día 1 deben ganar
        dia1 = [d for d in rep["detalle"] if d["fecha"] == "2026-07-01"]
        assert dia1 and all(d["gano"] for d in dia1)
