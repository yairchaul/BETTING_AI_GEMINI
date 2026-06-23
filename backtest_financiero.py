# -*- coding: utf-8 -*-
"""
BACKTEST FINANCIERO — Criterio de Kelly + curva de capital (equity curve).

Es el "paso 3" del método del reel: ya no medimos solo si el modelo acierta
(eso es el walk-forward + RPS), sino si su ventaja se traduce en GANANCIA real
apostando con gestión de banca.

Procedimiento:
  1. Walk-forward: por ventana entrena Dixon-Coles con datos <= corte.
  2. Para cada partido del trimestre siguiente, una "casa" sintética fija cuotas
     a partir de un modelo + margen (vig). El apostador usa Dixon-Coles.
  3. Si la prob del modelo del apostador supera la implícita de la cuota
     (valor esperado > 1 + umbral), se apuesta con fracción de Kelly.
  4. Se simula la banca partido a partido → curva de capital, ROI, drawdown.

⚠️ HONESTIDAD: NO tenemos cuotas históricas reales (The Odds API solo da las de
hoy). Por eso la casa es SINTÉTICA. Para que el test sea honesto incluimos un
escenario de CONTROL donde la casa es tan buena como el apostador (mismo modelo
+ vig): ahí el apostador DEBE perder (la comisión te mata). Solo si la casa usa
un modelo MÁS DÉBIL que el tuyo deberías ganar — esa es la única forma real de
tener ventaja. Las casas reales son muy afiladas, así que esto es una cota
superior optimista, no una promesa de ganancia.

Uso:  python backtest_financiero.py [primer_corte] [paso_meses]
"""
import os
import sys
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

OUT_PATH = os.path.join("data", "backtest_financiero.json")


# Reutiliza el harness walk-forward (predictores + utilidades de ventana)
from backtest_walkforward import (
    PredictorDixonColes, PredictorML, _entrenar_dc, _entrenar_ml,
    _add_months, _resultado, HOME, DRAW, AWAY,
)


def _odds_casa(probs_casa, vig, max_odds=26.0):
    """Cuotas decimales de la casa con sobre-redondeo (overround) = vig.
    probs_casa: (pL, pE, pV) del modelo de la casa. Se topan en max_odds porque
    ninguna casa real ofrece cuotas absurdas en un 1X2 (evita explosiones)."""
    return tuple(min(max_odds, 1.0 / (p * (1.0 + vig))) if p > 1e-6 else max_odds
                 for p in probs_casa)


def _kelly(p, odds):
    """Fracción de Kelly para una cuota decimal. f* = (p·odds - 1)/(odds - 1).
    Negativa (sin valor) → 0."""
    b = odds - 1.0
    if b <= 0:
        return 0.0
    return max(0.0, (p * odds - 1.0) / b)


def _max_drawdown(equity):
    """Máxima caída desde un pico (en %)."""
    pico = -1e18
    mdd = 0.0
    for v in equity:
        pico = max(pico, v)
        if pico > 0:
            mdd = max(mdd, (pico - v) / pico)
    return round(mdd * 100, 1)


def _max_drawdown_abs(equity):
    """Máxima caída desde un pico, en valor absoluto (unidades). Sirve para la
    curva de gestión plana, que puede ser negativa."""
    pico = -1e18
    mdd = 0.0
    for v in equity:
        pico = max(pico, v)
        mdd = max(mdd, pico - v)
    return mdd


def _recolectar_apuestas(primer_corte, paso_meses, vig, modelo_casa, shrink_casa, desde_anio):
    """Walk-forward: junta (fecha, probs_apostador_DC, cuotas_casa, resultado) de
    todos los partidos de prueba, en orden cronológico."""
    from motors.international_results import _cargar_datos
    datos = [r for r in _cargar_datos() if r.get("fecha") and len(r["fecha"]) >= 10]
    datos.sort(key=lambda x: x["fecha"])

    pred_dc = PredictorDixonColes(desde_anio)
    pred_ml = PredictorML(desde_anio) if modelo_casa == "ml" else None

    hoy = datetime.now()
    corte = datetime.strptime(primer_corte, "%Y-%m-%d")
    apuestas = []

    while corte < hoy:
        fin = _add_months(corte, paso_meses)
        cs, fs = corte.strftime("%Y-%m-%d"), fin.strftime("%Y-%m-%d")
        test = [r for r in datos if cs < r["fecha"][:10] <= fs]
        if not test:
            corte = fin
            continue
        mdc = pred_dc.entrenar(cs)
        mml = pred_ml.entrenar(cs) if pred_ml else None
        for r in test:
            pr_dc = pred_dc.predecir(mdc, r["local"], r["visita"], r.get("neutral", False))
            if not pr_dc or not pr_dc[0]:
                continue
            dc_probs = pr_dc[0]
            if modelo_casa == "dc":
                casa_probs = dc_probs
            else:
                pr_ml = pred_ml.predecir(mml, r["local"], r["visita"], r.get("neutral", False))
                if not pr_ml or not pr_ml[0]:
                    continue
                casa_probs = pr_ml[0]
            if shrink_casa > 0:
                casa_probs = tuple((1 - shrink_casa) * p + shrink_casa / 3.0 for p in casa_probs)
            odds = _odds_casa(casa_probs, vig)
            outcome = _resultado(r["goles_local"], r["goles_visita"])
            apuestas.append((r["fecha"][:10], dc_probs, odds, outcome))
        corte = fin
    return apuestas


