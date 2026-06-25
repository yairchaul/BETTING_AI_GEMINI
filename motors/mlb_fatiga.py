# -*- coding: utf-8 -*-
"""
MLB FATIGA — factor de cansancio del EQUIPO bateador (lo comparten todos sus
bateadores en el partido). Señales REALES del calendario oficial (statsapi, el
mismo que ya usa el predictor para lineups):

  1. Doble jornada, JUEGO 2  → el desgaste del primer partido pesa.
  2. Día después de un juego NOCTURNO → menos descanso/viaje (caída ofensiva leve
     documentada en sabermetría).
  3. Densidad de calendario → muchos días seguidos sin descanso.

Solo REDUCE la probabilidad de HR; el descanso es neutro (factor 1.0). Acotado a
[0.90, 1.0] y suave (los efectos reales son pequeños). NO-OP si no hay red o no
se encuentra al equipo → nunca puede empeorar un pick por falta de datos.
"""
import os
import json
import time
import logging
import unicodedata
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

_CACHE_PATH = os.path.join("data", "mlb_schedule_cache.json")
_TTL = 6 * 3600
_mem = {"ts": 0.0, "rango": None, "juegos": None}


def _norm(s: str) -> str:
    t = unicodedata.normalize("NFD", (s or "")).encode("ascii", "ignore").decode()
    return t.lower().replace(".", "").strip()


def _schedule(start: str, end: str):
    """Calendario MLB del rango [start, end] (un solo llamado cubre toda la liga).
    Cacheado en memoria y disco. Lanza excepción si no hay red (el caller la captura)."""
    rango = f"{start}:{end}"
    ahora = time.time()
    if _mem["juegos"] is not None and _mem["rango"] == rango and ahora - _mem["ts"] < _TTL:
        return _mem["juegos"]
    # Caché en disco
    try:
        if os.path.exists(_CACHE_PATH):
            with open(_CACHE_PATH, encoding="utf-8") as f:
                disco = json.load(f)
            if disco.get("rango") == rango and ahora - disco.get("ts", 0) < _TTL:
                _mem.update(ts=disco["ts"], rango=rango, juegos=disco["juegos"])
                return disco["juegos"]
    except Exception:
        pass

    import requests
    url = (f"https://statsapi.mlb.com/api/v1/schedule?sportId=1"
           f"&startDate={start}&endDate={end}")
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=12)
    r.raise_for_status()
    data = r.json()
    juegos = []
    for d in data.get("dates", []):
        for g in d.get("games", []):
            teams = g.get("teams", {})
            home = teams.get("home", {}).get("team", {}).get("name", "")
            away = teams.get("away", {}).get("team", {}).get("name", "")
            juegos.append({
                "fecha": g.get("officialDate") or g.get("gameDate", "")[:10],
                "datetime": g.get("gameDate", ""),
                "dh": g.get("doubleHeader", "N"),
                "num": g.get("gameNumber", 1),
                "home": _norm(home),
                "away": _norm(away),
            })
    _mem.update(ts=ahora, rango=rango, juegos=juegos)
    try:
        os.makedirs("data", exist_ok=True)
        with open(_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump({"ts": ahora, "rango": rango, "juegos": juegos}, f)
    except Exception:
        pass
    return juegos


def _hora_utc(dt_str: str):
    try:
        return int(dt_str[11:13])
    except (ValueError, TypeError, IndexError):
        return None


def _es_dia(dt_str: str) -> bool:
    """Proxy de juego DIURNO por la hora UTC (≈11am-5pm ET = 15-21 UTC).
    Imperfecto por husos, por eso la penalización asociada es pequeña."""
    h = _hora_utc(dt_str)
    return h is not None and 15 <= h < 21


def factor_fatiga(equipo: str, fecha: str = None):
    """(factor, razon) de fatiga del equipo. factor en [0.90, 1.0]; 1.0 = sin
    fatiga detectada o sin datos. razon = texto descriptivo (o '')."""
    hoy = (fecha or datetime.now().strftime("%Y-%m-%d"))[:10]
    try:
        hoy_dt = datetime.strptime(hoy, "%Y-%m-%d")
    except ValueError:
        return 1.0, ""
    inicio = (hoy_dt - timedelta(days=8)).strftime("%Y-%m-%d")
    try:
        juegos = _schedule(inicio, hoy)
    except Exception as e:
        logger.debug(f"mlb_fatiga sin calendario: {e}")
        return 1.0, ""

    eq = _norm(equipo)
    if not eq:
        return 1.0, ""
    mios = [g for g in juegos
            if (eq in g["home"] or g["home"] in eq or eq in g["away"] or g["away"] in eq)]
    if not mios:
        return 1.0, ""
    mios.sort(key=lambda g: (g["fecha"], g["num"]))

    hoy_juegos = [g for g in mios if g["fecha"] == hoy]
    previos = [g for g in mios if g["fecha"] < hoy]
    ayer = (hoy_dt - timedelta(days=1)).strftime("%Y-%m-%d")
    hace7 = (hoy_dt - timedelta(days=6)).strftime("%Y-%m-%d")

    f = 1.0
    razones = []
    # 1) Doble jornada, juego 2
    if any(g["num"] >= 2 for g in hoy_juegos):
        f *= 0.95
        razones.append("doble jornada (juego 2)")
    # 2) Día después de juego nocturno (ayer noche → hoy día)
    if hoy_juegos and previos:
        ult = previos[-1]
        if (ult["fecha"] == ayer and not _es_dia(ult["datetime"])
                and _es_dia(hoy_juegos[0]["datetime"])):
            f *= 0.96
            razones.append("día después de juego nocturno")
    # 3) Densidad: días distintos con juego en la última semana (sin descanso)
    dias_jugados = len({g["fecha"] for g in mios if hace7 <= g["fecha"] <= hoy})
    if dias_jugados >= 7:
        f *= 0.97
        razones.append(f"{dias_jugados} días seguidos sin descanso")

    f = round(max(0.90, min(1.0, f)), 3)
    return f, (" + ".join(razones) if razones else "")
