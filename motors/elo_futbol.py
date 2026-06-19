# -*- coding: utf-8 -*-
"""
ELO FÚTBOL — ratings dinámicos estilo World Football Elo.

Reproduce todo el historial (martj42/international_results, ~48k partidos desde
1872) actualizando un rating por selección tras cada partido. El rating pondera
la FUERZA del rival y la importancia del torneo, algo que el ranking FIFA fijo +
forma de últimos 5 no capturan bien.

Uso:
  elo_rating(equipo)              -> rating (float, ~1500 media)
  prob_1x2(local, visitante)      -> {local, empate, visitante} en %
  favorito(local, visitante)      -> (equipo, prob%) del más probable a ganar

Cachea los ratings finales en data/elo_ratings.json (se recalcula si caduca).
"""
import os
import json
import math
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

_CACHE = os.path.join("data", "elo_ratings.json")
_CACHE_DIAS = 3
_HFA = 65.0          # ventaja de localía en puntos ELO (~+65)
_R0 = 1500.0         # rating inicial

_ratings = None      # {equipo_norm: rating}


def _base_k(torneo: str) -> float:
    """K (velocidad de ajuste) según la importancia del torneo."""
    t = (torneo or "").lower()
    if "world cup" in t and "qual" not in t:
        return 60.0
    if any(x in t for x in ("euro", "copa américa", "copa america", "gold cup", "african cup", "asian cup")):
        return 50.0
    if "qualif" in t or "eliminat" in t or "nations league" in t:
        return 40.0
    if "friendly" in t or "amistoso" in t:
        return 20.0
    return 35.0


def _mult_goles(gd: int) -> float:
    """Multiplicador por diferencia de goles (World Football Elo)."""
    if gd <= 1:
        return 1.0
    if gd == 2:
        return 1.5
    if gd == 3:
        return 1.75
    return 1.75 + (gd - 3) / 8.0


def _calcular_ratings(force: bool = False) -> dict:
    """Replica el historial y devuelve {equipo: rating}. Cachea en disco."""
    global _ratings
    if _ratings is not None and not force:
        return _ratings

    # Caché en disco
    if not force and os.path.exists(_CACHE):
        try:
            age = (datetime.now() - datetime.fromtimestamp(os.path.getmtime(_CACHE))).days
            if age < _CACHE_DIAS:
                with open(_CACHE, encoding="utf-8") as f:
                    _ratings = json.load(f).get("ratings", {})
                if _ratings:
                    return _ratings
        except Exception:
            pass

    try:
        from motors.international_results import _cargar_datos
        datos = _cargar_datos()
    except Exception as e:
        logger.warning(f"ELO: sin datos históricos ({e})")
        _ratings = {}
        return _ratings

    ratings = {}
    # Orden cronológico (fecha 'YYYY-MM-DD' es ordenable)
    for row in sorted(datos, key=lambda x: x.get("fecha", "")):
        h, a = row.get("local"), row.get("visita")
        if not h or not a:
            continue
        gh, ga = row.get("goles_local", 0), row.get("goles_visita", 0)
        rh = ratings.get(h, _R0)
        ra = ratings.get(a, _R0)
        hfa = 0.0 if row.get("neutral") else _HFA
        dr = rh + hfa - ra
        we = 1.0 / (1.0 + 10 ** (-dr / 400.0))     # score esperado local
        w = 1.0 if gh > ga else (0.5 if gh == ga else 0.0)
        k = _base_k(row.get("torneo", "")) * _mult_goles(abs(gh - ga))
        delta = k * (w - we)
        ratings[h] = rh + delta
        ratings[a] = ra - delta

    _ratings = ratings
    try:
        os.makedirs("data", exist_ok=True)
        with open(_CACHE, "w", encoding="utf-8") as f:
            json.dump({"actualizado": datetime.now().isoformat(),
                       "n_equipos": len(ratings), "ratings": ratings}, f, ensure_ascii=False)
    except Exception:
        pass
    logger.info(f"ELO: {len(ratings)} equipos calculados")
    return _ratings


def _norm(nombre: str):
    try:
        from motors.international_results import _norm as _n
        return _n(nombre)
    except Exception:
        return (nombre or "").lower().strip()


def elo_rating(equipo: str) -> float:
    """Rating ELO del equipo (1500 si no hay historial)."""
    r = _calcular_ratings()
    # 1) nombre normalizado directo (las claves del rating usan _norm)
    eq = _norm(equipo)
    if eq in r:
        return r[eq]
    # 2) alias (South Korea -> korea republic, etc.)
    try:
        from motors.international_results import _resolve
        al = _resolve(equipo)
        if al in r:
            return r[al]
    except Exception:
        al = eq
    # 3) match parcial por nombre
    for k, v in r.items():
        if eq and len(eq) > 3 and (eq in k or k in eq):
            return v
    return _R0


def prob_1x2(local: str, visitante: str, neutral: bool = False) -> dict:
    """Probabilidades 1X2 (%) a partir de la diferencia de ELO."""
    rl = elo_rating(local)
    rv = elo_rating(visitante)
    dr = rl + (0.0 if neutral else _HFA) - rv
    we = 1.0 / (1.0 + 10 ** (-dr / 400.0))          # score esperado local
    # Modelo de empate: más probable cuando los equipos están parejos.
    p_draw = max(0.10, min(0.32, 0.30 * math.exp(-abs(dr) / 300.0)))
    p_local = max(0.0, we - p_draw / 2.0)
    p_visit = max(0.0, 1.0 - we - p_draw / 2.0)
    s = p_local + p_draw + p_visit
    if s <= 0:
        return {"local": 33.3, "empate": 33.3, "visitante": 33.3}
    return {"local": round(p_local / s * 100, 1),
            "empate": round(p_draw / s * 100, 1),
            "visitante": round(p_visit / s * 100, 1)}


def favorito(local: str, visitante: str, neutral: bool = False) -> tuple:
    """(equipo, prob% de ganar) del más probable según ELO."""
    p = prob_1x2(local, visitante, neutral)
    if p["local"] >= p["visitante"]:
        return local, p["local"]
    return visitante, p["visitante"]


if __name__ == "__main__":
    r = _calcular_ratings(force=True)
    top = sorted(r.items(), key=lambda x: -x[1])[:15]
    print(f"ELO calculado para {len(r)} equipos. Top 15:")
    for eq, rt in top:
        print(f"  {eq:<22} {rt:.0f}")
    print("\nEjemplos 1X2:")
    for l, v in [("United States", "Australia"), ("Mexico", "South Korea"),
                 ("Brazil", "Haiti"), ("Spain", "Cape Verde")]:
        print(f"  {l} vs {v}: {prob_1x2(l, v)}  favorito={favorito(l, v)}")
