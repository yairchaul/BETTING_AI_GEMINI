# -*- coding: utf-8 -*-
"""
BACKTEST DE RUNLINE (hándicap MLB) con datos REALES 2026 (statsapi).

Mide, sobre juegos finalizados de los últimos N días, la tasa de acierto de:
  • Favorito -1.5  (el favorito gana por 2+)        → paga más, riesgo medio
  • Perdedor +1.5  (el menos favorito pierde por ≤1 o gana)  → tu intuición "da la vuelta"
  • Local -1.5 / Visitante +1.5  (referencia)
  • Favorito ML recto (gana) y Perdedor ML (upset)

"Favorito" se define por el mejor récord AL MOMENTO del juego (leagueRecord),
que es el dato histórico que da statsapi sin necesidad de cuotas de cierre.

Uso:  python backtest_runline.py [dias]
"""
import os
import sys
import json
import requests
from datetime import datetime, timedelta
from collections import defaultdict

API = "https://statsapi.mlb.com/api/v1"
HEAD = {"User-Agent": "Mozilla/5.0"}
OUT = os.path.join("data", "runline_backtest.json")


def _j(url):
    try:
        r = requests.get(url, headers=HEAD, timeout=12)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def _pct(rec):
    try:
        return float(rec.get("pct", 0.5)) if rec else 0.5
    except Exception:
        return 0.5


def ejecutar(dias=20, progreso_cb=None):
    M = lambda: {"n": 0, "hit": 0}
    fav_ml, fav_15, dog_ml, dog_15 = M(), M(), M(), M()
    home_15, away_15 = M(), M()
    # Desglose por brecha de récord
    por_gap = defaultdict(lambda: {"fav_ml": M(), "fav_15": M(), "dog_15": M()})
    juegos = 0
    detalle = []

    for d in range(1, int(dias) + 1):
        fecha = (datetime.now() - timedelta(days=d)).strftime("%Y-%m-%d")
        sched = _j(f"{API}/schedule?sportId=1&date={fecha}&hydrate=team")
        if not sched:
            continue
        finales = [g for dt in sched.get("dates", []) for g in dt.get("games", [])
                   if g.get("status", {}).get("abstractGameState") == "Final"]
        for g in finales:
            h, a = g["teams"]["home"], g["teams"]["away"]
            hs, as_ = h.get("score"), a.get("score")
            if hs is None or as_ is None:
                continue
            pct_h, pct_a = _pct(h.get("leagueRecord")), _pct(a.get("leagueRecord"))
            juegos += 1
            if progreso_cb and juegos % 25 == 0:
                progreso_cb(juegos, fecha)

            margen = hs - as_                      # + => gana local
            gap = abs(pct_h - pct_a)
            tramo = "gap 15%+" if gap >= 0.15 else "gap 8-14%" if gap >= 0.08 else "gap <8%"
            # Favorito por récord (+ ventaja local leve)
            fav_es_home = (pct_h + 0.03) >= pct_a
            fav_margen = margen if fav_es_home else -margen   # + => ganó el favorito

            def _add(m, ok):
                m["n"] += 1; m["hit"] += 1 if ok else 0

            _add(fav_ml, fav_margen > 0)
            _add(fav_15, fav_margen >= 2)          # favorito -1.5 cubre si gana por 2+
            _add(dog_ml, fav_margen < 0)           # upset (gana el no favorito)
            _add(dog_15, fav_margen <= 1)          # perdedor +1.5 cubre si pierde por ≤1 o gana
            _add(home_15, margen >= 2)
            _add(away_15, margen <= 1)
            _add(por_gap[tramo]["fav_ml"], fav_margen > 0)
            _add(por_gap[tramo]["fav_15"], fav_margen >= 2)
            _add(por_gap[tramo]["dog_15"], fav_margen <= 1)

            detalle.append({"fecha": fecha,
                            "juego": f"{a['team']['name']} @ {h['team']['name']}",
                            "marcador": f"{as_}-{hs}", "margen_fav": fav_margen,
                            "gap": tramo})

    def _wr(m):
        return round(m["hit"] / m["n"] * 100, 1) if m["n"] else 0.0

    rep = {
        "timestamp": datetime.now().isoformat(), "dias": int(dias), "juegos": juegos,
        "mercados": {
            "favorito_ML": {**fav_ml, "win_rate": _wr(fav_ml)},
            "favorito_-1.5": {**fav_15, "win_rate": _wr(fav_15)},
            "perdedor_ML(upset)": {**dog_ml, "win_rate": _wr(dog_ml)},
            "perdedor_+1.5": {**dog_15, "win_rate": _wr(dog_15)},
            "local_-1.5": {**home_15, "win_rate": _wr(home_15)},
            "visitante_+1.5": {**away_15, "win_rate": _wr(away_15)},
        },
        "por_gap": {k: {kk: {**vv, "win_rate": _wr(vv)} for kk, vv in v.items()}
                    for k, v in por_gap.items()},
        "detalle": detalle[-120:],
    }
    os.makedirs("data", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=2)
    return rep


def _imprimir(r):
    print("=" * 72)
    print(f"BACKTEST RUNLINE — {r['juegos']} juegos reales · {r['dias']} días (2026)")
    print("=" * 72)
    for nombre, m in r["mercados"].items():
        print(f"  {nombre:<22} {m['hit']:>3}/{m['n']:<3} = {m['win_rate']}%")
    print("-" * 72)
    print("  Por brecha de récord (fav ML / fav -1.5 / perdedor +1.5):")
    for tramo, d in r["por_gap"].items():
        print(f"    {tramo:<10} ML {d['fav_ml']['win_rate']}%  "
              f"-1.5 {d['fav_15']['win_rate']}%  dog+1.5 {d['dog_15']['win_rate']}%  "
              f"(n={d['fav_ml']['n']})")
    print("=" * 72)


if __name__ == "__main__":
    dias = sys.argv[1] if len(sys.argv) > 1 else 20
    rep = ejecutar(dias=dias, progreso_cb=lambda i, f: print("  ", i, f))
    _imprimir(rep)
