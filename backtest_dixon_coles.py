# -*- coding: utf-8 -*-
"""
BACKTEST DIXON-COLES — validación out-of-sample con walk-forward.

Mide cuánto mejora el motor Dixon-Coles vs. los baselines, SOBRE PARTIDOS QUE EL
MODELO NUNCA VIO (se entrena con el pasado y se predice el año siguiente).

Métricas (estándar en forecasting deportivo):
  • RPS (Ranked Probability Score): qué tan cerca estuvo la prob. del 1X2 real.
    Menor = mejor. Castiga más equivocarse con mucha confianza.
  • Log-Loss: calidad de la probabilidad asignada al resultado real. Menor = mejor.
  • Accuracy 1X2: % de aciertos del resultado (gana/empata/pierde) por argmax.
  • Accuracy marcador exacto: % de marcadores correctos clavados.

Baselines:
  1. Base rate: frecuencias 1X2 del set de ENTRENAMIENTO (modelo "sin skill").
  2. λ por ranking (sólo subset con ranking): goles esperados al estilo del
     fallback FIFA del motor, pasados por el MISMO Poisson → aísla la mejora de
     estimar λ con Dixon-Coles vs. con ranking.
"""
import sys
import math
import logging
from collections import Counter

import numpy as np

logging.disable(logging.WARNING)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from motors.international_results import _cargar_datos
from motors import dixon_coles as dc
from motors.futbol_analyzer_jerarquico import _FIFA_RANK
from motors.international_results import _resolve

MAXG = dc.MAX_GOLES


# ── Métricas ────────────────────────────────────────────────────────────────
def rps_1x2(p_home, p_draw, p_away, obs):
    """RPS para 3 categorías ordinales [Home, Draw, Away]. obs en {'H','D','A'}."""
    p = [p_home, p_draw, p_away]
    o = {"H": [1, 0, 0], "D": [0, 1, 0], "A": [0, 0, 1]}[obs]
    cum_p = cum_o = 0.0
    total = 0.0
    for i in range(2):                       # r-1 = 2 términos
        cum_p += p[i]
        cum_o += o[i]
        total += (cum_p - cum_o) ** 2
    return total / 2.0


def log_loss_1x2(p_home, p_draw, p_away, obs):
    p = {"H": p_home, "D": p_draw, "A": p_away}[obs]
    return -math.log(max(1e-9, p))


def outcome(gl, gv):
    return "H" if gl > gv else ("D" if gl == gv else "A")


# ── λ por ranking FIFA (baseline al estilo del motor actual) ─────────────────
def lambdas_ranking(local, visitante):
    """Replica el fallback de ranking del motor: si ambos equipos tienen ranking,
    devuelve (λ_local, λ_visit); si no, None."""
    rl = _FIFA_RANK.get(_pretty(local))
    rv = _FIFA_RANK.get(_pretty(visitante))
    if rl is None or rv is None:
        return None
    diff = (rv - rl) / 20.0
    xg_l = max(0.3, 1.4 + diff * 0.5)
    xg_v = max(0.3, 1.4 - diff * 0.5)
    return xg_l, xg_v


# El _FIFA_RANK usa nombres con mayúscula tipo "Argentina"; mapeamos desde el raw.
def _pretty(name):
    return name  # los raw de martj42 ya vienen capitalizados ("Argentina")


def probs_desde_lambdas(lam_l, lam_v, rho=0.0):
    M = dc.matriz_marcadores(lam_l, lam_v, rho)
    p_h = float(np.tril(M, -1).sum())
    p_d = float(np.trace(M))
    p_a = float(np.triu(M, 1).sum())
    # argmax marcador exacto
    i, j = np.unravel_index(np.argmax(M), M.shape)
    return p_h, p_d, p_a, f"{i}-{j}"


