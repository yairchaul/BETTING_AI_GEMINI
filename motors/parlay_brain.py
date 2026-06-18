# -*- coding: utf-8 -*-
"""
PARLAY BRAIN — el cerebro que aprende a armar parlays.

Cierra el ciclo: los parlays generados se guardan (parlay_history.json) → se
RESUELVEN a partir del resultado real de sus legs (que pick_memory ya resuelve)
→ se MIDE qué estructuras/tipos ganan más → el generador puede preferirlas.

Un parlay GANA si TODAS sus legs ganaron; PIERDE si alguna perdió; sigue
PENDIENTE si alguna leg aún no se resuelve.
"""
import os
import json

PARLAY_FILE = os.path.join("data", "parlay_history.json")
PICK_FILE = os.path.join("data", "pick_history.json")


def _load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save(path, data):
    try:
        os.makedirs("data", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
    except Exception:
        pass


def _norm(s):
    return (s or "").lower().strip()


def resolver_parlays_pendientes():
    """Resuelve los parlays pendientes según el resultado de sus legs en
    pick_memory. Devuelve cuántos se resolvieron."""
    resueltos = {}
    for p in _load(PICK_FILE):
        if p.get("estado") in ("ganado", "perdido"):
            resueltos[_norm(p.get("pick"))] = p["estado"]
    if not resueltos:
        return 0
    parlays = _load(PARLAY_FILE)
    n = 0
    for par in parlays:
        if par.get("estado") != "pendiente":
            continue
        estados = [resueltos.get(_norm(leg.get("pick"))) for leg in par.get("legs", [])]
        if not estados:
            continue
        if any(e == "perdido" for e in estados):
            par["estado"] = "perdido"; n += 1
        elif all(e == "ganado" for e in estados):
            par["estado"] = "ganado"; n += 1
        # si alguna leg sigue None (sin resolver) → el parlay sigue pendiente
    if n:
        _save(PARLAY_FILE, parlays)
    return n


def stats_por_tipo():
    """Win-rate y ROI por TIPO de parlay (SEGURO, VALOR, MÁXIMO PAGO, etc.)."""
    out = {}
    for par in _load(PARLAY_FILE):
        if par.get("estado") not in ("ganado", "perdido"):
            continue
        d = out.setdefault(par.get("tipo", "?"),
                           {"total": 0, "ganados": 0, "cuota_sum": 0.0})
        d["total"] += 1
        if par["estado"] == "ganado":
            d["ganados"] += 1
            d["cuota_sum"] += float(par.get("cuota", 1) or 1)
    for d in out.values():
        d["win_rate"] = round(d["ganados"] / d["total"] * 100, 1) if d["total"] else 0
        # ROI apostando 1u por parlay: (suma de cuotas ganadas − total apostado) / total
        d["roi"] = round((d["cuota_sum"] - d["total"]) / d["total"] * 100, 1) if d["total"] else 0
    return out


def stats_de_tipo(tipo):
    return stats_por_tipo().get(tipo, {})


def factor_tipo(tipo, minimo=4):
    """Multiplicador de preferencia por tipo de parlay según su win-rate real
    (1.0 si no hay muestra suficiente). El generador puede usarlo para priorizar."""
    s = stats_de_tipo(tipo)
    if not s or s.get("total", 0) < minimo:
        return 1.0
    wr = s["win_rate"] / 100.0
    return round(max(0.6, min(1.4, 0.7 + wr)), 2)


if __name__ == "__main__":
    print("Parlays resueltos:", resolver_parlays_pendientes())
    print("Stats por tipo:", json.dumps(stats_por_tipo(), ensure_ascii=False, indent=2))
