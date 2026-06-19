# -*- coding: utf-8 -*-
"""
BACKTEST DE PARLAYS Y MERCADOS — qué acertó, qué no, y cuál es el mejor parlay.

Une las piezas que ya existen:
  • box_score_resolver.resolver_todo()  → resuelve picks pendientes vs resultados reales
  • parlay_brain.resolver_parlays_pendientes() → marca parlays ganados/perdidos por sus legs
  • pick_memory.stats() → % de acierto por deporte y mercado (REAL)
  • parlay_brain.stats_por_tipo() → % de acierto y ROI por tipo de parlay

Reporta:
  1. Efectividad por MERCADO (cuáles mercados acierta más → en qué confiar).
  2. Efectividad por TIPO de parlay (SEGURO, VALOR, GIGANTE...).
  3. Detalle de los últimos parlays resueltos (legs que ganaron/perdieron).
  4. Propuesta de MEJOR PARLAY: arma uno solo con los mercados de mayor tasa real.

Uso:
  python backtest_parlays.py            # solo reporta (no toca la red)
  python backtest_parlays.py --resolver # primero resuelve picks vs resultados reales (usa red)
"""
import os
import sys
import json
from datetime import datetime

DATA = "data"


def _load(path, default):
    try:
        with open(os.path.join(DATA, path), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


# ── Umbral de confianza por mercado según su tasa real (se recalibra abajo) ──
MIN_WINRATE_PARA_PARLAY = 58.0   # solo mercados que históricamente ganan ≥58%


def resolver_si_pedido():
    if "--resolver" not in sys.argv:
        return
    print("Resolviendo picks pendientes contra resultados reales (puede tardar)...")
    try:
        from motors.box_score_resolver import resolver_todo
        r = resolver_todo(progreso_cb=lambda m: print("  ", m))
        print(f"  Picks resueltos: {r}")
    except Exception as e:
        print(f"  No se pudieron resolver picks: {e}")
    try:
        from motors.parlay_brain import resolver_parlays_pendientes
        n = resolver_parlays_pendientes()
        print(f"  Parlays resueltos: {n}")
    except Exception as e:
        print(f"  No se pudieron resolver parlays: {e}")


def efectividad_por_mercado():
    from motors.pick_memory import pick_memory
    s = pick_memory.stats()
    print("=" * 74)
    print("EFECTIVIDAD POR MERCADO (picks reales resueltos)")
    print("=" * 74)
    g = s.get("global", {})
    print(f"GLOBAL: {g.get('aciertos',0)}/{g.get('total',0)} = {g.get('win_rate',0)}% "
          f"· ROI {g.get('roi',0)}% · pendientes: {s.get('pendientes',0)}")
    print("-" * 74)
    filas = sorted(s.get("por_deporte_mercado", {}).items(),
                   key=lambda x: x[1]["win_rate"], reverse=True)
    confiables = []
    for nombre, d in filas:
        flag = "✅" if d["win_rate"] >= MIN_WINRATE_PARA_PARLAY else ("⚠️" if d["win_rate"] >= 45 else "❌")
        print(f"  {flag} {nombre:<26} {d['aciertos']:>3}/{d['total']:<3} = {d['win_rate']:>5}%  ROI {d['roi']:+.0f}%")
        if d["win_rate"] >= MIN_WINRATE_PARA_PARLAY and d["total"] >= 5:
            confiables.append((nombre, d))
    return confiables


def efectividad_por_tipo_parlay():
    from motors.parlay_brain import stats_por_tipo
    stats = stats_por_tipo()
    print("\n" + "=" * 74)
    print("EFECTIVIDAD POR TIPO DE PARLAY")
    print("=" * 74)
    if not stats:
        print("  (Aún no hay parlays resueltos. Se irán midiendo conforme se guarden y resuelvan.)")
        return
    for tipo, d in sorted(stats.items(), key=lambda x: x[1]["win_rate"], reverse=True):
        print(f"  {tipo:<26} {d['ganados']}/{d['total']} = {d['win_rate']}%  ROI {d['roi']:+.0f}%")


def detalle_parlays_resueltos(max_n=10):
    parlays = _load("parlay_history.json", [])
    picks = _load("pick_history.json", [])
    estado_por_pick = {(p.get("pick") or "").lower().strip(): p for p in picks}
    resueltos = [p for p in parlays if p.get("estado") in ("ganado", "perdido")]
    if not resueltos:
        return
    print("\n" + "=" * 74)
    print("DETALLE DE PARLAYS RESUELTOS (legs que acertaron / fallaron)")
    print("=" * 74)
    for par in resueltos[-max_n:]:
        ico = "✅ GANADO" if par["estado"] == "ganado" else "❌ PERDIDO"
        print(f"\n{ico} · {par.get('tipo')} · {par.get('fecha')} · cuota {par.get('cuota')}x")
        for leg in par.get("legs", []):
            pk = estado_por_pick.get((leg.get("pick") or "").lower().strip())
            est = pk.get("estado") if pk else "?"
            li = "✅" if est == "ganado" else "❌" if est == "perdido" else "•"
            print(f"   {li} {leg.get('pick')}  ({leg.get('mercado')} · {leg.get('evento')})")


def proponer_mejor_parlay(confiables, max_legs=5):
    """Arma parlays con picks de los mercados de MAYOR TASA REAL, usando la tasa
    real calibrada (no la confianza cruda del modelo) y limitando los legs para
    que la probabilidad combinada sea realista."""
    print("\n" + "=" * 74)
    print("MEJOR PARLAY SUGERIDO (mercados de alta tasa real · prob. calibrada)")
    print("=" * 74)
    if not confiables:
        print("  No hay mercados con tasa ≥ "
              f"{MIN_WINRATE_PARA_PARLAY}% y muestra suficiente todavía.")
        return
    # Tasa real por mercado (calibración): {mercado: win_rate}
    tasa_real = {nombre.split(" · ")[-1]: d["win_rate"] for nombre, d in confiables}
    print(f"  Mercados de confianza y su tasa real: "
          + ", ".join(f"{m} {t}%" for m, t in tasa_real.items()))
    picks = _load("pick_history.json", [])
    fechas = sorted({p.get("fecha_evento") or p.get("fecha") for p in picks})
    ult = fechas[-1] if fechas else ""
    cand = [p for p in picks
            if p.get("mercado") in tasa_real
            and (p.get("fecha_evento") or p.get("fecha")) == ult]
    cand = sorted(cand, key=lambda x: x.get("confianza", 0), reverse=True)
    vistos, legs = set(), []
    for p in cand:
        if p.get("evento") in vistos:
            continue
        vistos.add(p.get("evento"))
        legs.append(p)
    if not legs:
        print(f"  No hay picks recientes ({ult}) en los mercados confiables.")
        return

    # Mostrar el parlay para 3, 4 y max_legs legs usando la TASA REAL calibrada
    print(f"  Fecha: {ult} · candidatos disponibles: {len(legs)}")
    for n in sorted({3, 4, max_legs}):
        if len(legs) < n:
            continue
        sel = legs[:n]
        prob = cuota = 1.0
        for p in sel:
            pr = tasa_real.get(p.get("mercado"), 50) / 100.0   # tasa real, no confianza
            prob *= pr
            cuota *= float(p.get("cuota", 1.85) or 1.85)
        print(f"\n  ── Parlay de {n} legs ── prob. real ≈ {round(prob*100,1)}%  ·  "
              f"cuota {round(cuota,2)}x  ·  $100 -> ${round((cuota-1)*100):,}")
        for p in sel:
            print(f"     • {p.get('pick'):<40} {p.get('mercado')}  @{p.get('cuota')}")
    print("\n  Nota: la prob. usa la TASA REAL del mercado (backtest), no la confianza")
    print("  del modelo. A más legs, más pago pero MENOS probabilidad de acertar todo.")


if __name__ == "__main__":
    resolver_si_pedido()
    confiables = efectividad_por_mercado()
    efectividad_por_tipo_parlay()
    detalle_parlays_resueltos()
    proponer_mejor_parlay(confiables)
    print("\nListo. Usa --resolver para actualizar resultados reales antes del reporte.")