# ── Backtest walk-forward ────────────────────────────────────────────────────
def correr(test_years=(2023, 2024, 2025), desde=2018):
    filas = _cargar_datos()
    if not filas:
        print("Sin datos."); return

    acc = {
        "dc": {"rps": [], "ll": [], "hit": 0, "exact": 0},
        "base": {"rps": [], "ll": [], "hit": 0, "exact": 0},
        "rank": {"rps": [], "ll": [], "hit": 0, "exact": 0, "n": 0},
        "dc_rank": {"rps": [], "ll": [], "hit": 0, "exact": 0, "n": 0},  # DC en el MISMO subset que rank
    }
    n_test = 0
    n_cubiertos = 0

    for Y in test_years:
        corte = f"{Y-1}-12-31"
        print(f"\n[Entrenando Dixon-Coles con {desde}..{Y-1}, probando {Y}…]")
        modelo = dc.entrenar(desde_anio=desde, hasta_fecha=corte, ref_fecha=corte, guardar=False)
        if not modelo:
            print(f"  (datos insuficientes para {Y})"); continue
        idx = modelo["idx"]

        # Base rate del set de entrenamiento
        train = [r for r in filas if f"{desde}-01-01" <= r["fecha"] <= corte]
        out_train = [outcome(r["goles_local"], r["goles_visita"]) for r in train]
        c = Counter(out_train)
        tot = max(1, len(out_train))
        base_p = (c["H"] / tot, c["D"] / tot, c["A"] / tot)
        # Marcador más común en entrenamiento (base rate de marcador exacto)
        scores = Counter((min(r["goles_local"], MAXG), min(r["goles_visita"], MAXG)) for r in train)
        base_score = "{}-{}".format(*scores.most_common(1)[0][0])

        test = [r for r in filas if r["fecha"][:4] == str(Y)]
        cubiertos_year = 0
        for r in test:
            n_test += 1
            if r["local"] not in idx or r["visita"] not in idx:
                continue
            n_cubiertos += 1
            cubiertos_year += 1
            obs = outcome(r["goles_local"], r["goles_visita"])
            exact_real = "{}-{}".format(min(r["goles_local"], MAXG), min(r["goles_visita"], MAXG))

            # ── Dixon-Coles ──
            lam = dc.get_lambdas(r["local_raw"], r["visita_raw"],
                                 neutral=r.get("neutral", False), modelo=modelo)
            ph, pd, pa, exact_dc = probs_desde_lambdas(lam[0], lam[1], modelo["rho"])
            acc["dc"]["rps"].append(rps_1x2(ph, pd, pa, obs))
            acc["dc"]["ll"].append(log_loss_1x2(ph, pd, pa, obs))
            pred = "H" if ph >= pd and ph >= pa else ("D" if pd >= pa else "A")
            acc["dc"]["hit"] += (pred == obs)
            acc["dc"]["exact"] += (exact_dc == exact_real)

            # ── Base rate ──
            bph, bpd, bpa = base_p
            acc["base"]["rps"].append(rps_1x2(bph, bpd, bpa, obs))
            acc["base"]["ll"].append(log_loss_1x2(bph, bpd, bpa, obs))
            bpred = "H" if bph >= bpd and bph >= bpa else ("D" if bpd >= bpa else "A")
            acc["base"]["hit"] += (bpred == obs)
            acc["base"]["exact"] += (base_score == exact_real)

            # ── λ por ranking (subset informativo) ──
            lr = lambdas_ranking(r["local_raw"], r["visita_raw"])
            if lr:
                rph, rpd, rpa, exact_rk = probs_desde_lambdas(lr[0], lr[1], 0.0)
                acc["rank"]["rps"].append(rps_1x2(rph, rpd, rpa, obs))
                acc["rank"]["ll"].append(log_loss_1x2(rph, rpd, rpa, obs))
                rpred = "H" if rph >= rpd and rph >= rpa else ("D" if rpd >= rpa else "A")
                acc["rank"]["hit"] += (rpred == obs)
                acc["rank"]["exact"] += (exact_rk == exact_real)
                acc["rank"]["n"] += 1
                # Dixon-Coles en el MISMO subset (comparación justa)
                acc["dc_rank"]["rps"].append(rps_1x2(ph, pd, pa, obs))
                acc["dc_rank"]["ll"].append(log_loss_1x2(ph, pd, pa, obs))
                acc["dc_rank"]["hit"] += (pred == obs)
                acc["dc_rank"]["exact"] += (exact_dc == exact_real)
                acc["dc_rank"]["n"] += 1

        print(f"  Partidos {Y}: {len(test)} | predichos por el modelo: {cubiertos_year}")

    # ── Reporte ──
    n_dc = len(acc["dc"]["rps"])
    if n_dc == 0:
        print("\nSin partidos cubiertos."); return
    n_rk = acc["rank"]["n"]

    def fila(nombre, d, n):
        rps = np.mean(d["rps"])
        ll = np.mean(d["ll"])
        return (f"{nombre:<22} RPS {rps:.4f} | LogLoss {ll:.4f} | "
                f"Acc 1X2 {100*d['hit']/n:5.1f}% | Marcador {100*d['exact']/n:4.1f}%")

    print("\n" + "=" * 78)
    print(f"RESULTADOS OUT-OF-SAMPLE — {n_dc} partidos de selecciones (años {list(test_years)})")
    print(f"Cobertura del modelo: {n_cubiertos}/{n_test} partidos ({100*n_cubiertos/max(1,n_test):.0f}%)")
    print("=" * 78)
    print(fila("Base rate (sin skill)", acc["base"], n_dc))
    print(fila("DIXON-COLES", acc["dc"], n_dc))
    print("-" * 78)
    print(f"Subset con ranking FIFA ({n_rk} partidos) — mismos partidos, dos modelos:")
    if n_rk:
        print(fila("  λ por ranking (motor)", acc["rank"], n_rk))
        print(fila("  λ Dixon-Coles", acc["dc_rank"], n_rk))
    print("=" * 78)

    rps_base = np.mean(acc["base"]["rps"])
    rps_dc = np.mean(acc["dc"]["rps"])
    ll_base = np.mean(acc["base"]["ll"])
    ll_dc = np.mean(acc["dc"]["ll"])
    skill_rps = 100 * (rps_base - rps_dc) / rps_base
    skill_ll = 100 * (ll_base - ll_dc) / ll_base
    print(f"\nMEJORA Dixon-Coles vs base rate:  RPS {skill_rps:+.1f}%  |  LogLoss {skill_ll:+.1f}%")
    print(f"Accuracy marcador exacto Dixon-Coles: {100*acc['dc']['exact']/n_dc:.1f}% "
          f"(el video esperaba 15-20%)")


