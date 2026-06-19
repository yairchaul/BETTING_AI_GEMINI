# -*- coding: utf-8 -*-
"""
BACKTEST RUTA DB — Motor 1 de fútbol con HISTORIAL REAL (no ranking FIFA).

A diferencia de backtest_futbol_wc.py (que usa forzar_ranking), este puebla el
historial real de cada equipo (últimos 5, con goles de PRIMER TIEMPO reales) y
corre analizar_futbol_jerarquico por la ruta de DB — la que usa las reglas
corregidas (Regla 1 HT vía Poisson y Regla 7 ML+Over ≥60% como 1ª opción).

⚠️ LEAKAGE: el historial de cada equipo (descargado hoy) incluye el propio
partido evaluado. El número es orientativo del comportamiento de las reglas
sobre datos reales, no una simulación pre-partido pura.

Uso:  python backtest_futbol_db.py [liga] [dias]
"""
import os
import sys
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.WARNING)

OUT_PATH = os.path.join("data", "futbol_backtest_db.json")


def ejecutar(liga="FIFA World Cup", dias=8):
    from espn_futbol import ESPN_FUTBOL
    from motors.futbol_analyzer_jerarquico import analizar_futbol_jerarquico
    from motors.futbol_backtest_real import _grade_pick

    scraper = ESPN_FUTBOL()
    partidos = scraper.gestor.obtener_partidos(liga, dias_atras=int(dias))
    fin = [p for p in partidos
           if p.get("completado") and p.get("goles_local") is not None
           and p.get("goles_visitante") is not None]
    print(f"Partidos finalizados de '{liga}' (últimos {dias}d): {len(fin)}", flush=True)
    if not fin:
        return None

    # 1. Poblar historial REAL (con HT) de cada equipo una sola vez
    print("Poblando historial real (últimos 5 + HT) de los equipos...", flush=True)
    def _prog(i, n, nombre):
        print(f"  [{i}/{n}] {nombre}", flush=True)
    scraper.gestor.poblar_historial(fin, progreso_cb=_prog)

    # 2. Correr el motor por la ruta DB y graduar
    mercados = {k: {"aciertos": 0, "total": 0} for k in ("moneyline", "over_under", "btts", "combo")}
    detalle, no_eval = [], 0

    for p in fin:
        local = p.get("home") or p.get("local", "")
        visit = p.get("away") or p.get("visitante", "")
        gl, gv = int(p["goles_local"]), int(p["goles_visitante"])
        try:
            res = analizar_futbol_jerarquico(
                local, visit, es_torneo=p.get("es_torneo", False),
                fase=p.get("fase", ""), liga=liga, forzar_ranking=False)
        except Exception as e:
            logging.warning(f"motor falló {local} vs {visit}: {e}")
            continue
        pick = res.get("pick", "")
        mercado, acierto = _grade_pick(pick, gl, gv, local, visit)
        if mercado is None or acierto is None:
            no_eval += 1
            detalle.append({"partido": f"{local} {gl}-{gv} {visit}", "pick": pick,
                            "regla": res.get("regla"), "mercado": "(no eval)", "acierto": None})
            continue
        mercados[mercado]["total"] += 1
        if acierto:
            mercados[mercado]["aciertos"] += 1
        detalle.append({"partido": f"{local} {gl}-{gv} {visit}", "pick": pick,
                        "regla": res.get("regla"), "mercado": mercado,
                        "confianza": res.get("confianza"), "acierto": acierto})

    for m in mercados.values():
        m["precision"] = round(m["aciertos"] / m["total"] * 100, 1) if m["total"] else 0.0
    ag = sum(m["aciertos"] for m in mercados.values())
    tg = sum(m["total"] for m in mercados.values())
    glob = round(ag / tg * 100, 1) if tg else 0.0

    rep = {"timestamp": datetime.now().isoformat(), "liga": liga, "dias": int(dias),
           "partidos": len(fin), "evaluados": tg, "no_evaluables": no_eval,
           "precision_global": glob, "mercados": mercados, "detalle": detalle}
    os.makedirs("data", exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=2)
    return rep


def _imprimir(rep):
    print("=" * 80)
    print(f"BACKTEST RUTA DB — {rep['liga']} (historial real + HT)")
    print("=" * 80)
    print(f"{'PARTIDO':<36} {'PICK':<28} {'R':<3} {'OK'}")
    print("-" * 80)
    for d in rep["detalle"]:
        ok = "—" if d["acierto"] is None else ("OK" if d["acierto"] else "X")
        print(f"{d['partido'][:35]:<36} {str(d['pick'])[:27]:<28} {str(d.get('regla')):<3} {ok}")
    print("-" * 80)
    for nombre, m in rep["mercados"].items():
        if m["total"]:
            print(f"  {nombre:<12} {m['aciertos']:>2}/{m['total']:<2} = {m['precision']}%")
    print(f"\n  GLOBAL: {rep['evaluados']} evaluados · {rep['precision_global']}% · "
          f"{rep['no_evaluables']} no evaluables (HT no se puede calificar con marcador final)")
    print("=" * 80)


if __name__ == "__main__":
    liga = sys.argv[1] if len(sys.argv) > 1 else "FIFA World Cup"
    dias = sys.argv[2] if len(sys.argv) > 2 else 8
    rep = ejecutar(liga, dias)
    if rep:
        _imprimir(rep)
