# -*- coding: utf-8 -*-
"""
HR BACKTESTER — Valida las predicciones de Home Run contra resultados reales.

Para los últimos N días:
  1. Baja los juegos finalizados (MLB Stats API)
  2. Para cada juego, genera los candidatos a HR del motor (mismo dataset)
  3. Baja del boxscore quién pegó HR realmente
  4. Cruza: de los candidatos predichos, ¿cuáles conectaron?

Reporta la tasa de acierto por nivel de probabilidad → permite pulir el motor.
Escribe data/hr_backtest_reporte.json.

Uso:  python -m motors.hr_backtester [dias]
"""

import os
import sys
import json
import time
import unicodedata
import requests
from datetime import datetime, timedelta
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motors.motor_mlb_pro import _candidatos_hr_equipo

HEADERS = {'User-Agent': 'Mozilla/5.0'}
REPORTE_PATH = os.path.join("data", "hr_backtest_reporte.json")


def _norm(nombre):
    t = unicodedata.normalize('NFD', nombre or '').encode('ascii', 'ignore').decode('utf-8')
    return t.strip().lower()


def _get_json(url, timeout=12):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def _hr_reales_del_juego(game_pk):
    """Set de nombres normalizados que pegaron HR en el juego."""
    box = _get_json(f"https://statsapi.mlb.com/api/v1/game/{game_pk}/boxscore")
    bateadores_hr = set()
    if not box:
        return bateadores_hr
    for lado in ('home', 'away'):
        players = box.get('teams', {}).get(lado, {}).get('players', {})
        for _pid, pdata in players.items():
            hr = pdata.get('stats', {}).get('batting', {}).get('homeRuns', 0)
            if hr and hr > 0:
                bateadores_hr.add(_norm(pdata.get('person', {}).get('fullName', '')))
    return bateadores_hr


def ejecutar_hr_backtest(dias=15, top_n=5, progreso_cb=None):
    """Cruza candidatos a HR predichos vs HR reales en los últimos N días."""
    detalle = []
    # Acierto agrupado por tramo de probabilidad
    tramos = defaultdict(lambda: {"predichos": 0, "aciertos": 0})
    total_pred = total_acierto = 0

    juegos_procesados = 0
    for d in range(1, dias + 1):
        fecha = (datetime.now() - timedelta(days=d)).strftime('%Y-%m-%d')
        sched = _get_json(f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={fecha}&hydrate=team")
        if not sched:
            continue
        juegos = [g for dt in sched.get('dates', []) for g in dt.get('games', [])
                  if g.get('status', {}).get('abstractGameState') == 'Final']

        for g in juegos:
            gpk = g.get('gamePk')
            home = g['teams']['home']['team']['name']
            away = g['teams']['away']['team']['name']
            venue = g.get('venue', {}).get('name', '')
            if progreso_cb:
                progreso_cb(juegos_procesados, f"{fecha}: {away} @ {home}")

            # Candidatos predichos (top_n por equipo) con el mismo motor
            candidatos = (_candidatos_hr_equipo(home, '', venue) +
                          _candidatos_hr_equipo(away, '', venue))
            candidatos = sorted(candidatos, key=lambda x: x['probabilidad'], reverse=True)[:top_n * 2]
            if not candidatos:
                continue

            hr_reales = _hr_reales_del_juego(gpk)
            juegos_procesados += 1

            for c in candidatos:
                pegó = _norm(c['jugador']) in hr_reales
                prob = c['probabilidad']
                tramo = "15%+" if prob >= 15 else "12-14%" if prob >= 12 else "9-11%" if prob >= 9 else "<9%"
                tramos[tramo]["predichos"] += 1
                tramos[tramo]["aciertos"] += 1 if pegó else 0
                total_pred += 1
                total_acierto += 1 if pegó else 0
                detalle.append({
                    "fecha": fecha, "jugador": c['jugador'], "equipo": c['equipo'],
                    "probabilidad": prob, "pegó_hr": pegó,
                })
            time.sleep(0.12)

    # Calcular precisión por tramo
    resumen_tramos = {}
    for tramo, d in tramos.items():
        if d["predichos"] > 0:
            resumen_tramos[tramo] = {
                "predichos": d["predichos"], "aciertos": d["aciertos"],
                "precision": round(d["aciertos"] / d["predichos"] * 100, 1),
            }

    reporte = {
        "timestamp": datetime.now().isoformat(),
        "dias": dias, "juegos": juegos_procesados,
        "total_predichos": total_pred, "total_aciertos": total_acierto,
        "precision_global": round(total_acierto / total_pred * 100, 1) if total_pred else 0,
        "por_tramo_probabilidad": resumen_tramos,
        "detalle": sorted(detalle, key=lambda x: (x['pegó_hr'], x['probabilidad']), reverse=True)[:80],
    }

    os.makedirs("data", exist_ok=True)
    with open(REPORTE_PATH, 'w', encoding='utf-8') as f:
        json.dump(reporte, f, indent=2, ensure_ascii=False)

    print(f"[HR-backtest] {juegos_procesados} juegos | precisión global {reporte['precision_global']}% "
          f"| por tramo: {resumen_tramos}")
    return reporte


if __name__ == "__main__":
    dias = int(sys.argv[1]) if len(sys.argv) > 1 else 15
    rep = ejecutar_hr_backtest(dias=dias)
    print(json.dumps({k: v for k, v in rep.items() if k != 'detalle'}, indent=2, ensure_ascii=False))