def calibracion_picks(test_years=(2023, 2024, 2025), desde=2018):
    """¿Cuándo el modelo marca un mercado como pick, qué tan seguido gana de verdad
    (out-of-sample)? Compara probabilidad predicha vs. tasa real de aciertos. Si
    coinciden, los picks están bien calibrados y son confiables."""
    filas = _cargar_datos()
    # (nombre, clave en mercados, umbral, evaluador(gl,gv)) — mismos umbrales que el motor
    # Umbrales = los del motor (_picks_dixon_coles), ya recalibrados con este backtest
    MERCADOS = [
        ("LOCAL",      "local",     55, lambda gl, gv: gl > gv),
        ("VISITANTE",  "visitante", 55, lambda gl, gv: gv > gl),
        ("OVER 1.5",   "over_1.5",  70, lambda gl, gv: gl + gv >= 2),
        ("OVER 2.5",   "over_2.5",  55, lambda gl, gv: gl + gv >= 3),
        ("OVER 3.5",   "over_3.5",  63, lambda gl, gv: gl + gv >= 4),
        ("UNDER 1.5",  "under_1.5", 72, lambda gl, gv: gl + gv <= 1),
        ("UNDER 2.5",  "under_2.5", 68, lambda gl, gv: gl + gv <= 2),
        ("BTTS",       "btts_si",   65, lambda gl, gv: gl > 0 and gv > 0),
        ("DOBLE 1X",   "doble_1x",  78, lambda gl, gv: gl >= gv),
        ("DOBLE X2",   "doble_x2",  78, lambda gl, gv: gv >= gl),
    ]
    stats = {n: {"n": 0, "hit": 0, "psum": 0.0} for n, _, _, _ in MERCADOS}

    for Y in test_years:
        corte = f"{Y-1}-12-31"
        modelo = dc.entrenar(desde_anio=desde, hasta_fecha=corte, ref_fecha=corte, guardar=False)
        if not modelo:
            continue
        idx = modelo["idx"]
        test = [r for r in filas if r["fecha"][:4] == str(Y)
                and r["local"] in idx and r["visita"] in idx]
        for r in test:
            pr = dc.predecir(r["local_raw"], r["visita_raw"],
                             neutral=r.get("neutral", False), modelo=modelo)
            if not pr.get("disponible"):
                continue
            m = pr["mercados"]
            gl, gv = r["goles_local"], r["goles_visita"]
            for name, key, thr, ev in MERCADOS:
                if name == "DOBLE 1X" and not (m["local"] > m["visitante"]):
                    continue
                if name == "DOBLE X2" and not (m["visitante"] > m["local"]):
                    continue
                if m.get(key, 0) >= thr:
                    s = stats[name]
                    s["n"] += 1
                    s["psum"] += m[key]
                    s["hit"] += 1 if ev(gl, gv) else 0

    print("\n" + "=" * 78)
    print("CALIBRACIÓN DE PICKS — cuando el modelo marca el mercado, ¿gana? (out-of-sample)")
    print("=" * 78)
    print(f"{'Mercado':<14}{'# picks':>9}{'prob media':>12}{'gana real':>11}{'gap':>8}")
    print("-" * 78)
    for name, _, _, _ in MERCADOS:
        s = stats[name]
        if s["n"] == 0:
            continue
        pred = s["psum"] / s["n"]
        real = 100 * s["hit"] / s["n"]
        print(f"{name:<14}{s['n']:>9}{pred:>11.1f}%{real:>10.1f}%{real-pred:>+7.1f}")
    print("=" * 78)
    print("gap ≈ 0 → bien calibrado. gap positivo → gana MÁS de lo que dice (conservador).")
    print("(Mercados HT no evaluables: el dataset no trae marcador al descanso.)")


if __name__ == "__main__":
    correr()
    calibracion_picks()
