# -*- coding: utf-8 -*-
"""
BACKTEST OFFLINE — Motor 1 de fútbol (analizar_futbol_jerarquico) sobre los
partidos REALES del Mundial 2026 con marcador conocido.

- Reproduce el pick que mostró la tarjeta usando forzar_ranking=True
  (lógica pre-partido por ranking FIFA, SIN leakage de datos post-juego).
- Califica cada pick contra el marcador real con el mismo grader del backtest
  oficial (_grade_pick de motors/futbol_backtest_real).
- Reporta precisión por mercado (moneyline, over_under, btts, combo) y global.

Uso:  python backtest_futbol_wc.py
Salida: data/futbol_backtest_wc.json  +  tabla por consola.
"""
import os
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.WARNING)

# ── Dataset: partidos finalizados del Mundial 2026 (marcador real) ───────────
# (fecha, local, visitante, goles_local, goles_visitante, fase)
PARTIDOS_WC = [
    ("2026-06-18", "Czechia", "South Africa", 1, 1, "Grupo"),
    ("2026-06-18", "Switzerland", "Bosnia-Herzegovina", 4, 1, "Grupo"),
    ("2026-06-18", "Canada", "Qatar", 6, 0, "Grupo"),
    ("2026-06-19", "Mexico", "South Korea", 1, 0, "Grupo"),
    ("2026-06-17", "Austria", "Jordan", 3, 1, "Grupo"),
    ("2026-06-17", "Portugal", "Congo DR", 1, 1, "Grupo"),
    ("2026-06-17", "England", "Croatia", 4, 2, "Grupo"),
    ("2026-06-17", "Ghana", "Panama", 1, 0, "Grupo"),
    ("2026-06-18", "Uzbekistan", "Colombia", 1, 3, "Grupo"),
    ("2026-06-16", "France", "Senegal", 3, 1, "Grupo"),
    ("2026-06-16", "Iraq", "Norway", 1, 4, "Grupo"),
    ("2026-06-17", "Argentina", "Algeria", 3, 0, "Grupo"),
    ("2026-06-15", "Spain", "Cape Verde", 0, 0, "Grupo"),
    ("2026-06-15", "Belgium", "Egypt", 1, 1, "Grupo"),
    ("2026-06-15", "Saudi Arabia", "Uruguay", 1, 1, "Grupo"),
    ("2026-06-16", "Iran", "New Zealand", 2, 2, "Grupo"),
    ("2026-06-14", "Australia", "Türkiye", 2, 0, "Grupo"),
    ("2026-06-14", "Germany", "Curaçao", 7, 1, "Grupo"),
    ("2026-06-14", "Netherlands", "Japan", 2, 2, "Grupo"),
    ("2026-06-14", "Ivory Coast", "Ecuador", 1, 0, "Grupo"),
    ("2026-06-15", "Sweden", "Tunisia", 5, 1, "Grupo"),
    ("2026-06-13", "Qatar", "Switzerland", 1, 1, "Grupo"),
    ("2026-06-13", "Brazil", "Morocco", 1, 1, "Grupo"),
    ("2026-06-14", "Haiti", "Scotland", 0, 1, "Grupo"),
    ("2026-06-12", "Canada", "Bosnia-Herzegovina", 1, 1, "Grupo"),
]

OUT_PATH = os.path.join("data", "futbol_backtest_wc.json")


def ejecutar(forzar_ranking: bool = True):
    from motors.futbol_analyzer_jerarquico import analizar_futbol_jerarquico
    from motors.futbol_backtest_real import _grade_pick

    mercados = {
        "moneyline": {"aciertos": 0, "total": 0},
        "over_under": {"aciertos": 0, "total": 0},
        "btts": {"aciertos": 0, "total": 0},
        "combo": {"aciertos": 0, "total": 0},
    }
    detalle = []
    no_evaluables = []

    for fecha, local, visit, gl, gv, fase in PARTIDOS_WC:
        try:
            res = analizar_futbol_jerarquico(
                local, visit, es_torneo=True, fase=fase,
                forzar_ranking=forzar_ranking,
            )
        except Exception as e:
            no_evaluables.append((f"{local} vs {visit}", f"ERROR motor: {e}"))
            continue

        pick = res.get("pick", "")
        conf = res.get("confianza", 0)
        regla = res.get("regla", res.get("regla_motor_1", "?"))
        mercado, acierto = _grade_pick(pick, gl, gv, local, visit)

        if mercado is None or acierto is None:
            no_evaluables.append((f"{local} {gl}-{gv} {visit}", f"{pick} (no evaluable)"))
            continue

        mercados[mercado]["total"] += 1
        if acierto:
            mercados[mercado]["aciertos"] += 1
        detalle.append({
            "fecha": fecha,
            "partido": f"{local} {gl}-{gv} {visit}",
            "pick": pick,
            "regla": regla,
            "mercado": mercado,
            "confianza": conf,
            "acierto": acierto,
        })

    for m in mercados.values():
        m["precision"] = round(m["aciertos"] / m["total"] * 100, 1) if m["total"] else 0.0

    aciertos_glob = sum(m["aciertos"] for m in mercados.values())
    total_glob = sum(m["total"] for m in mercados.values())
    precision_global = round(aciertos_glob / total_glob * 100, 1) if total_glob else 0.0

    reporte = {
        "timestamp": datetime.now().isoformat(),
        "fuente": "Mundial 2026 (marcador real, forzar_ranking=%s)" % forzar_ranking,
        "partidos": len(PARTIDOS_WC),
        "evaluados": total_glob,
        "no_evaluables": len(no_evaluables),
        "precision_global": precision_global,
        "mercados": mercados,
        "detalle": detalle,
        "detalle_no_evaluables": no_evaluables,
    }

    os.makedirs("data", exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(reporte, f, ensure_ascii=False, indent=2)

    return reporte


def _imprimir(rep: dict):
    print("=" * 78)
    print(f"BACKTEST MOTOR 1 FÚTBOL — {rep['fuente']}")
    print("=" * 78)
    print(f"{'FECHA':<11} {'PARTIDO':<34} {'PICK':<26} {'R':<2} {'OK'}")
    print("-" * 78)
    for d in rep["detalle"]:
        ok = "✅" if d["acierto"] else "❌"
        print(f"{d['fecha']:<11} {d['partido'][:33]:<34} {d['pick'][:25]:<26} "
              f"{str(d['regla']):<2} {ok}")
    print("-" * 78)
    print("PRECISIÓN POR MERCADO:")
    for nombre, m in rep["mercados"].items():
        if m["total"]:
            print(f"  {nombre:<12} {m['aciertos']:>2}/{m['total']:<2} = {m['precision']}%")
    print(f"\n  GLOBAL: {rep['evaluados']} picks evaluados · {rep['precision_global']}% aciertos")
    if rep["no_evaluables"]:
        print(f"\n  No evaluables ({rep['no_evaluables']}):")
        for partido, motivo in rep["detalle_no_evaluables"]:
            print(f"    - {partido}: {motivo}")
    print("=" * 78)


if __name__ == "__main__":
    reporte = ejecutar(forzar_ranking=True)
    _imprimir(reporte)
