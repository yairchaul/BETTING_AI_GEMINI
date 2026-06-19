# -*- coding: utf-8 -*-
"""
BACKTEST 1X2 — valida el predictor de resultado (local/empate/visitante) contra
los marcadores REALES del Mundial 2026. Mide:
  • Acierto del resultado 1X2 directo (incluido empate)
  • Acierto de la DOBLE OPORTUNIDAD sugerida (más segura)

Reutiliza el dataset de resultados reales de backtest_futbol_wc.py.
Uso:  python backtest_1x2.py
"""
import os
import json
from datetime import datetime

from motors.predictor_1x2 import predecir_1x2
from backtest_futbol_wc import PARTIDOS_WC

OUT = os.path.join("data", "backtest_1x2.json")


def _resultado_real(gl, gv):
    if gl > gv:
        return "LOCAL"
    if gl < gv:
        return "VISITANTE"
    return "EMPATE"


def _do_acierta(mercado, real):
    if mercado.startswith("1X"):
        return real in ("LOCAL", "EMPATE")
    if mercado.startswith("12"):
        return real in ("LOCAL", "VISITANTE")
    if mercado.startswith("X2"):
        return real in ("EMPATE", "VISITANTE")
    return False


def ejecutar():
    ok_1x2 = ok_do = total = 0
    por_resultado = {"LOCAL": [0, 0], "EMPATE": [0, 0], "VISITANTE": [0, 0]}
    detalle = []
    for fecha, local, visit, gl, gv, fase in PARTIDOS_WC:
        pred = predecir_1x2(local, visit, es_torneo=True, fase=fase)
        if not pred:
            continue
        real = _resultado_real(gl, gv)
        total += 1
        acierto = pred["resultado_probable"] == real
        ok_1x2 += 1 if acierto else 0
        do_ok = _do_acierta(pred["doble_oportunidad"]["mercado"], real)
        ok_do += 1 if do_ok else 0
        por_resultado[real][0] += 1
        por_resultado[real][1] += 1 if acierto else 0
        detalle.append({
            "partido": f"{local} {gl}-{gv} {visit}", "real": real,
            "pred": pred["resultado_probable"], "prob": pred["prob"],
            "do": pred["doble_oportunidad"]["mercado"], "do_prob": pred["doble_oportunidad"]["prob"],
            "ok_1x2": acierto, "ok_do": do_ok,
        })

    rep = {
        "timestamp": datetime.now().isoformat(), "partidos": total,
        "acierto_1x2": round(ok_1x2 / total * 100, 1) if total else 0,
        "acierto_doble_oportunidad": round(ok_do / total * 100, 1) if total else 0,
        "por_resultado_real": {k: {"total": v[0], "aciertos": v[1],
                                   "precision": round(v[1] / v[0] * 100, 1) if v[0] else 0}
                               for k, v in por_resultado.items()},
        "detalle": detalle,
    }
    os.makedirs("data", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=2)
    return rep


def _imprimir(r):
    print("=" * 72)
    print(f"BACKTEST 1X2 — {r['partidos']} partidos reales del Mundial 2026")
    print("=" * 72)
    print(f"{'PARTIDO':<34} {'REAL':<10} {'PRED':<10} {'P%':>5}  1X2 DO")
    print("-" * 72)
    for d in r["detalle"]:
        a = "✅" if d["ok_1x2"] else "❌"
        b = "✅" if d["ok_do"] else "❌"
        print(f"{d['partido'][:33]:<34} {d['real']:<10} {d['pred']:<10} {d['prob']:>5} {a} {b}")
    print("-" * 72)
    print(f"  Acierto 1X2 directo (con empate): {r['acierto_1x2']}%")
    print(f"  Acierto doble oportunidad:        {r['acierto_doble_oportunidad']}%")
    print("  Por resultado real:")
    for k, v in r["por_resultado_real"].items():
        print(f"    {k:<10} {v['aciertos']}/{v['total']} = {v['precision']}%")
    print("=" * 72)


if __name__ == "__main__":
    _imprimir(ejecutar())
