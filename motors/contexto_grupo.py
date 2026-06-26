# -*- coding: utf-8 -*-
"""
CONTEXTO DE GRUPO — situación de cada selección en el Mundial (standings ESPN),
para que Gemini razone la MOTIVACIÓN/INTERESES que el modelo numérico no ve:

  • ¿Ya clasificó? → puede rotar titulares (menos goles, riesgo de upset).
  • ¿Necesita ganar para avanzar? → sale a atacar (más over / BTTS).
  • ¿Eliminado? → puede jugar suelto o relajado.
  • Diferencia de goles: si necesita golear para pasar por desempate.

Es una capa de CONTEXTO (asesora, vía Gemini), no un número backtesteable. El
modelo numérico sigue siendo la base; esto afina la decisión por situación.
Fuente: ESPN fifa.world/standings. NO-OP si no hay red (devuelve None).
"""
import os
import json
import time
import unicodedata
import logging

logger = logging.getLogger(__name__)

_URL = "https://site.api.espn.com/apis/v2/sports/soccer/fifa.world/standings"
_CACHE = os.path.join("data", "wc_standings_cache.json")
_TTL = 3 * 3600
_mem = {"ts": 0.0, "mapa": None}


def _norm(s: str) -> str:
    t = unicodedata.normalize("NFD", (s or "")).encode("ascii", "ignore").decode()
    return t.lower().replace("-", " ").replace(".", "").strip()


def _standings_map():
    """{equipo_norm: {grupo, pos, pj, pts, dg}} con caché mem+disco. {} si falla."""
    ahora = time.time()
    if _mem["mapa"] is not None and ahora - _mem["ts"] < _TTL:
        return _mem["mapa"]
    try:
        if os.path.exists(_CACHE):
            with open(_CACHE, encoding="utf-8") as f:
                disco = json.load(f)
            if ahora - disco.get("ts", 0) < _TTL:
                _mem.update(ts=disco["ts"], mapa=disco["mapa"])
                return disco["mapa"]
    except Exception:
        pass

    mapa = {}
    try:
        import requests
        r = requests.get(_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        r.raise_for_status()
        data = r.json()
        for grupo in data.get("children", []):
            gname = grupo.get("name", "")
            entries = (grupo.get("standings", {}) or {}).get("entries", []) or []
            for pos, e in enumerate(entries, 1):
                team = (e.get("team", {}) or {}).get("displayName", "")
                stats = {s.get("name"): s.get("value") for s in e.get("stats", [])}
                if not team:
                    continue
                mapa[_norm(team)] = {
                    "grupo": gname, "pos": pos,
                    "pj": int(stats.get("gamesPlayed", 0) or 0),
                    "pts": int(stats.get("points", 0) or 0),
                    "dg": int(stats.get("pointDifferential", 0) or 0),
                }
    except Exception as e:
        logger.debug(f"contexto_grupo standings: {e}")
        return {}

    _mem.update(ts=ahora, mapa=mapa)
    try:
        os.makedirs("data", exist_ok=True)
        with open(_CACHE, "w", encoding="utf-8") as f:
            json.dump({"ts": ahora, "mapa": mapa}, f, ensure_ascii=False)
    except Exception:
        pass
    return mapa


def situacion_grupo(equipo: str):
    """Situación de la selección en su grupo + lectura de motivación. None si no
    se encuentra (p.ej. clubes o sin red)."""
    mapa = _standings_map()
    if not mapa:
        return None
    eq = _norm(equipo)
    info = mapa.get(eq) or next((v for k, v in mapa.items() if eq and (eq in k or k in eq)), None)
    if not info:
        return None
    pj = info["pj"]
    rest = max(0, 3 - pj)
    pos = info["pos"]
    if rest == 0:                                  # fase de grupos terminada para él
        if pos <= 2:
            estado = "clasificado probable (puede rotar titulares)"
        elif pos == 3:
            estado = "3º: depende de mejores terceros (aún se juega algo)"
        else:
            estado = "eliminado probable"
    else:
        if pos <= 2:
            estado = "bien posicionado, pero aún no asegura"
        else:
            estado = "necesita ganar para avanzar (saldrá a atacar)"
    out = dict(info)
    out["partidos_restantes"] = rest
    out["estado"] = estado
    out["resumen"] = (f"{info['grupo']}: {pos}º con {info['pts']} pts en {pj} PJ "
                      f"(dif gol {info['dg']:+d}); quedan {rest} de grupo → {estado}")
    return out
