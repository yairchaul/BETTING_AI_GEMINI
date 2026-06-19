# -*- coding: utf-8 -*-
"""
SIMULADOR DE PARLAYS — mide cuánto mejora el programa con la estrategia NUEVA
(runline +1.5 al no favorito + moneyline favorito) vs la VIEJA (total bases /
mercados flojos), sobre juegos REALES 2026 y calificando cada leg.

Para cada día arma parlays de 2/3/4 legs y los califica (TODAS las legs deben
acertar). Reporta la tasa de acierto del parlay por tamaño y estrategia.

Estrategias comparadas:
  • NUEVA-A : visitante +1.5 (el mercado más fiable del backtest, 62.9%)
  • NUEVA-B : favorito ML (55.6%)
  • NUEVA-MIX: combina ambas (1 ML fav + resto visitante +1.5)
  • VIEJA  : TOTAL OVER 8.5 (proxy de los mercados flojos que se favorecían)

Uso:  python backtest_parlays_sim.py [dias] [legs]
"""
import os
import sys
import json
import requests
from datetime import datetime, timedelta
from collections import defaultdict

API = "https://statsapi.mlb.com/api/v1"
HEAD = {"User-Agent": "Mozilla/5.0"}
OUT = os.path.join("data", "parlays_sim_backtest.json")


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


def _juegos_dia(fecha):
    sched = _j(f"{API}/schedule?sportId=1&date={fecha}&hydrate=team")
    if not sched:
        return []
    out = []
    for dt in sched.get("dates", []):
        for g in dt.get("games", []):
            if g.get("status", {}).get("abstractGameState") != "Final":
                continue
            h, a = g["teams"]["home"], g["teams"]["away"]
            if h.get("score") is None or a.get("score") is None:
                continue
            out.append({
                "home": h["team"]["name"], "away": a["team"]["name"],
                "hs": h["score"], "as": a["score"],
                "pct_h": _pct(h.get("leagueRecord")), "pct_a": _pct(a.get("leagueRecord")),
            })
    return out


def _legs_del_dia(juegos):
    """Genera las legs candidatas por estrategia con su resultado (hit/fail)."""
    legs = {"NUEVA-A": [], "NUEVA-B": [], "VIEJA": [], "MEJOR-LEG": []}
    for g in juegos:
        margen = g["hs"] - g["as"]            # + gana local
        fav_es_home = (g["pct_h"] + 0.03) >= g["pct_a"]
        fav_margen = margen if fav_es_home else -margen
        total = g["hs"] + g["as"]
        gap = abs(g["pct_h"] - g["pct_a"])
        # NUEVA-A: visitante +1.5 (cubre si visita pierde por ≤1 o gana)
        ok_vis15 = margen <= 1
        legs["NUEVA-A"].append(("visitante +1.5", ok_vis15))
        # NUEVA-B: favorito ML
        ok_favml = fav_margen > 0
        legs["NUEVA-B"].append(("favorito ML", ok_favml))
        # VIEJA: total OVER 8.5
        legs["VIEJA"].append(("OVER 8.5", total > 8.5))
        # MEJOR-LEG: replica el selector (runline +1.5 al no favorito con filtro
        # de brecha vs moneyline favorito) y toma el de mayor confianza calibrada.
        dog_es_visitante = not fav_es_home  # el +1.5 va al no favorito; preferimos visitante
        rl_conf = 63 if dog_es_visitante else 58
        if gap >= 0.20:
            rl_conf -= 8
        elif gap >= 0.12:
            rl_conf -= 4
        ml_conf = 50 + gap * 80          # favorito ML sube con la brecha
        if rl_conf >= ml_conf:
            # +1.5 al no favorito (si fav es local, el dog es visitante → ok_vis15)
            ok = (margen <= 1) if dog_es_visitante else (fav_margen >= -1)
            legs["MEJOR-LEG"].append((f"+1.5 no-fav (rl {rl_conf})", ok))
        else:
            legs["MEJOR-LEG"].append((f"favorito ML (ml {ml_conf:.0f})", ok_favml))
    return legs


def _tasa_parlay(legs_hits, n_legs):
    """Arma parlays consecutivos de n_legs y mide cuántos ganan (todas aciertan)."""
    parlays = 0
    ganados = 0
    for i in range(0, len(legs_hits) - n_legs + 1, n_legs):
        grupo = legs_hits[i:i + n_legs]
        if len(grupo) < n_legs:
            break
        parlays += 1
        if all(ok for _, ok in grupo):
            ganados += 1
    return ganados, parlays


