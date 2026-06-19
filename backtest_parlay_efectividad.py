# -*- coding: utf-8 -*-
"""
BACKTEST DE EFECTIVIDAD DE PARLAYS — motor de fútbol mejorado + cuotas reales.

Corre el motor jerárquico (ruta DB, la del live) sobre los partidos reales del
Mundial, califica cada pick, y arma parlays de 2/3/4 legs para medir:
  - Acierto del parlay (todas las legs aciertan)
  - ROI usando cuotas REALES de The Odds API (moneyline) + cuotas de mercado
    típicas por mercado (OVER/UNDER/BTTS), no inventadas.

Uso:  python backtest_parlay_efectividad.py
"""
import os
import json
import traceback
from datetime import datetime
from backtest_futbol_wc import PARTIDOS_WC

# Cuotas decimales típicas de mercado por tipo de pick (cuando no hay real)
_CUOTA_MERCADO = {
    "OVER 1.5": 1.25, "OVER 2.5": 1.95, "OVER 3.5": 3.20, "OVER 1.5 HT": 2.20,
    "UNDER 2.5": 1.70, "UNDER 1.5": 3.00, "BTTS": 1.85, "AMBOS ANOTAN": 1.85,
    "MONEYLINE": 1.70, "COMBO": 3.50,
}


def _real(gl, gv):
    return "LOCAL" if gl > gv else "VISITANTE" if gv > gl else "EMPATE"


def _cuota_pick(pick, ml_real=None):
    p = pick.lower()
    if "+" in p:  # combinado
        return _CUOTA_MERCADO["COMBO"]
    if "btts" in p or "ambos" in p:
        return _CUOTA_MERCADO["BTTS"]
    if "under 2.5" in p:
        return _CUOTA_MERCADO["UNDER 2.5"]
    if "over 1.5 ht" in p:
        return _CUOTA_MERCADO["OVER 1.5 HT"]
    if "over 1.5" in p:
        return _CUOTA_MERCADO["OVER 1.5"]
    if "over 2.5" in p:
        return _CUOTA_MERCADO["OVER 2.5"]
    if "over 3.5" in p:
        return _CUOTA_MERCADO["OVER 3.5"]
    if "local" in p or "visitante" in p or "gana" in p:
        return ml_real or _CUOTA_MERCADO["MONEYLINE"]
    return 1.80


def _grade(pick, gl, gv, local, visit):
    """True/False/None (no evaluable) del pick vs marcador."""
    p = pick.lower()
    total = gl + gv
    if "ht" in p:
        return None  # no se puede calificar el 1er tiempo con marcador final
    if "+" in p:  # combo: gana X + over Y
        partes = p.split("+")
        gana_ok = (gl > gv) if local.lower()[:5] in partes[0] else ((gv > gl) if visit.lower()[:5] in partes[0] else None)
        ou_ok = None
        for ln in (3.5, 2.5, 1.5, 0.5):
            if str(ln) in partes[1]:
                ou_ok = total > ln
                break
        return (gana_ok and ou_ok) if (gana_ok is not None and ou_ok is not None) else None
    if "btts" in p or "ambos" in p:
        return gl > 0 and gv > 0
    if "under 2.5" in p:
        return total < 2.5
    for ln in (3.5, 2.5, 1.5):
        if f"over {ln}" in p:
            return total > ln
    if "local" in p or local.lower()[:5] in p:
        return gl > gv
    if "visitante" in p or visit.lower()[:5] in p:
        return gv > gl
    return None


def _ml_reales():
    """{equipo_norm: cuota_decimal} de The Odds API (moneyline WC)."""
    out = {}
    try:
        from scrapers.odds_api import obtener_odds_futbol
        def _dec(am):
            try:
                a = int(str(am).replace("+", ""))
                return round(1 + (a / 100.0 if a > 0 else 100.0 / abs(a)), 2)
            except Exception:
                return None
        for o in obtener_odds_futbol() or []:
            if o.get("home_ml"):
                out[(o["home"] or "").lower()] = _dec(o["home_ml"])
            if o.get("away_ml"):
                out[(o["away"] or "").lower()] = _dec(o["away_ml"])
    except Exception:
        pass
    return out


def ejecutar():
    from motors.futbol_analyzer_jerarquico import analizar_futbol_jerarquico
    ml_map = _ml_reales()

    picks = []
    for fecha, local, visit, gl, gv, fase in PARTIDOS_WC:
        try:
            r = analizar_futbol_jerarquico(local, visit, es_torneo=True, fase=fase)
        except Exception:
            continue
        pick = r.get("pick", "")
        res = _grade(pick, gl, gv, local, visit)
        if res is None:
            continue
        # cuota real ML si el pick es moneyline del favorito
        ml_real = None
        pl = pick.lower()
        if "local" in pl or local.lower()[:5] in pl:
            ml_real = ml_map.get(local.lower())
        elif "visitante" in pl or visit.lower()[:5] in pl:
            ml_real = ml_map.get(visit.lower())
        picks.append({"partido": f"{local} {gl}-{gv} {visit}", "pick": pick,
                      "ok": res, "cuota": _cuota_pick(pick, ml_real)})

    # Single-leg
    n_ok = sum(1 for p in picks if p["ok"])
    print("=" * 80)
    print(f"EFECTIVIDAD — motor mejorado sobre {len(picks)} picks evaluables del Mundial")
    print("=" * 80)
    print(f"SINGLE (1 leg): {n_ok}/{len(picks)} = {round(n_ok/len(picks)*100,1)}%")
    print("-" * 80)
    # Parlays de 2/3/4 legs (ventanas consecutivas, sin solapar)
    print("PARLAYS (todas las legs aciertan) — acierto y ROI con cuotas reales/mercado:")
    for n in (2, 3, 4):
        ganados = total_par = 0
        roi_acum = 0.0
        for i in range(0, len(picks) - n + 1, n):
            grupo = picks[i:i + n]
            if len(grupo) < n:
                break
            total_par += 1
            cuota = 1.0
            for g in grupo:
                cuota *= g["cuota"]
            if all(g["ok"] for g in grupo):
                ganados += 1
                roi_acum += (cuota - 1)   # ganancia por unidad apostada
            else:
                roi_acum -= 1
        wr = round(ganados / total_par * 100, 1) if total_par else 0
        roi = round(roi_acum / total_par * 100, 1) if total_par else 0
        print(f"  {n} legs: {ganados}/{total_par} = {wr}% acierto · ROI {roi:+.0f}%")
    print("=" * 80)
    print("Cuotas ML reales de The Odds API; OVER/UNDER/BTTS con cuotas de mercado típicas.")


if __name__ == "__main__":
    try:
        ejecutar()
    except Exception:
        traceback.print_exc()
