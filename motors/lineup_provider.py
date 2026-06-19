# -*- coding: utf-8 -*-
"""
LINEUP PROVIDER — alineación del día con respaldo PROYECTADO.

La alineación oficial de MLB se publica ~1-2h antes del juego. Cuando aún no
está, este módulo usa la ÚLTIMA alineación CONFIRMADA del equipo (de su juego
finalizado más reciente) como proyección, para no quedarse en "por confirmar".

Devuelve, por equipo:
  { "lineup": [nombres], "proyectada": bool, "fuente": "oficial|proyectada" }

Todo vía statsapi; cachea en memoria por game_pk/equipo.
"""
import logging
import unicodedata
import requests

logger = logging.getLogger(__name__)

API = "https://statsapi.mlb.com/api/v1"
API11 = "https://statsapi.mlb.com/api/v1.1"
HEAD = {"User-Agent": "Mozilla/5.0"}

_cache = {}   # (game_pk, lado) -> dict


def _norm(s):
    t = unicodedata.normalize("NFD", (s or "").strip()).encode("ascii", "ignore").decode()
    return t.lower().replace(".", "").replace("-", " ").strip()


def _get(url):
    try:
        r = requests.get(url, headers=HEAD, timeout=12)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        logger.debug(f"lineup_provider GET {url}: {e}")
    return None


def _battingorder_nombres(box_team):
    """Nombres en orden de bateo de un team del boxscore (battingOrder)."""
    nombres = []
    players = box_team.get("players", {})
    orden = box_team.get("battingOrder", []) or []
    for pid in orden:
        p = players.get(f"ID{pid}") or players.get(str(pid))
        if p:
            nm = p.get("person", {}).get("fullName", "")
            if nm:
                nombres.append(nm)
    # Respaldo: si no hay battingOrder, usar 'batters'
    if not nombres:
        for pid in box_team.get("batters", [])[:9]:
            p = players.get(f"ID{pid}")
            if p:
                nm = p.get("person", {}).get("fullName", "")
                if nm:
                    nombres.append(nm)
    return nombres


def _ultima_alineacion_confirmada(team_id):
    """Última alineación CONFIRMADA del equipo (de su juego final más reciente)."""
    if not team_id:
        return []
    sched = _get(f"{API}/schedule?sportId=1&teamId={team_id}&season=2026"
                 f"&gameType=R&hydrate=team&fields=dates,games,gamePk,status,abstractGameState")
    if not sched:
        return []
    finales = [g for dt in sched.get("dates", []) for g in dt.get("games", [])
               if g.get("status", {}).get("abstractGameState") == "Final"]
    if not finales:
        return []
    # El más reciente
    for g in sorted(finales, key=lambda x: x.get("gamePk", 0), reverse=True)[:3]:
        box = _get(f"{API}/game/{g['gamePk']}/boxscore")
        if not box:
            continue
        for lado in ("home", "away"):
            t = box.get("teams", {}).get(lado, {})
            if t.get("team", {}).get("id") == team_id:
                nombres = _battingorder_nombres(t)
                if nombres:
                    return nombres
    return []


def obtener_lineup(game_pk, equipo_nombre):
    """Alineación del equipo para el juego. Oficial si está; si no, proyectada
    (última confirmada). Devuelve dict con lineup/proyectada/fuente."""
    if not game_pk:
        return {"lineup": [], "proyectada": True, "fuente": "sin_game_pk"}
    clave = (str(game_pk), _norm(equipo_nombre))
    if clave in _cache:
        return _cache[clave]

    res = {"lineup": [], "proyectada": True, "fuente": "no_disponible"}
    feed = _get(f"{API11}/game/{game_pk}/feed/live")
    team_id = None
    if feed:
        box = feed.get("liveData", {}).get("boxscore", {}).get("teams", {})
        gdata = feed.get("gameData", {}).get("teams", {})
        for lado in ("home", "away"):
            nombre = box.get(lado, {}).get("team", {}).get("name", "")
            if _norm(nombre) == _norm(equipo_nombre) or _norm(equipo_nombre) in _norm(nombre):
                oficial = _battingorder_nombres(box.get(lado, {}))
                team_id = gdata.get(lado, {}).get("id")
                if len(oficial) >= 9:           # alineación oficial completa
                    res = {"lineup": oficial, "proyectada": False, "fuente": "oficial"}
                    _cache[clave] = res
                    return res
                break

    # Sin oficial completa → proyectar con la última confirmada
    proy = _ultima_alineacion_confirmada(team_id)
    if proy:
        res = {"lineup": proy, "proyectada": True, "fuente": "proyectada"}
    _cache[clave] = res
    return res


def en_alineacion(jugador, lineup_info):
    """True si el jugador está en la alineación (oficial o proyectada)."""
    if not lineup_info or not lineup_info.get("lineup"):
        return None      # desconocida
    jn = _norm(jugador)
    for ln in lineup_info["lineup"]:
        lnn = _norm(ln)
        if jn in lnn or lnn in jn:
            return True
        # match por apellido
        ap = jn.split()[-1] if jn.split() else ""
        if ap and len(ap) > 3 and ap in lnn:
            return True
    return False