def ejecutar(dias=20, max_legs=4, progreso_cb=None):
    por_estrategia = {e: defaultdict(lambda: [0, 0]) for e in
                      ("NUEVA-A", "NUEVA-B", "NUEVA-MIX", "MEJOR-LEG", "VIEJA")}
    leg_winrate = defaultdict(lambda: [0, 0])
    dias_con_juegos = 0

    for d in range(1, int(dias) + 1):
        fecha = (datetime.now() - timedelta(days=d)).strftime("%Y-%m-%d")
        juegos = _juegos_dia(fecha)
        if len(juegos) < 2:
            continue
        dias_con_juegos += 1
        if progreso_cb:
            progreso_cb(fecha, len(juegos))
        legs = _legs_del_dia(juegos)

        # tasa por leg individual
        for e in ("NUEVA-A", "NUEVA-B", "VIEJA", "MEJOR-LEG"):
            for _, ok in legs[e]:
                leg_winrate[e][1] += 1
                leg_winrate[e][0] += 1 if ok else 0

        # MIX: 1 favorito ML + resto visitante +1.5
        mix = legs["NUEVA-B"][:1] + legs["NUEVA-A"][1:]

        for n in range(2, int(max_legs) + 1):
            for e, base in (("NUEVA-A", legs["NUEVA-A"]), ("NUEVA-B", legs["NUEVA-B"]),
                            ("NUEVA-MIX", mix), ("MEJOR-LEG", legs["MEJOR-LEG"]),
                            ("VIEJA", legs["VIEJA"])):
                gan, tot = _tasa_parlay(base, n)
                por_estrategia[e][n][0] += gan
                por_estrategia[e][n][1] += tot

    rep = {
        "timestamp": datetime.now().isoformat(), "dias": int(dias),
        "dias_con_juegos": dias_con_juegos,
        "leg_winrate": {e: {"hit": v[0], "n": v[1],
                            "win_rate": round(v[0] / v[1] * 100, 1) if v[1] else 0}
                        for e, v in leg_winrate.items()},
        "parlay_winrate": {
            e: {str(n): {"ganados": v[0], "parlays": v[1],
                         "win_rate": round(v[0] / v[1] * 100, 1) if v[1] else 0}
                for n, v in sorted(d.items())}
            for e, d in por_estrategia.items()},
    }
    os.makedirs("data", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=2)
    return rep


def _imprimir(r):
    print("=" * 74)
    print(f"SIMULADOR DE PARLAYS — {r['dias_con_juegos']} días con juegos reales (2026)")
    print("=" * 74)
    print("Tasa por leg individual:")
    nombres = {"NUEVA-A": "visitante +1.5", "NUEVA-B": "favorito ML",
               "MEJOR-LEG": "MEJOR leg/juego", "VIEJA": "OVER 8.5 (viejo)"}
    for e, v in r["leg_winrate"].items():
        print(f"  {nombres.get(e,e):<22} {v['hit']}/{v['n']} = {v['win_rate']}%")
    print("-" * 74)
    print("Tasa de ACIERTO del PARLAY (todas las legs aciertan) por tamaño:")
    etiquetas = {"NUEVA-A": "NUEVA visitante+1.5", "NUEVA-B": "NUEVA favorito ML",
                 "NUEVA-MIX": "NUEVA mix", "MEJOR-LEG": "MEJOR leg/juego (selector)",
                 "VIEJA": "VIEJA over 8.5"}
    for e in ("MEJOR-LEG", "NUEVA-A", "NUEVA-MIX", "NUEVA-B", "VIEJA"):
        d = r["parlay_winrate"][e]
        linea = "  ".join(f"{n}legs={v['win_rate']}%({v['ganados']}/{v['parlays']})"
                          for n, v in d.items())
        print(f"  {etiquetas[e]:<26} {linea}")
    print("=" * 74)


if __name__ == "__main__":
    dias = sys.argv[1] if len(sys.argv) > 1 else 20
    legs = sys.argv[2] if len(sys.argv) > 2 else 4
    rep = ejecutar(dias=dias, max_legs=legs, progreso_cb=lambda f, n: print("  ", f, f"({n} juegos)"))
    _imprimir(rep)
