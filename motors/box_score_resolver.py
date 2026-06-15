# -*- coding: utf-8 -*-
"""
BOX SCORE RESOLVER — Resuelve los picks pendientes de la memoria (pick_memory)
contra BOX SCORES REALES.

Fuentes:
  • MLB  → MLB Stats API (schedule + boxscore): marcador, HR, bases totales, K.
  • NBA  → ESPN (scoreboard + summary/boxscore): puntos, rebotes, asistencias, triples.
  • Fútbol → ESPN soccer (se mantiene el resolver de main).

Cada pick se marca ganado/perdido/push según el resultado real.
"""
import re
import unicodedata
import requests
from datetime import datetime
from collections import defaultdict

from motors.pick_memory import pick_memory

HEADERS = {"User-Agent": "Mozilla/5.0"}


def _norm(txt):
    if not txt:
        return ""
    t = unicodedata.normalize("NFD", str(txt)).encode("ascii", "ignore").decode("utf-8")
    return t.lower().replace(".", "").replace(" jr", "").replace(" sr", "").strip()


def _get(url, timeout=12):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def _num_en(texto):
    m = re.search(r"(\d+\.?\d*)", str(texto))
    return float(m.group(1)) if m else None


# ══════════════════════════ MLB ══════════════════════════
def _mlb_juegos_fecha(fecha):
    """{gamePk, home, away, hs, as} de los juegos FINALES de esa fecha."""
    url = (f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={fecha}"
           "&hydrate=linescore,team")
    data = _get(url)
    juegos = []
    if not data:
        return juegos
    for d in data.get("dates", []):
        for g in d.get("games", []):
            estado = g.get("status", {}).get("abstractGameState", "")
            if estado != "Final":
                continue
            t = g.get("teams", {})
            juegos.append({
                "gamePk": g.get("gamePk"),
                "home": t.get("home", {}).get("team", {}).get("name", ""),
                "away": t.get("away", {}).get("team", {}).get("name", ""),
                "hs": t.get("home", {}).get("score", 0),
                "as": t.get("away", {}).get("score", 0),
            })
    return juegos


