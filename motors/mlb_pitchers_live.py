# -*- coding: utf-8 -*-
"""
MLB PITCHERS LIVE — Abridores probables del día + stats de temporada.

Fuente: MLB Stats API oficial (statsapi.mlb.com). El factor #1 de un juego
individual de MLB es el duelo de abridores; este módulo lo revive con datos
FRESCOS del día, por pitcher (no por equipo, no de un JSON congelado).

Claves de diseño:
  • Una sola llamada para los probables (schedule) + una sola para sus stats
    (people en bloque). Se cachea en memoria (TTL) y en disco como respaldo.
  • SHRINKAGE bayesiano: una ERA de 0.74 en 1 salida o 10.80 en 2 entradas no
    debe dominar. Cada stat se regresa hacia la media de liga según las entradas
    lanzadas, así los abridores con poca muestra no engañan al motor.

Uso:
    from motors.mlb_pitchers_live import obtener_abridores_hoy, calidad_pitcher
    mapa = obtener_abridores_hoy()              # {team_lower: {...}}
    info = mapa.get("chicago white sox")        # abridor de los White Sox hoy
"""

import os
import json
import time
import logging
from datetime import datetime

import requests

logger = logging.getLogger(__name__)

# Medias de liga (referencia para shrinkage y para el composite de calidad)
LIGA_ERA = 4.20
LIGA_WHIP = 1.30
LIGA_K9 = 8.2
PRIOR_IP = 25.0          # "entradas previas" del prior — más alto = más conservador

_API = "https://statsapi.mlb.com/api/v1"
_HEADERS = {"User-Agent": "Mozilla/5.0"}
_TTL = 3 * 3600          # 3 horas
_DISK = os.path.join("data", "abridores_hoy.json")

_CACHE = {"ts": 0.0, "fecha": None, "data": {}}
_ULTIMO_INTENTO = 0.0      # anti-martilleo cuando la API no responde
_COOLDOWN = 600.0          # 10 min entre reintentos si el fetch viene vacío


# ──────────────────────────────────────────────────────────────────────────
# PARSING / SHRINKAGE
# ──────────────────────────────────────────────────────────────────────────

def _parse_ip(ip):
    """'56.2' → 56.667 (en béisbol el decimal son outs: .1=1/3, .2=2/3)."""
    try:
        s = str(ip).strip()
        if not s or s in ("-", "--", "None"):
            return 0.0
        if "." in s:
            whole, frac = s.split(".", 1)
            return int(whole or 0) + (int(frac[0]) / 3.0)
        return float(s)
    except Exception:
        return 0.0


def _to_float(v, default=0.0):
    try:
        f = float(v)
        # MLB usa "-.--"/"*.**" para infinito; los descartamos
        return f if f == f and f not in (float("inf"),) else default
    except Exception:
        return default


def _shrink(value, prior, ip, prior_ip=PRIOR_IP):
    """Regresa un ratio hacia la media de liga según la muestra (IP)."""
    if ip <= 0:
        return prior
    return (value * ip + prior * prior_ip) / (ip + prior_ip)


# ──────────────────────────────────────────────────────────────────────────
# CALIDAD COMPUESTA DEL ABRIDOR
# ──────────────────────────────────────────────────────────────────────────

def calidad_pitcher(info):
    """Calidad compuesta del abridor (0 ≈ media de liga; + es mejor).

    ERA manda (cada carrera de ERA pesa ~1), WHIP y K/9 afinan. Se usan los
    valores YA suavizados por shrinkage (era_adj/whip_adj/k9_adj).
    """
    if not info:
        return 0.0
    era = info.get("era_adj", info.get("era", LIGA_ERA)) or LIGA_ERA
    whip = info.get("whip_adj", info.get("whip", LIGA_WHIP)) or LIGA_WHIP
    k9 = info.get("k9_adj", info.get("k9", LIGA_K9)) or LIGA_K9
    q = (LIGA_ERA - era) \
        + (LIGA_WHIP - whip) * 4.0 \
        + (k9 - LIGA_K9) * 0.35
    return round(q, 3)


# ──────────────────────────────────────────────────────────────────────────
# FETCH
# ──────────────────────────────────────────────────────────────────────────

