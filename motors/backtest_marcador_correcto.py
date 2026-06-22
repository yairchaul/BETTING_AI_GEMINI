# -*- coding: utf-8 -*-
"""
BACKTEST DE MARCADOR CORRECTO — valida las 3 opciones de marcador del modelo
Dixon-Coles contra los resultados REALES, y mide la "cercanía".

Idea (lo que pidió el usuario): para cada partido reciente de selecciones,
el modelo propone su Top-3 de marcadores. Aquí medimos:
  • ¿pegó EXACTO alguno? ¿en qué posición (1°, 2° o 3°)?
  • ¿cuál de los 3 fue el MÁS CERCANO? (distancia = |Δlocal| + |Δvisitante|)
  • ¿acertó al menos el RESULTADO 1X2 (gana/empata/pierde)?
Sirve de tablero de aprendizaje: ver dónde acierta y dónde se acerca para seguir
calibrando.

HONESTO: el modelo se entrena EXCLUYENDO la ventana de prueba (out-of-sample), no
con los mismos partidos que evalúa.
"""
import logging
from datetime import datetime, timedelta

from motors.international_results import _cargar_datos
from motors import dixon_coles as dc

logger = logging.getLogger(__name__)


def _outcome(gl, gv):
    return "LOCAL" if gl > gv else ("EMPATE" if gl == gv else "VISITANTE")


def _parse(marcador):
    a, b = marcador.split("-")
    return int(a), int(b)


def backtest_marcador(dias=10, desde_anio=2018, max_partidos=120):
    """Backtest out-of-sample del marcador correcto sobre los últimos `dias` de
    partidos internacionales con resultado. Devuelve dict {resumen, partidos}."""
    filas = _cargar_datos()
    if not filas:
        return {"resumen": {}, "partidos": [], "error": "sin datos"}

    fin = max(r["fecha"] for r in filas)
    try:
        fin_dt = datetime.strptime(fin[:10], "%Y-%m-%d")
    except Exception:
        return {"resumen": {}, "partidos": [], "error": "fecha inválida"}
    inicio_dt = fin_dt - timedelta(days=dias)
    inicio = inicio_dt.strftime("%Y-%m-%d")
    corte = (inicio_dt - timedelta(days=1)).strftime("%Y-%m-%d")  # entrena ANTES de la ventana

    # Modelo entrenado SIN la ventana de prueba (out-of-sample)
    modelo = dc.entrenar(desde_anio=desde_anio, hasta_fecha=corte, ref_fecha=corte, guardar=False)
    if not modelo:
        return {"resumen": {}, "partidos": [], "error": "datos insuficientes para entrenar"}
    idx = modelo["idx"]

    test = [r for r in filas if inicio <= r["fecha"] <= fin
            and r["local"] in idx and r["visita"] in idx]
    test.sort(key=lambda r: r["fecha"], reverse=True)
    test = test[:max_partidos]

    partidos = []
    n = top1 = top3 = outcome_ok = cerca1 = 0
    suma_dist = 0
    for r in test:
        pred = dc.predecir(r["local_raw"], r["visita_raw"],
                           neutral=r.get("neutral", False), modelo=modelo)
        if not pred.get("disponible"):
            continue
        top = pred["marcador_top"][:3]
        if not top:
            continue
        gl, gv = r["goles_local"], r["goles_visita"]
        real = f"{gl}-{gv}"
        n += 1

        # ¿exacto y en qué posición?
        rank = next((i + 1 for i, t in enumerate(top) if t["marcador"] == real), None)
        if rank == 1:
            top1 += 1
        if rank:
            top3 += 1

        # cuál de los 3 más cercano + distancia mínima
        dists = []
        for t in top:
            pa, pb = _parse(t["marcador"])
            dists.append(abs(pa - gl) + abs(pb - gv))
        dist_min = min(dists)
        idx_cerca = dists.index(dist_min)
        suma_dist += dist_min
        if dist_min <= 1:
            cerca1 += 1

        # ¿acertó el 1X2 con el marcador #1?
        out_ok = (top[0]["resultado"] == _outcome(gl, gv))
        if out_ok:
            outcome_ok += 1

        partidos.append({
            "fecha": r["fecha"],
            "local": r["local_raw"], "visitante": r["visita_raw"],
            "real": real,
            "top3": [f"{t['marcador']} ({t['pct']}%)" for t in top],
            "exacto_rank": rank,                 # 1, 2, 3 o None
            "mas_cercano": top[idx_cerca]["marcador"],
            "distancia": dist_min,               # 0 = exacto
            "outcome_ok": out_ok,
            "torneo": r.get("torneo", ""),
        })

    resumen = {
        "partidos": n,
        "ventana_dias": dias,
        "desde": inicio, "hasta": fin,
        "exacto_top1_pct": round(100 * top1 / n, 1) if n else 0,
        "exacto_top3_pct": round(100 * top3 / n, 1) if n else 0,
        "outcome_1x2_pct": round(100 * outcome_ok / n, 1) if n else 0,
        "cerca_1gol_pct": round(100 * cerca1 / n, 1) if n else 0,
        "distancia_media": round(suma_dist / n, 2) if n else 0,
    }
    logger.info(f"[marcador-backtest] {n} partidos | exacto top3 {resumen['exacto_top3_pct']}% "
                f"| 1X2 {resumen['outcome_1x2_pct']}% | dist media {resumen['distancia_media']}")
    return {"resumen": resumen, "partidos": partidos}


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    rep = backtest_marcador(dias=10)
    r = rep["resumen"]
    print(f"\n=== MARCADOR CORRECTO — últimos {r.get('ventana_dias')} días "
          f"({r.get('desde')} → {r.get('hasta')}) ===")
    print(f"Partidos: {r.get('partidos')}")
    print(f"Exacto en Top-1: {r.get('exacto_top1_pct')}%  |  Exacto en Top-3: {r.get('exacto_top3_pct')}%")
    print(f"Acertó resultado 1X2 (marcador #1): {r.get('outcome_1x2_pct')}%")
    print(f"Se acercó (≤1 gol de distancia): {r.get('cerca_1gol_pct')}%  |  Distancia media: {r.get('distancia_media')}")
    print("\nDetalle (más recientes):")
    for p in rep["partidos"][:25]:
        mark = "✅EXACTO" if p["exacto_rank"] else ("🎯1X2" if p["outcome_ok"] else f"d={p['distancia']}")
        rank = f" (#{p['exacto_rank']})" if p["exacto_rank"] else ""
        print(f"  {p['fecha']} {p['local']} {p['real']} {p['visitante']:<22} "
              f"pred {p['top3'][0]}{rank}  [{mark}]")
