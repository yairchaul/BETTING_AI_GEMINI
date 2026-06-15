# -*- coding: utf-8 -*-
"""
NBA BACKTEST REAL — Corre el motor NBA sobre cada juego histórico.

Reconstruye cada juego de los últimos N días desde ESPN (récords + marcador) y
ejecuta `analizar_nba_pro_v17` igual que la app, comparando contra el resultado:
  • Moneyline: ¿el pick ganó?
  • Over/Under: ¿acertó vs el total de puntos real?
  • Hándicap: ¿el favorito cubrió?

Escribe data/nba_backtest_real.json
Uso:  python -m motors.nba_backtest_real [dias]
"""

import os
import sys
import json
import time
import requests
from datetime import datetime, timedelta
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motors import analizar_nba_pro_v17

HEADERS = {'User-Agent': 'Mozilla/5.0'}
REPORTE_PATH = os.path.join("data", "nba_backtest_real.json")


def _get_json(url, timeout=12):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def _record(competitor):
    for rr in competitor.get('records', []) or []:
        if rr.get('type') == 'total':
            return rr.get('summary', '0-0')
    return '0-0'


def ejecutar_nba_backtest_real(dias=15, progreso_cb=None):
    ml_total = ml_ok = 0
    ml_por_conf = defaultdict(lambda: {"n": 0, "ok": 0})
    ou_total = ou_ok = 0
    hcap_total = hcap_ok = 0
    detalle = []
    juegos = 0

    for d in range(1, dias + 1):
        fecha = (datetime.now() - timedelta(days=d)).strftime('%Y%m%d')
        data = _get_json(f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={fecha}")
        if not data:
            continue
        finales = [e for e in data.get('events', [])
                   if e['competitions'][0].get('status', {}).get('type', {}).get('completed')]

        for e in finales:
            c = e['competitions'][0]
            try:
                home = next(x for x in c['competitors'] if x['homeAway'] == 'home')
                away = next(x for x in c['competitors'] if x['homeAway'] == 'away')
            except StopIteration:
                continue
            try:
                sh, sa = int(home.get('score', 0)), int(away.get('score', 0))
            except (TypeError, ValueError):
                continue
            if sh == 0 and sa == 0:
                continue
            juegos += 1
            if progreso_cb:
                progreso_cb(juegos, f"{away['team']['displayName']} @ {home['team']['displayName']}")

            partido = {
                'local': home['team']['displayName'],
                'visitante': away['team']['displayName'],
                'local_record': _record(home),
                'visitante_record': _record(away),
                'odds': {'over_under': 225.5},
            }
            try:
                pred = analizar_nba_pro_v17(partido)
            except Exception:
                continue

            gano_local = sh > sa
            ganador = partido['local'] if gano_local else partido['visitante']
            total_real = sh + sa
            margen = abs(sh - sa)

            # Moneyline
            pick_ml = pred.get('moneyline', {}).get('pick', pred.get('recomendacion', '').replace('Gana ', ''))
            ml_acierto = pick_ml in ganador or ganador in str(pick_ml)
            conf = pred.get('confianza', 50)
            tramo = "65%+" if conf >= 65 else "58-64%" if conf >= 58 else "<58%"
            ml_por_conf[tramo]["n"] += 1
            ml_por_conf[tramo]["ok"] += 1 if ml_acierto else 0
            ml_total += 1
            ml_ok += 1 if ml_acierto else 0

            # Over/Under (línea estándar 225.5)
            ou = pred.get('over_under', {})
            if ou.get('pick'):
                linea = ou.get('line', 225.5)
                real_over = total_real > linea
                ou_acierto = (ou['pick'] == "OVER" and real_over) or (ou['pick'] == "UNDER" and not real_over)
                ou_total += 1
                ou_ok += 1 if ou_acierto else 0

            # Hándicap: el favorito cubrió -5.5 (aprox)
            spread = pred.get('spread', {})
            if spread.get('pick'):
                favorito_gano_x = gano_local and (pred.get('moneyline', {}).get('pick') == partido['local'])
                cubrio = margen >= 6 and ml_acierto
                hcap_total += 1
                hcap_ok += 1 if cubrio else 0

            detalle.append({
                "fecha": fecha, "juego": f"{partido['visitante']} @ {partido['local']}",
                "marcador": f"{sa}-{sh}", "ml_pick": pick_ml, "ml_conf": conf,
                "ml_ok": ml_acierto, "total_real": total_real,
            })
            time.sleep(0.1)

    def _prec(dd):
        return {k: {**v, "precision": round(v["ok"] / v["n"] * 100, 1) if v.get("n") else 0}
                for k, v in dd.items() if v.get("n")}

    reporte = {
        "timestamp": datetime.now().isoformat(), "dias": dias, "juegos": juegos,
        "moneyline": {"precision_global": round(ml_ok / ml_total * 100, 1) if ml_total else 0,
                      "aciertos": ml_ok, "total": ml_total, "por_confianza_motor": _prec(ml_por_conf)},
        "over_under": {"precision": round(ou_ok / ou_total * 100, 1) if ou_total else 0,
                       "aciertos": ou_ok, "total": ou_total},
        "handicap": {"precision": round(hcap_ok / hcap_total * 100, 1) if hcap_total else 0,
                     "aciertos": hcap_ok, "total": hcap_total},
        "detalle": detalle[:100],
    }

    os.makedirs("data", exist_ok=True)
    with open(REPORTE_PATH, 'w', encoding='utf-8') as f:
        json.dump(reporte, f, indent=2, ensure_ascii=False)

    print(f"[NBA-backtest-real] {juegos} juegos | ML {reporte['moneyline']['precision_global']}% "
          f"| O/U {reporte['over_under']['precision']}% | Hcap {reporte['handicap']['precision']}%")
    return reporte


if __name__ == "__main__":
    dias = int(sys.argv[1]) if len(sys.argv) > 1 else 15
    rep = ejecutar_nba_backtest_real(dias=dias)
    print(json.dumps({k: v for k, v in rep.items() if k != 'detalle'}, indent=2, ensure_ascii=False))
