# -*- coding: utf-8 -*-
"""
MLB BACKTEST REAL — Corre el MOTOR completo sobre cada juego histórico.

A diferencia de un proxy, reconstruye cada juego de los últimos N días con los
datos que existían ESE día (récords del momento, pitchers probables, estadio) y
ejecuta `analizar_mlb_pro_v20` EXACTAMENTE como lo haría la app. Luego compara
contra el resultado real (marcador + HR del boxscore):

  • Moneyline: ¿el pick del motor ganó?
  • Over/Under: ¿acertó OVER/UNDER vs el total real?
  • Home Runs: de los candidatos del motor, ¿cuáles conectaron?

Escribe data/mlb_backtest_real.json
Uso:  python -m motors.mlb_backtest_real [dias]
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

from motors import analizar_mlb_pro_v20

HEADERS = {'User-Agent': 'Mozilla/5.0'}
REPORTE_PATH = os.path.join("data", "mlb_backtest_real.json")


def _norm(n):
    t = unicodedata.normalize('NFD', n or '').encode('ascii', 'ignore').decode('utf-8')
    return t.strip().lower()


def _get_json(url, timeout=12):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def _resultado_real(game_pk):
    """Marcador final + set de bateadores que pegaron HR (boxscore oficial)."""
    box = _get_json(f"https://statsapi.mlb.com/api/v1/game/{game_pk}/boxscore")
    hr = set()
    if not box:
        return hr
    for lado in ('home', 'away'):
        for _pid, pdata in box.get('teams', {}).get(lado, {}).get('players', {}).items():
            if pdata.get('stats', {}).get('batting', {}).get('homeRuns', 0):
                hr.add(_norm(pdata.get('person', {}).get('fullName', '')))
    return hr


def _reconstruir_partido(g):
    """Arma el dict de partido con los datos que existían ese día."""
    home = g['teams']['home']
    away = g['teams']['away']
    rh = home.get('leagueRecord', {})
    ra = away.get('leagueRecord', {})
    return {
        'local': home['team']['name'],
        'visitante': away['team']['name'],
        'local_record': f"{rh.get('wins', 0)}-{rh.get('losses', 0)}",
        'visitante_record': f"{ra.get('wins', 0)}-{ra.get('losses', 0)}",
        'venue': g.get('venue', {}).get('name', ''),
        'game_pk': g.get('gamePk'),
        'pitchers': {
            'local': {'nombre': home.get('probablePitcher', {}).get('fullName', 'TBD')},
            'visitante': {'nombre': away.get('probablePitcher', {}).get('fullName', 'TBD')},
        },
        'odds': {'over_under': 8.5},  # línea estándar (sin momios históricos)
        '_score_home': home.get('score'),
        '_score_away': away.get('score'),
    }


def ejecutar_backtest_real(dias=15, progreso_cb=None):
    """Corre el motor real sobre cada juego de los últimos N días."""
    ml_total = ml_ok = 0
    ml_por_conf = defaultdict(lambda: {"n": 0, "ok": 0})
    ou_total = ou_ok = 0
    rl_total = rl_ok = 0
    hr_pred = hr_ok = 0
    hr_por_tramo = defaultdict(lambda: {"pred": 0, "ok": 0})
    detalle = []
    juegos = 0

    for d in range(1, dias + 1):
        fecha = (datetime.now() - timedelta(days=d)).strftime('%Y-%m-%d')
        sched = _get_json(f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={fecha}"
                          "&hydrate=team,probablePitcher")
        if not sched:
            continue
        finales = [g for dt in sched.get('dates', []) for g in dt.get('games', [])
                   if g.get('status', {}).get('abstractGameState') == 'Final']

        for g in finales:
            partido = _reconstruir_partido(g)
            sh, sa = partido.pop('_score_home'), partido.pop('_score_away')
            if sh is None or sa is None:
                continue
            juegos += 1
            if progreso_cb:
                progreso_cb(juegos, f"{fecha}: {partido['visitante']} @ {partido['local']}")

            # ── Correr el MOTOR REAL ──
            try:
                pred = analizar_mlb_pro_v20(partido, game_pk=partido['game_pk'])
            except Exception:
                continue

            gano_local = sh > sa
            ganador_real = partido['local'] if gano_local else partido['visitante']
            total_real = sh + sa
            hr_reales = _resultado_real(partido['game_pk'])

            # Moneyline del motor
            pick_ml = pred.get('pick', '')
            ml_acierto = pick_ml == ganador_real
            ml_total += 1
            ml_ok += 1 if ml_acierto else 0
            conf = pred.get('confianza', 50)
            tramo_c = "70%+" if conf >= 70 else "60-69%" if conf >= 60 else "55-59%" if conf >= 55 else "<55%"
            ml_por_conf[tramo_c]["n"] += 1
            ml_por_conf[tramo_c]["ok"] += 1 if ml_acierto else 0

            # Over/Under del motor
            ou_pick = pred.get('ou_pick')
            ou_acierto = None
            if ou_pick:
                linea = pred.get('ou_linea_ajustada', 8.5)
                real_over = total_real > linea
                ou_acierto = (ou_pick == "OVER" and real_over) or (ou_pick == "UNDER" and not real_over)
                ou_total += 1
                ou_ok += 1 if ou_acierto else 0

            # Run Line (hándicap ±1.5) del motor
            rl = pred.get('run_line', {})
            rl_acierto = None
            if rl and rl.get('pick'):
                rl_pick = rl['pick']
                es_favorito = str(rl.get('linea', '-1.5')).strip().startswith('-')
                margen = abs(sh - sa)
                pick_gano = (rl_pick == ganador_real)
                if es_favorito:
                    # -1.5: cubre si su equipo gana por 2+
                    rl_acierto = pick_gano and margen >= 2
                else:
                    # +1.5: cubre si gana o pierde por 1
                    rl_acierto = pick_gano or margen <= 1
                rl_total += 1
                rl_ok += 1 if rl_acierto else 0

            # HR candidatos del motor
            hits_juego = 0
            for c in pred.get('hr_candidates', [])[:6]:
                pegó = _norm(c.get('jugador', '')) in hr_reales
                prob = c.get('probabilidad', 0)
                tramo = "15%+" if prob >= 15 else "12-14%" if prob >= 12 else "9-11%" if prob >= 9 else "<9%"
                hr_por_tramo[tramo]["pred"] += 1
                hr_por_tramo[tramo]["ok"] += 1 if pegó else 0
                hr_pred += 1
                hr_ok += 1 if pegó else 0
                hits_juego += 1 if pegó else 0

            detalle.append({
                "fecha": fecha, "juego": f"{partido['visitante']} @ {partido['local']}",
                "marcador": f"{sa}-{sh}",
                "ml_pick": pick_ml, "ml_conf": conf, "ml_ok": ml_acierto,
                "ou_pick": f"{ou_pick} {pred.get('ou_linea_ajustada','')}" if ou_pick else "—",
                "ou_ok": ou_acierto, "total_real": total_real,
                "rl_pick": f"{rl.get('pick','')} {rl.get('linea','')}".strip() if rl else "—",
                "rl_ok": rl_acierto,
                "hr_aciertos": hits_juego,
            })
            time.sleep(0.12)

    def _prec(d):
        return {k: {**v, "precision": round(v["ok"] / v["n"] * 100, 1) if v.get("n") else
                    round(v["ok"] / v["pred"] * 100, 1) if v.get("pred") else 0}
                for k, v in d.items() if (v.get("n") or v.get("pred"))}

    reporte = {
        "timestamp": datetime.now().isoformat(), "dias": dias, "juegos": juegos,
        "moneyline": {
            "precision_global": round(ml_ok / ml_total * 100, 1) if ml_total else 0,
            "aciertos": ml_ok, "total": ml_total,
            "por_confianza_motor": _prec(ml_por_conf),
        },
        "over_under": {
            "precision": round(ou_ok / ou_total * 100, 1) if ou_total else 0,
            "aciertos": ou_ok, "total": ou_total,
        },
        "run_line": {
            "precision": round(rl_ok / rl_total * 100, 1) if rl_total else 0,
            "aciertos": rl_ok, "total": rl_total,
        },
        "home_runs": {
            "precision_global": round(hr_ok / hr_pred * 100, 1) if hr_pred else 0,
            "aciertos": hr_ok, "predichos": hr_pred,
            "por_tramo": _prec(hr_por_tramo),
        },
        "detalle": detalle[:100],
    }

    os.makedirs("data", exist_ok=True)
    with open(REPORTE_PATH, 'w', encoding='utf-8') as f:
        json.dump(reporte, f, indent=2, ensure_ascii=False)

    print(f"[backtest-real] {juegos} juegos | ML {reporte['moneyline']['precision_global']}% "
          f"| O/U {reporte['over_under']['precision']}% | HR {reporte['home_runs']['precision_global']}%")
    return reporte


if __name__ == "__main__":
    dias = int(sys.argv[1]) if len(sys.argv) > 1 else 15
    rep = ejecutar_backtest_real(dias=dias)
    print(json.dumps({k: v for k, v in rep.items() if k != 'detalle'}, indent=2, ensure_ascii=False))
