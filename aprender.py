# -*- coding: utf-8 -*-
"""
APRENDER — cierra el ciclo de aprendizaje del cerebro.

1. Resuelve picks pendientes contra resultados REALES (box_score_resolver).
2. Resuelve parlays pendientes a partir de sus legs (parlay_brain).
3. Recalcula la TASA REAL por mercado y por tipo de parlay.
4. Escribe data/aprendizaje_mercados.json (calibración) que el generador de
   parlays y el motor leen para preferir los mercados que MÁS aciertan.

Uso:
  python aprender.py             # recalcula desde lo ya resuelto + escribe calibración
  python aprender.py --resolver  # primero resuelve contra resultados reales (usa red)
"""
import os
import sys
import json
from datetime import datetime

CALIB_PATH = os.path.join("data", "aprendizaje_mercados.json")


def _resolver():
    if "--resolver" not in sys.argv:
        return
    print("Resolviendo contra resultados reales...")
    try:
        from motors.box_score_resolver import resolver_todo
        print("  picks:", resolver_todo(progreso_cb=lambda m: None))
    except Exception as e:
        print("  picks: error", e)
    try:
        from motors.parlay_brain import resolver_parlays_pendientes
        print("  parlays:", resolver_parlays_pendientes())
    except Exception as e:
        print("  parlays: error", e)


def aprender():
    _resolver()
    from motors.pick_memory import pick_memory
    from motors.parlay_brain import stats_por_tipo

    stats = pick_memory.stats()
    por_mercado = {}
    for nombre, d in stats.get("por_deporte_mercado", {}).items():
        # nombre = "MLB · PONCHES (K)"
        if d["total"] >= 5:                       # muestra mínima para confiar
            por_mercado[nombre] = {
                "win_rate": d["win_rate"], "roi": d["roi"], "total": d["total"],
                # factor de preferencia: <1 penaliza, >1 premia (centrado en 50%)
                "factor": round(max(0.4, min(1.5, 0.5 + d["win_rate"] / 100.0)), 2),
            }
    tipos = stats_por_tipo()

    calib = {
        "actualizado": datetime.now().isoformat(),
        "global": stats.get("global", {}),
        "por_mercado": por_mercado,
        "por_tipo_parlay": tipos,
        "ranking_mercados": sorted(
            [{"mercado": k, "win_rate": v["win_rate"], "roi": v["roi"], "n": v["total"]}
             for k, v in por_mercado.items()],
            key=lambda x: x["win_rate"], reverse=True),
    }
    os.makedirs("data", exist_ok=True)
    with open(CALIB_PATH, "w", encoding="utf-8") as f:
        json.dump(calib, f, ensure_ascii=False, indent=2)
    return calib


def factor_mercado_aprendido(deporte, mercado, default=1.0):
    """Lee el factor aprendido de un mercado (para el generador de parlays)."""
    try:
        with open(CALIB_PATH, encoding="utf-8") as f:
            calib = json.load(f)
        clave = f"{(deporte or '').upper()} · {mercado}"
        return calib.get("por_mercado", {}).get(clave, {}).get("factor", default)
    except Exception:
        return default


if __name__ == "__main__":
    c = aprender()
    print("=" * 64)
    print("APRENDIZAJE ACTUALIZADO —", c["actualizado"][:19])
    print("=" * 64)
    g = c["global"]
    print(f"Global: {g.get('aciertos',0)}/{g.get('total',0)} = {g.get('win_rate',0)}% · ROI {g.get('roi',0)}%")
    print("\nRanking de mercados (lo que MÁS acierta → el cerebro lo prefiere):")
    for r in c["ranking_mercados"]:
        print(f"  {r['mercado']:<26} {r['win_rate']:>5}%  ROI {r['roi']:+.0f}%  (n={r['n']})")
    if c["por_tipo_parlay"]:
        print("\nPor tipo de parlay:")
        for t, d in c["por_tipo_parlay"].items():
            print(f"  {t:<26} {d.get('win_rate',0)}%  ROI {d.get('roi',0):+.0f}%")
    print(f"\nCalibración escrita en {CALIB_PATH}")
