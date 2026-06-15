# -*- coding: utf-8 -*-
"""
MLB MOTOR BACKTESTER — Valida Moneyline y Over/Under contra resultados reales.

Para los últimos N días usa la MLB Stats API (que da el récord AL MOMENTO del
juego + el marcador final):
  • Moneyline: predice el equipo con mejor récord y comprueba si ganó.
  • Over/Under: mide cuántos juegos pasaron de la línea típica (8.5 carreras).

Agrupa por la diferencia de récord (proxy de confianza) → permite ver en qué
tramo el heurístico atina más, y escribe una calibración que el motor puede leer.

Escribe data/mlb_motor_backtest.json + data/mlb_calibracion.json
Uso:  python -m motors.mlb_motor_backtester [dias]
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta
from collections import defaultdict

HEADERS = {'User-Agent': 'Mozilla/5.0'}
REPORTE_PATH = os.path.join("data", "mlb_motor_backtest.json")
CALIB_PATH = os.path.join("data", "mlb_calibracion.json")
LINEA_OU = 8.5  # línea estándar de carreras


def _get_json(url, timeout=12):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def _pct(record):
    try:
        return float(record.get('pct', 0)) if record else 0.5
    except Exception:
        return 0.5


def ejecutar_mlb_backtest(dias=15, progreso_cb=None):
    """Backtest de moneyline (por récord) y over/under en los últimos N días."""
    ml_tramos = defaultdict(lambda: {"juegos": 0, "aciertos": 0})
    ou_total = ou_over = 0
    ml_total = ml_acierto = 0
    detalle = []
    juegos = 0

    for d in range(1, dias + 1):
        fecha = (datetime.now() - timedelta(days=d)).strftime('%Y-%m-%d')
        sched = _get_json(f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={fecha}&hydrate=team")
        if not sched:
            continue
        finales = [g for dt in sched.get('dates', []) for g in dt.get('games', [])
                   if g.get('status', {}).get('abstractGameState') == 'Final']

        for g in finales:
            home = g['teams']['home']
            away = g['teams']['away']
            hs = home.get('score')
            as_ = away.get('score')
            if hs is None or as_ is None:
                continue
            pct_h = _pct(home.get('leagueRecord'))
            pct_a = _pct(away.get('leagueRecord'))
            juegos += 1
            if progreso_cb:
                progreso_cb(juegos, f"{fecha}: {away['team']['name']} @ {home['team']['name']}")

            # ── Moneyline: predecir el de mejor récord (+ ventaja de local) ──
            score_h = pct_h + 0.03  # ventaja de local
            pred_home = score_h >= pct_a
            gano_home = hs > as_
            acierto_ml = (pred_home and gano_home) or (not pred_home and not gano_home)
            gap = abs(pct_h - pct_a)
            tramo = "gap 15%+" if gap >= 0.15 else "gap 8-14%" if gap >= 0.08 else "gap <8%"
            ml_tramos[tramo]["juegos"] += 1
            ml_tramos[tramo]["aciertos"] += 1 if acierto_ml else 0
            ml_total += 1
            ml_acierto += 1 if acierto_ml else 0

            # ── Over/Under ──
            total = hs + as_
            ou_total += 1
            ou_over += 1 if total > LINEA_OU else 0

            detalle.append({
                "fecha": fecha,
                "juego": f"{away['team']['name']} @ {home['team']['name']}",
                "marcador": f"{as_}-{hs}", "total": total,
                "pred_ml": home['team']['name'] if pred_home else away['team']['name'],
                "ganador": home['team']['name'] if gano_home else away['team']['name'],
                "ml_ok": acierto_ml,
            })

    # Precisión ML por tramo
    resumen_ml = {}
    for tramo, dd in ml_tramos.items():
        if dd["juegos"] > 0:
            resumen_ml[tramo] = {"juegos": dd["juegos"], "aciertos": dd["aciertos"],
                                 "precision": round(dd["aciertos"] / dd["juegos"] * 100, 1)}

    tasa_over = round(ou_over / ou_total * 100, 1) if ou_total else 0

    reporte = {
        "timestamp": datetime.now().isoformat(),
        "dias": dias, "juegos": juegos,
        "moneyline": {
            "precision_global": round(ml_acierto / ml_total * 100, 1) if ml_total else 0,
            "por_tramo_record": resumen_ml,
        },
        "over_under": {
            "linea": LINEA_OU, "juegos": ou_total,
            "tasa_over": tasa_over, "tasa_under": round(100 - tasa_over, 1),
            "sesgo": "OVER" if tasa_over > 53 else "UNDER" if tasa_over < 47 else "EQUILIBRADO",
        },
        "detalle": detalle[:80],
    }

    os.makedirs("data", exist_ok=True)
    with open(REPORTE_PATH, 'w', encoding='utf-8') as f:
        json.dump(reporte, f, indent=2, ensure_ascii=False)

    # Calibración para el motor
    calib = {
        "actualizado": reporte["timestamp"], "juegos": juegos,
        "ml_precision_global": reporte["moneyline"]["precision_global"],
        "ml_precision_por_gap": resumen_ml,
        "ou_tasa_over": tasa_over,
    }
    with open(CALIB_PATH, 'w', encoding='utf-8') as f:
        json.dump(calib, f, indent=2, ensure_ascii=False)

    print(f"[MLB-backtest] {juegos} juegos | ML global {reporte['moneyline']['precision_global']}% "
          f"| O/U: {tasa_over}% OVER ({reporte['over_under']['sesgo']})")
    return reporte


if __name__ == "__main__":
    dias = int(sys.argv[1]) if len(sys.argv) > 1 else 15
    rep = ejecutar_mlb_backtest(dias=dias)
    print(json.dumps({k: v for k, v in rep.items() if k != 'detalle'}, indent=2, ensure_ascii=False))