def _fetch(fecha):
    """Devuelve {team_lower: {nombre, id, era, whip, k9, ip, gs, *_adj, calidad}}."""
    mapa = {}
    try:
        url = (f"{_API}/schedule?sportId=1&date={fecha}"
               "&hydrate=probablePitcher,team")
        sch = requests.get(url, headers=_HEADERS, timeout=12).json()
    except Exception as e:
        logger.warning(f"MLB schedule no disponible: {e}")
        return mapa

    pid_team = {}   # pitcher_id → (team_name, pitcher_name, game_pk)
    for d in sch.get("dates", []):
        for g in d.get("games", []):
            game_pk = g.get("gamePk")
            for lado in ("home", "away"):
                t = g["teams"][lado]
                team_name = t.get("team", {}).get("name", "")
                pp = t.get("probablePitcher", {}) or {}
                pid = pp.get("id")
                entry = {
                    "nombre": pp.get("fullName", "TBD") or "TBD",
                    "id": pid, "game_pk": game_pk,
                    "era": LIGA_ERA, "whip": LIGA_WHIP, "k9": LIGA_K9,
                    "ip": 0.0, "gs": 0,
                }
                if team_name:
                    mapa[team_name.lower()] = entry
                    if pid:
                        pid_team[pid] = team_name.lower()

    if not pid_team:
        return mapa

    # Stats de temporada en bloque (una sola llamada)
    try:
        idlist = ",".join(str(i) for i in pid_team)
        season = fecha[:4]
        url = (f"{_API}/people?personIds={idlist}"
               f"&hydrate=stats(group=[pitching],type=[season],season={season})")
        ppl = requests.get(url, headers=_HEADERS, timeout=20).json()
    except Exception as e:
        logger.warning(f"MLB people stats no disponible: {e}")
        ppl = {}

    for person in ppl.get("people", []):
        pid = person.get("id")
        team = pid_team.get(pid)
        if not team or team not in mapa:
            continue
        era = whip = None
        so = 0
        ip = 0.0
        gs = 0
        for sg in person.get("stats", []):
            for sp in sg.get("splits", []):
                stt = sp.get("stat", {})
                era = _to_float(stt.get("era"), LIGA_ERA)
                whip = _to_float(stt.get("whip"), LIGA_WHIP)
                so = int(_to_float(stt.get("strikeOuts"), 0))
                ip = _parse_ip(stt.get("inningsPitched"))
                gs = int(_to_float(stt.get("gamesStarted"), 0))
        if era is None:
            continue
        k9 = (so * 9.0 / ip) if ip > 0 else LIGA_K9
        info = mapa[team]
        info.update(era=round(era, 2), whip=round(whip, 2), k9=round(k9, 2),
                    ip=round(ip, 1), gs=gs)
        # Shrinkage hacia la media según las entradas lanzadas
        info["era_adj"] = round(_shrink(era, LIGA_ERA, ip), 2)
        info["whip_adj"] = round(_shrink(whip, LIGA_WHIP, ip), 2)
        info["k9_adj"] = round(_shrink(k9, LIGA_K9, ip), 2)
        info["calidad"] = calidad_pitcher(info)

    # Calidad para los que tienen pitcher pero sin stats (queda en media → 0)
    for info in mapa.values():
        info.setdefault("calidad", calidad_pitcher(info))
    return mapa


# ──────────────────────────────────────────────────────────────────────────
# API PÚBLICA
# ──────────────────────────────────────────────────────────────────────────

def obtener_abridores_hoy(force=False):
    """Mapa {team_lower: info_abridor} para los juegos de hoy (cacheado)."""
    global _ULTIMO_INTENTO
    hoy = datetime.now().strftime("%Y-%m-%d")
    if (not force and _CACHE["fecha"] == hoy
            and (time.time() - _CACHE["ts"]) < _TTL and _CACHE["data"]):
        return _CACHE["data"]

    # Si un intento reciente vino vacío, no remartillar la API dentro del loop
    if not force and (time.time() - _ULTIMO_INTENTO) < _COOLDOWN and not _CACHE["data"]:
        return _disco_si_es_hoy(hoy)

    _ULTIMO_INTENTO = time.time()
    data = _fetch(hoy)
    if data:
        _CACHE.update(ts=time.time(), fecha=hoy, data=data)
        try:
            os.makedirs("data", exist_ok=True)
            with open(_DISK, "w", encoding="utf-8") as f:
                json.dump({"fecha": hoy, "abridores": data}, f,
                          ensure_ascii=False, indent=2)
        except Exception:
            pass
        return data

    # Sin red: respaldo en memoria o disco (solo si es de hoy)
    if _CACHE["data"]:
        return _CACHE["data"]
    return _disco_si_es_hoy(hoy)


def _disco_si_es_hoy(hoy):
    """Lee el respaldo en disco solo si corresponde a la fecha de hoy."""
    if _CACHE["data"]:
        return _CACHE["data"]
    try:
        with open(_DISK, encoding="utf-8") as f:
            disk = json.load(f)
        if disk.get("fecha") == hoy:
            return disk.get("abridores", {})
    except Exception:
        pass
    return {}


def _buscar_equipo(mapa, nombre_equipo):
    """Match tolerante por nombre de equipo (substring en ambos sentidos)."""
    if not nombre_equipo:
        return None
    ne = nombre_equipo.lower().strip()
    if ne in mapa:
        return mapa[ne]
    for k, v in mapa.items():
        if k in ne or ne in k:
            return v
    return None


def abridor_de(equipo, mapa=None):
    """Info del abridor de un equipo hoy (o None)."""
    mapa = mapa if mapa is not None else obtener_abridores_hoy()
    return _buscar_equipo(mapa, equipo)


if __name__ == "__main__":
    m = obtener_abridores_hoy(force=True)
    print(f"Equipos con abridor hoy: {len(m)}\n")
    filas = sorted(m.items(), key=lambda kv: kv[1].get("calidad", 0), reverse=True)
    for team, info in filas:
        print(f"{team:24} {info['nombre']:20} "
              f"ERA {info.get('era','--'):>5} (adj {info.get('era_adj','--'):>5}) "
              f"WHIP {info.get('whip','--'):>5} K9 {info.get('k9','--'):>5} "
              f"IP {info.get('ip','--'):>5} → calidad {info.get('calidad',0):+.2f}")