def simular(primer_corte="2021-01-01", paso_meses=3, vig=0.05, kelly_frac=0.25,
            umbral_ev=0.05, modelo_casa="ml", shrink_casa=0.0, banca0=100.0,
            cap_frac=0.05, desde_anio=2018):
    """Simula los value bets con DOS gestiones de banca:
      • PLANO (1 unidad por apuesta): robusto, da el YIELD honesto (ganancia por
        unidad apostada), sin el efecto de bola de nieve del interés compuesto.
      • KELLY fraccional: muestra el crecimiento compuesto de la banca."""
    apuestas = _recolectar_apuestas(primer_corte, paso_meses, vig, modelo_casa, shrink_casa, desde_anio)

    # ── Gestión PLANA (1 unidad/apuesta) ────────────────────────────────────
    profit = 0.0
    eq_plano = [0.0]
    n_bets = wins = 0
    for _f, dc_probs, odds, outcome in apuestas:
        ev, o = max((dc_probs[k] * odds[k] - 1.0, k) for k in range(3))
        if ev <= umbral_ev:
            continue
        n_bets += 1
        if outcome == o:
            profit += odds[o] - 1.0
            wins += 1
        else:
            profit -= 1.0
        eq_plano.append(profit)

    # ── Gestión KELLY fraccional (banca compuesta) ──────────────────────────
    banca = banca0
    eq_kelly = [banca]
    for _f, dc_probs, odds, outcome in apuestas:
        ev, o = max((dc_probs[k] * odds[k] - 1.0, k) for k in range(3))
        if ev <= umbral_ev:
            continue
        f = min(_kelly(dc_probs[o], odds[o]) * kelly_frac, cap_frac)
        if f <= 0:
            continue
        stake = banca * f
        banca += stake * (odds[o] - 1.0) if outcome == o else -stake
        eq_kelly.append(banca)

    return {
        "escenario": f"casa={modelo_casa} shrink={shrink_casa} vig={vig}",
        "primer_corte": primer_corte, "paso_meses": paso_meses,
        "n_partidos": len(apuestas), "n_apuestas": n_bets,
        "hit_rate": round(wins / n_bets * 100, 1) if n_bets else 0.0,
        "profit_unidades": round(profit, 1),
        "yield_pct": round(profit / n_bets * 100, 2) if n_bets else 0.0,
        "max_dd_unidades": round(_max_drawdown_abs(eq_plano), 1),
        "kelly_banca_final": round(banca, 2),
        "kelly_roi_pct": round((banca - banca0) / banca0 * 100, 1),
        "kelly_max_dd_pct": _max_drawdown(eq_kelly),
        "kelly_frac": kelly_frac, "umbral_ev": umbral_ev,
    }


def _imprimir(reps):
    print("=" * 88)
    print("BACKTEST FINANCIERO — value betting + Kelly (casa SINTÉTICA)")
    print("=" * 88)
    print(f"{'ESCENARIO':<32}{'Apu':>6}{'Hit%':>7}{'Yield%':>9}{'Profit(u)':>11}{'MaxDD(u)':>10}")
    print("-" * 88)
    for rep in reps:
        print(f"{rep['escenario']:<32}{rep['n_apuestas']:>6}{rep['hit_rate']:>6.1f}%"
              f"{rep['yield_pct']:>8.2f}%{rep['profit_unidades']:>11.1f}{rep['max_dd_unidades']:>10.1f}")
    print("-" * 88)
    print("Yield = ganancia por unidad apostada (gestión plana, 1u/apuesta). Métrica honesta.")
    print("CONTROL (casa afilada, shrink≈0): el vig elimina el valor → ~0 apuestas.")
    print("Si AHÍ se ganara, el backtest estaría mal (no hay dinero gratis).")
    print("OJO: casa SINTÉTICA. Las reales son muy afiladas; 'casa débil' es una")
    print("cota superior optimista, NO una ganancia esperada. Sin cuotas históricas")
    print("reales no se puede prometer rentabilidad contra books profesionales.")
    print("=" * 88)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    primer_corte = sys.argv[1] if len(sys.argv) > 1 else "2021-01-01"
    paso = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    print(f"Simulando value betting + Kelly desde {primer_corte}, paso {paso}m...\n")
    escenarios = [
        # Casa con modelo MÁS DÉBIL (ML-GLM): cota superior si encuentras book soft.
        dict(modelo_casa="ml", shrink_casa=0.0, vig=0.05, umbral_ev=0.05),
        # Casa = DC pero más blanda (shrink 15%) y umbral 3%: caso intermedio realista.
        dict(modelo_casa="dc", shrink_casa=0.15, vig=0.05, umbral_ev=0.03),
        # CONTROL: casa tan afilada como tú (DC + vig). Debe dar ~0 apuestas.
        dict(modelo_casa="dc", shrink_casa=0.0, vig=0.05, umbral_ev=0.03),
    ]
    reps = []
    for e in escenarios:
        rep = simular(primer_corte=primer_corte, paso_meses=paso, **e)
        reps.append(rep)
        print(f"  {rep['escenario']}: {rep['n_apuestas']} apuestas, "
              f"yield {rep['yield_pct']}%, profit {rep['profit_unidades']}u", flush=True)
    print()
    _imprimir(reps)
    os.makedirs("data", exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(reps, f, ensure_ascii=False, indent=2)
