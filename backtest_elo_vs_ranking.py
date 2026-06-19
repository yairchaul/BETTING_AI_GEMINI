# -*- coding: utf-8 -*-
"""
BACKTEST A/B — ELO vs el ranking-blend actual para el MONEYLINE de fútbol.

Compara, sobre los partidos reales del Mundial 2026:
  • ELO        : favorito según motors/elo_futbol (rating dinámico histórico)
  • RANKING-MIX: favorito según la lógica actual (0.3 forma + 0.7 ranking FIFA)

Métricas:
  - Acierto del favorito (solo partidos decisivos: el ML no puede ganar empate)
  - Brier score (calibración: menor = mejor)

Uso:  python backtest_elo_vs_ranking.py
"""
import traceback
from backtest_futbol_wc import PARTIDOS_WC


def _real(gl, gv):
    return "LOCAL" if gl > gv else "VISITANTE" if gv > gl else "EMPATE"


def _winpct(team):
    try:
        from utils.database_manager import db
        s = db.get_team_stats_detailed(team, "soccer")
        if not s or not s.get("goles_favor"):
            return None
        gf, gc = s["goles_favor"], s["goles_contra"]
        n = len(gf)
        return sum(1 for f, c in zip(gf, gc) if f > c) / n * 100 if n else None
    except Exception:
        return None


def _rank(team):
    from motors.futbol_analyzer_jerarquico import _FIFA_RANK
    t = team.lower()
    return next((v for k, v in _FIFA_RANK.items() if k.lower() in t or t in k.lower()), 60)


def _fav_ranking(local, visit):
    """Replica la Regla 5 actual: 0.3 forma + 0.7 ranking."""
    wl, wv = _winpct(local), _winpct(visit)
    if wl is None:
        wl = 40.0
    if wv is None:
        wv = 40.0
    rl, rv = _rank(local), _rank(visit)
    edge = max(-0.35, min(0.35, (rv - rl) / 80.0))
    pl = 0.3 * wl + 0.7 * (50 + edge * 100)
    pv = 0.3 * wv + 0.7 * (50 - edge * 100)
    return (local, pl / 100.0) if pl >= pv else (visit, pv / 100.0)


def _fav_elo(local, visit):
    from motors.elo_futbol import prob_1x2
    p = prob_1x2(local, visit)
    if p["local"] >= p["visitante"]:
        return local, p["local"] / 100.0
    return visit, p["visitante"] / 100.0


def main():
    elo = {"ok": 0, "n": 0}
    rnk = {"ok": 0, "n": 0}
    eb = nb = 0
    rows = []
    for fecha, local, visit, gl, gv, fase in PARTIDOS_WC:
        real = _real(gl, gv)
        fe, pe = _fav_elo(local, visit)
        fr, pr = _fav_ranking(local, visit)
        gano_real = local if real == "LOCAL" else visit if real == "VISITANTE" else None
        # Brier sobre "el favorito gana" (resultado binario, empate = no gana)
        eb += (pe - (1 if fe == gano_real else 0)) ** 2
        nb += (pr - (1 if fr == gano_real else 0)) ** 2
        if real != "EMPATE":
            elo["n"] += 1; rnk["n"] += 1
            if fe == gano_real:
                elo["ok"] += 1
            if fr == gano_real:
                rnk["ok"] += 1
        rows.append((f"{local} {gl}-{gv} {visit}", real, f"{fe}({pe*100:.0f}%)", f"{fr}({pr*100:.0f}%)",
                     fe == gano_real, fr == gano_real))

    print("=" * 86)
    print(f"A/B ELO vs RANKING-MIX — {len(PARTIDOS_WC)} partidos reales del Mundial")
    print("=" * 86)
    print(f"{'PARTIDO':<34} {'REAL':<10} {'ELO fav':<18} {'RANKING fav':<18}")
    print("-" * 86)
    for partido, real, fe, fr, eok, rok in rows:
        print(f"{partido[:33]:<34} {real:<10} {fe:<16}{'OK' if eok else ' .':<2} {fr:<16}{'OK' if rok else ' .'}")
    print("-" * 86)
    n = len(PARTIDOS_WC)
    print(f"Acierto del favorito (decisivos):  ELO {elo['ok']}/{elo['n']} = {round(elo['ok']/elo['n']*100,1)}%   "
          f"RANKING {rnk['ok']}/{rnk['n']} = {round(rnk['ok']/rnk['n']*100,1)}%")
    print(f"Brier score (menor = mejor):       ELO {round(eb/n,4)}   RANKING {round(nb/n,4)}")
    print("=" * 86)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
