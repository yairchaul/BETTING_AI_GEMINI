# -*- coding: utf-8 -*-
"""
ODDS API — Momios REALES de mercado vía the-odds-api.com (no inventados).

Fuente fiable que funciona en la nube (JSON, sin Selenium ni región MX).
Usa ODDS_API_KEY del .env. Cuota gratuita ~500 req/mes → cacheamos en disco
(TTL 6h) para gastar poco. Los nombres se normalizan (ñ/acentos) para matchear.
"""

import os
import json
import time
import logging

import requests

try:
    from utils.fuzzy_matching import normalizar
except Exception:
    def normalizar(s):
        return (s or "").lower().strip()

logger = logging.getLogger(__name__)

_BASE = "https://api.the-odds-api.com/v4/sports"
_CACHE_FILE = os.path.join("data", "odds_api_cache.json")
_TTL = 6 * 3600


def _key():
    k = os.getenv("ODDS_API_KEY", "")
    return k.strip().strip('"').strip("'")


def _cache_load():
    try:
        with open(_CACHE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _cache_save(cache):
    try:
        os.makedirs("data", exist_ok=True)
        with open(_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False)
    except Exception:
        pass


def _fetch_odds(sport_key):
    """Eventos con momios h2h (americano) de un deporte. Cacheado a disco (TTL)."""
    cache = _cache_load()
    entry = cache.get(sport_key)
    if entry and (time.time() - entry.get("ts", 0)) < _TTL:
        return entry.get("data", [])

    key = _key()
    if not key:
        logger.warning("ODDS_API_KEY no configurada; sin momios reales.")
        return entry.get("data", []) if entry else []

    try:
        url = (f"{_BASE}/{sport_key}/odds/?apiKey={key}"
               "&regions=us&markets=h2h&oddsFormat=american")
        r = requests.get(url, timeout=20)
        if r.status_code != 200:
            logger.warning(f"the-odds-api {sport_key}: HTTP {r.status_code}")
            return entry.get("data", []) if entry else []
        data = r.json()
        cache[sport_key] = {"ts": time.time(), "data": data}
        _cache_save(cache)
        rem = r.headers.get("x-requests-remaining")
        logger.info(f"Momios {sport_key}: {len(data)} eventos (quota restante: {rem})")
        return data
    except Exception as e:
        logger.warning(f"the-odds-api {sport_key} error: {e}")
        return entry.get("data", []) if entry else []


def _americano(v):
    try:
        v = int(round(float(v)))
        return f"+{v}" if v > 0 else str(v)
    except Exception:
        return None


def obtener_odds_ufc():
    """{nombre_normalizado_peleador: momio_americano} de las peleas UFC/MMA."""
    odds = {}
    for ev in _fetch_odds("mma_mixed_martial_arts"):
        for bm in ev.get("bookmakers", []):
            for mkt in bm.get("markets", []):
                if mkt.get("key") != "h2h":
                    continue
                for o in mkt.get("outcomes", []):
                    nombre = normalizar(o.get("name", ""))
                    ml = _americano(o.get("price"))
                    if nombre and ml and nombre not in odds:
                        odds[nombre] = ml
        # con el primer bookmaker basta
    return odds


def obtener_odds_mlb():
    """{nombre_equipo_normalizado: momio_americano} de los juegos MLB de hoy."""
    odds = {}
    for ev in _fetch_odds("baseball_mlb"):
        bms = ev.get("bookmakers", [])
        if not bms:
            continue
        for mkt in bms[0].get("markets", []):
            if mkt.get("key") != "h2h":
                continue
            for o in mkt.get("outcomes", []):
                nombre = normalizar(o.get("name", ""))
                ml = _americano(o.get("price"))
                if nombre and ml:
                    odds[nombre] = ml
    return odds


def obtener_odds_futbol(sport_key="soccer_fifa_world_cup"):
    """Lista de partidos con momios reales: {home, away, home_ml, draw_ml, away_ml}."""
    partidos = []
    for ev in _fetch_odds(sport_key):
        home, away = ev.get("home_team", ""), ev.get("away_team", "")
        ml = {}
        for bm in ev.get("bookmakers", []):
            for mkt in bm.get("markets", []):
                if mkt.get("key") != "h2h":
                    continue
                for o in mkt.get("outcomes", []):
                    nm = o.get("name", "")
                    if nm == home:
                        ml["home"] = _americano(o.get("price"))
                    elif nm == away:
                        ml["away"] = _americano(o.get("price"))
                    else:
                        ml["draw"] = _americano(o.get("price"))
            if ml:
                break
        if ml:
            partidos.append({"home": home, "away": away,
                             "home_ml": ml.get("home"), "draw_ml": ml.get("draw"),
                             "away_ml": ml.get("away")})
    return partidos


def odds_de(nombre, odds_map):
    """Busca el momio de un peleador en el mapa por nombre normalizado (tolerante)."""
    if not nombre or not odds_map:
        return None
    n = normalizar(nombre)
    if n in odds_map:
        return odds_map[n]
    # match parcial por apellido
    for k, v in odds_map.items():
        if n in k or k in n:
            return v
    return None


if __name__ == "__main__":
    u = obtener_odds_ufc()
    print(f"UFC momios reales: {len(u)} peleadores")
    for k in list(u)[:6]:
        print(f"  {k}: {u[k]}")