def _mlb_boxscore(game_pk):
    """{bateadores:{norm:{hr,tb}}, pitchers:{norm:{k}}} del juego."""
    data = _get(f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live", timeout=15)
    out = {"bateadores": {}, "pitchers": {}}
    if not data:
        return out
    box = data.get("liveData", {}).get("boxscore", {}).get("teams", {})
    for lado in ("home", "away"):
        players = box.get(lado, {}).get("players", {})
        for _pid, pdata in players.items():
            nombre = _norm(pdata.get("person", {}).get("fullName", ""))
            bat = pdata.get("stats", {}).get("batting", {})
            pit = pdata.get("stats", {}).get("pitching", {})
            if bat:
                hr = int(bat.get("homeRuns", 0) or 0)
                # Bases totales: H + 2B + 2*3B + 3*HR  (TB estándar)
                h = int(bat.get("hits", 0) or 0)
                dobles = int(bat.get("doubles", 0) or 0)
                triples = int(bat.get("triples", 0) or 0)
                tb = h + dobles + 2 * triples + 3 * hr
                out["bateadores"][nombre] = {"hr": hr, "tb": tb}
            if pit:
                out["pitchers"][nombre] = {"k": int(pit.get("strikeOuts", 0) or 0)}
    return out


def _match_juego(evento, juegos):
    """Empata el evento ('A @ B' / 'A vs B') con un juego real."""
    partes = re.split(r"\s+@\s+|\s+vs\s+", evento)
    if len(partes) != 2:
        return None
    a, b = _norm(partes[0]), _norm(partes[1])
    for j in juegos:
        nh, na = _norm(j["home"]), _norm(j["away"])
        if {a, b} & {nh} and {a, b} & {na}:
            return j
        if (a in nh or nh in a or a in na or na in a) and (b in nh or nh in b or b in na or na in b):
            return j
    return None


def _resolver_mlb(pendientes, progreso_cb=None):
    por_fecha = defaultdict(list)
    for p in pendientes:
        if (p.get("deporte") or "").upper() == "MLB":
            por_fecha[p.get("fecha_evento") or p.get("fecha")].append(p)

    n = 0
    for fecha, picks in por_fecha.items():
        juegos = _mlb_juegos_fecha(fecha)
        if not juegos:
            continue
        box_cache = {}
        for p in picks:
            j = _match_juego(p.get("evento", ""), juegos)
            if not j:
                continue
            mercado = (p.get("mercado") or "").upper()
            pick_txt = p.get("pick", "")
            pl = pick_txt.lower()
            res = None
            total = j["hs"] + j["as"]
            marcador = f'{j["away"]} {j["as"]}-{j["hs"]} {j["home"]}'

            if "MONEYLINE" in mercado or pl.startswith("gana"):
                gana_home = j["hs"] > j["as"]
                ganador = _norm(j["home"]) if gana_home else _norm(j["away"])
                res = ganador in _norm(pick_txt) or _norm(pick_txt).find(ganador) >= 0
            elif "TOTAL BASES" in mercado or "bases" in pl:
                if j["gamePk"] not in box_cache:
                    box_cache[j["gamePk"]] = _mlb_boxscore(j["gamePk"])
                linea = _num_en(re.sub(r"bases", "", pl)) or 1.5
                jugador = _norm(re.split(r"over|under", pick_txt, flags=re.I)[0])
                bat = _buscar_jugador(box_cache[j["gamePk"]]["bateadores"], jugador)
                if bat is not None:
                    res = bat["tb"] > linea if "over" in pl else bat["tb"] < linea
            elif mercado == "TOTAL" or "over" in pl or "under" in pl:
                linea = _num_en(pick_txt) or 8.5
                res = total > linea if "over" in pl else total < linea
            elif "HOME RUN" in mercado or " hr" in pl or "pega hr" in pl:
                if j["gamePk"] not in box_cache:
                    box_cache[j["gamePk"]] = _mlb_boxscore(j["gamePk"])
                jugador = _norm(pick_txt.split(" pega")[0].split(" HR")[0])
                bat = _buscar_jugador(box_cache[j["gamePk"]]["bateadores"], jugador)
                if bat is not None:
                    res = bat["hr"] >= 1
            elif "K" in mercado or " k" in pl:
                if j["gamePk"] not in box_cache:
                    box_cache[j["gamePk"]] = _mlb_boxscore(j["gamePk"])
                linea = _num_en(re.sub(r"\bk\b", "", pl)) or 5.5
                pitcher = _norm(re.split(r"over|under", pick_txt, flags=re.I)[0])
                pit = _buscar_jugador(box_cache[j["gamePk"]]["pitchers"], pitcher)
                if pit is not None:
                    res = pit["k"] > linea if "over" in pl else pit["k"] < linea

            if res is not None:
                pick_memory.resolver(p["id"], "ganado" if res else "perdido", marcador)
                n += 1
        if progreso_cb:
            progreso_cb(f"MLB {fecha}: {n} resueltos")
    return n


def _buscar_jugador(mapa, nombre_norm):
    if not nombre_norm:
        return None
    if nombre_norm in mapa:
        return mapa[nombre_norm]
    for k, v in mapa.items():
        if nombre_norm in k or k in nombre_norm:
            return v
        # match por apellido
        ap = nombre_norm.split()[-1] if nombre_norm.split() else ""
        if ap and len(ap) > 3 and ap in k:
            return v
    return None


# ══════════════════════════ NBA ══════════════════════════
def _nba_juegos_fecha(fecha):
    """fecha 'YYYY-MM-DD' → eventos finales con id + scores."""
    ymd = fecha.replace("-", "")
    data = _get(f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={ymd}")
    juegos = []
    if not data:
        return juegos
    for e in data.get("events", []):
        c = e.get("competitions", [{}])[0]
        if not c.get("status", {}).get("type", {}).get("completed"):
            continue
        comp = {x.get("homeAway"): x for x in c.get("competitors", [])}
        h, a = comp.get("home", {}), comp.get("away", {})
        juegos.append({
            "id": e.get("id"),
            "home": h.get("team", {}).get("displayName", ""),
            "away": a.get("team", {}).get("displayName", ""),
            "hs": int(h.get("score", 0) or 0),
            "as": int(a.get("score", 0) or 0),
        })
    return juegos


def _nba_boxscore(event_id):
    """{jugador_norm: {pts, reb, ast, 3pm}} del summary de ESPN."""
    data = _get(f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={event_id}")
    out = {}
    if not data:
        return out
    for team in data.get("boxscore", {}).get("players", []):
        for grp in team.get("statistics", []):
            labels = grp.get("labels", grp.get("names", []))
            try:
                i_pts = labels.index("PTS"); i_reb = labels.index("REB"); i_ast = labels.index("AST")
                i_3pm = labels.index("3PT")
            except ValueError:
                i_pts = i_reb = i_ast = i_3pm = None
            for ath in grp.get("athletes", []):
                nombre = _norm(ath.get("athlete", {}).get("displayName", ""))
                stats = ath.get("stats", [])
                if not stats or i_pts is None or i_pts >= len(stats):
                    continue
                try:
                    pts = float(stats[i_pts]) if stats[i_pts] not in ("--", "") else 0
                    reb = float(stats[i_reb]) if stats[i_reb] not in ("--", "") else 0
                    ast = float(stats[i_ast]) if stats[i_ast] not in ("--", "") else 0
                    tpm = float(str(stats[i_3pm]).split("-")[0]) if "-" in str(stats[i_3pm]) else 0
                except (ValueError, IndexError):
                    continue
                out[nombre] = {"pts": pts, "reb": reb, "ast": ast, "3pm": tpm}
    return out


def _resolver_nba(pendientes, progreso_cb=None):
    por_fecha = defaultdict(list)
    for p in pendientes:
        if (p.get("deporte") or "").upper() == "NBA":
            por_fecha[p.get("fecha_evento") or p.get("fecha")].append(p)

    n = 0
    for fecha, picks in por_fecha.items():
        juegos = _nba_juegos_fecha(fecha)
        if not juegos:
            continue
        box_cache = {}
        for p in picks:
            j = _match_juego(p.get("evento", ""), juegos)
            if not j:
                continue
            mercado = (p.get("mercado") or "").upper()
            pick_txt = p.get("pick", "")
            pl = pick_txt.lower()
            res = None
            total = j["hs"] + j["as"]
            marcador = f'{j["away"]} {j["as"]}-{j["hs"]} {j["home"]}'

            if "MONEYLINE" in mercado or pl.startswith("gana"):
                ganador = _norm(j["home"]) if j["hs"] > j["as"] else _norm(j["away"])
                res = ganador in _norm(pick_txt)
            elif "TOTAL" in mercado and "OVER" in pick_txt.upper():
                linea = _num_en(pick_txt) or 225.5
                res = total > linea
            elif "TOTAL" in mercado and "UNDER" in pick_txt.upper():
                linea = _num_en(pick_txt) or 225.5
                res = total < linea
            elif "PROP" in mercado:
                if j["id"] not in box_cache:
                    box_cache[j["id"]] = _nba_boxscore(j["id"])
                res = _grade_prop_nba(pick_txt, box_cache[j["id"]])

            if res is not None:
                pick_memory.resolver(p["id"], "ganado" if res else "perdido", marcador)
                n += 1
        if progreso_cb:
            progreso_cb(f"NBA {fecha}: {n} resueltos")
    return n


def _grade_prop_nba(pick_txt, boxscore):
    """Evalúa un prop NBA: '<jugador> <Stat> OVER <linea>'."""
    pl = pick_txt.lower()
    stat_key = None
    for clave, k in (("punto", "pts"), ("rebote", "reb"), ("asistenc", "ast"), ("triple", "3pm")):
        if clave in pl:
            stat_key = k
            break
    if not stat_key:
        return None
    linea = _num_en(re.split(r"over|under", pick_txt, flags=re.I)[-1])
    if linea is None:
        return None
    jugador = _norm(re.split(r"puntos|rebotes|asistencias|triples|over|under", pick_txt, flags=re.I)[0])
    jug = _buscar_jugador(boxscore, jugador)
    if jug is None:
        return None
    return jug[stat_key] > linea if "over" in pl else jug[stat_key] < linea


# ══════════════════════════ API ══════════════════════════
def resolver_todo(progreso_cb=None):
    """Resuelve TODOS los picks pendientes (MLB + NBA) contra box scores reales."""
    pendientes = pick_memory.pendientes()
    n_mlb = _resolver_mlb(pendientes, progreso_cb)
    n_nba = _resolver_nba(pendientes, progreso_cb)
    return {"mlb": n_mlb, "nba": n_nba, "total": n_mlb + n_nba}
