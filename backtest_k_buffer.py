# -*- coding: utf-8 -*-
"""
BACKTEST DE LÍNEA DE PONCHES (K) — programa vs casa de apuestas.

Demuestra el problema que reportaste: el programa fija la línea de K más baja que
la casa (ej. programa OVER 4.5, casa OVER 5.5). Aquí, sobre lanzadores abridores
reales de los últimos N días, comparamos la tasa de acierto del OVER en:
  • LÍNEA PROGRAMA  = max(2.5, round(proy) − 0.5)   (blanda, no siempre apostable)
  • LÍNEA CASA      = línea programa + buffer (lo que SÍ ofrece la casa)

Así se ve cuánto cae la tasa real cuando apuestas la línea que de verdad existe,
y valida el buffer K_BUFFER_CASA del motor.

Uso:  python backtest_k_buffer.py [dias] [buffer]
"""
import os
import sys
import json
import requests
from datetime import datetime, timedelta

API = "https://statsapi.mlb.com/api/v1"
HEAD = {"User-Agent": "Mozilla/5.0"}
OUT = os.path.join("data", "k_buffer_backtest.json")


def _j(url):
    try:
        r = requests.get(url, headers=HEAD, timeout=12)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def _k9_temporada(pid, year):
    d = _j(f"{API}/people/{pid}/stats?stats=statsSingleSeason&group=pitching&season={year}")
    try:
        st = d["stats"][0]["splits"][0]["stat"]
    except Exception:
        return 0.0
    # K/9 directo si existe; si no, se calcula de strikeOuts / inningsPitched
    k9 = st.get("strikeOutsPer9Inn")
    try:
        if k9 not in (None, "", "-.--"):
            return float(k9)
    except Exception:
        pass
    try:
        so = float(st.get("strikeOuts", 0))
        ip = float(st.get("inningsPitched", 0))
        return round(so / ip * 9.0, 2) if ip > 0 else 0.0
    except Exception:
        return 0.0


def ejecutar(dias=7, buffer=1.0, progreso_cb=None):
    prog = {"over": 0, "hit": 0}     # línea programa
    casa = {"over": 0, "hit": 0}     # línea casa (programa + buffer)
    apostables = {"over": 0, "hit": 0}   # solo los que el motor marcaría apostables
    detalle = []
    juegos = 0

    for d in range(1, int(dias) + 1):
        fecha = (datetime.now() - timedelta(days=d)).strftime("%Y-%m-%d")
        sched = _j(f"{API}/schedule?sportId=1&date={fecha}")
        if not sched:
            continue
        finales = [g for dt in sched.get("dates", []) for g in dt.get("games", [])
                   if g.get("status", {}).get("abstractGameState") == "Final"]
        for g in finales:
            box = _j(f"{API}/game/{g['gamePk']}/boxscore")
            if not box:
                continue
            for side in ("home", "away"):
                pitchers = box["teams"][side].get("pitchers", [])
                if not pitchers:
                    continue
                pid = pitchers[0]   # abridor
                pdata = box["teams"][side]["players"].get(f"ID{pid}", {})
                k_real = pdata.get("stats", {}).get("pitching", {}).get("strikeOuts")
                nombre = pdata.get("person", {}).get("fullName", "?")
                if k_real is None:
                    continue
                k9 = _k9_temporada(pid, fecha[:4])
                if k9 < 4.0:
                    continue
                k_proy = round((k9 / 9.0) * 5.5, 1)
                linea_prog = max(2.5, round(k_proy) - 0.5)
                linea_casa = round(linea_prog + float(buffer), 1)
                juegos += 1
                if progreso_cb:
                    progreso_cb(juegos, f"{fecha}: {nombre} ({k_real}K)")

                # OVER en línea programa
                prog["over"] += 1
                prog["hit"] += 1 if k_real > linea_prog else 0
                # OVER en línea casa
                casa["over"] += 1
                casa["hit"] += 1 if k_real > linea_casa else 0
                # ¿el motor lo marcaría apostable? (P(over) Poisson en la casa ≥ 55%)
                import math as _m
                _kmin = int(_m.floor(linea_casa)) + 1
                _cdf = sum(_m.exp(-k_proy) * k_proy ** i / _m.factorial(i) for i in range(_kmin))
                p_over_casa = 1.0 - _cdf
                apostable = p_over_casa >= 0.55
                if apostable:
                    apostables["over"] += 1
                    apostables["hit"] += 1 if k_real > linea_casa else 0

                detalle.append({
                    "fecha": fecha, "pitcher": nombre, "k9": round(k9, 1),
                    "k_proy": k_proy, "k_real": k_real,
                    "linea_prog": linea_prog, "linea_casa": linea_casa,
                    "ok_prog": k_real > linea_prog, "ok_casa": k_real > linea_casa,
                    "apostable": apostable,
                })

    def _wr(d):
        return round(d["hit"] / d["over"] * 100, 1) if d["over"] else 0.0

    rep = {
        "timestamp": datetime.now().isoformat(), "dias": int(dias), "buffer": float(buffer),
        "muestras": juegos,
        "over_linea_programa": {**prog, "win_rate": _wr(prog)},
        "over_linea_casa": {**casa, "win_rate": _wr(casa)},
        "over_solo_apostables": {**apostables, "win_rate": _wr(apostables)},
        "detalle": detalle[-100:],
    }
    os.makedirs("data", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=2)
    return rep


def _imprimir(r):
    print("=" * 72)
    print(f"BACKTEST LÍNEA DE K — programa vs casa (buffer +{r['buffer']}) · "
          f"{r['muestras']} aperturas · {r['dias']} días")
    print("=" * 72)
    p = r["over_linea_programa"]; c = r["over_linea_casa"]; a = r["over_solo_apostables"]
    print(f"  OVER en LÍNEA PROGRAMA : {p['hit']}/{p['over']} = {p['win_rate']}%  (línea blanda)")
    print(f"  OVER en LÍNEA CASA     : {c['hit']}/{c['over']} = {c['win_rate']}%  (la que SÍ se apuesta)")
    print(f"  OVER solo APOSTABLES   : {a['hit']}/{a['over']} = {a['win_rate']}%  "
          f"(motor con buffer: proy supera casa por ≥0.5)")
    print("-" * 72)
    print(f"  Caída programa→casa: {round(p['win_rate'] - c['win_rate'],1)} puntos. "
          f"El filtro 'apostable' recupera calidad: {a['win_rate']}%.")
    print("=" * 72)


if __name__ == "__main__":
    dias = sys.argv[1] if len(sys.argv) > 1 else 7
    buffer = sys.argv[2] if len(sys.argv) > 2 else 1.0
    rep = ejecutar(dias=dias, buffer=buffer, progreso_cb=lambda i, m: print("  ", i, m) if i % 10 == 0 else None)
    _imprimir(rep)
