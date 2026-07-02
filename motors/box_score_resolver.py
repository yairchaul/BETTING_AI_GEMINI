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


def _estado_de(res):
    """Mapea el resultado de calificar un pick a estado de pick_memory.
    True→ganado, False→perdido, "push"→push (línea exacta: se devuelve la apuesta,
    NO cuenta como pérdida en el win-rate)."""
    if res == "push":
        return "push"
    return "ganado" if res else "perdido"


def _grade_linea(valor, linea, es_over):
    """Califica OVER/UNDER contra una línea. Empate exacto (línea entera) = push."""
    if valor == linea:
        return "push"
    return valor > linea if es_over else valor < linea


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
                    res = _grade_linea(bat["tb"], linea, "over" in pl)
            elif mercado == "TOTAL" or "over" in pl or "under" in pl:
                linea = _num_en(pick_txt) or 8.5
                res = _grade_linea(total, linea, "over" in pl)
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
                    res = _grade_linea(pit["k"], linea, "over" in pl)

            if res is not None:
                pick_memory.resolver(p["id"], _estado_de(res), marcador)
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
                res = _grade_linea(total, linea, True)
            elif "TOTAL" in mercado and "UNDER" in pick_txt.upper():
                linea = _num_en(pick_txt) or 225.5
                res = _grade_linea(total, linea, False)
            elif "PROP" in mercado:
                if j["id"] not in box_cache:
                    box_cache[j["id"]] = _nba_boxscore(j["id"])
                res = _grade_prop_nba(pick_txt, box_cache[j["id"]])

            if res is not None:
                pick_memory.resolver(p["id"], _estado_de(res), marcador)
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
    return _grade_linea(jug[stat_key], linea, "over" in pl)


# ══════════════════════════ UFC ══════════════════════════
def _grade_ufc(mercado, pick_txt, pelea, metodo=None):
    """Califica un pick UFC contra el resultado real. True=ganó, False=perdió,
    None=no se pudo determinar. Función PURA (testeable sin red).

    pelea: dict con ganador_real, round_final, rounds_programados.
    metodo: 'KO/TKO' | 'Sumisión' | 'Decisión' | None (se pide aparte solo si hace falta).
    """
    mercado = (mercado or "").upper()
    pl = (pick_txt or "").lower()
    ganador = _norm(pelea.get("ganador_real", ""))
    rfinal = pelea.get("round_final", 0) or 0
    rprog = pelea.get("rounds_programados", 3) or 3

    # ¿Va a la distancia? (DISTANCIA / "llega a decisión")
    if "DISTANCIA" in mercado or "decision" in pl or "decisión" in pl or "distancia" in pl:
        llega = (metodo == "Decisión") if metodo else (rfinal >= rprog)
        quiere_no = ("no llega" in pl) or ("termina antes" in pl)
        return (not llega) if quiere_no else llega
    # Total de rounds (OVER/UNDER X.5)
    if "ROUNDS" in mercado or "round" in pl or "asalto" in pl:
        linea = _num_en(pl) or 1.5
        return _grade_linea(rfinal, linea, "over" in pl)
    # Gana por KO/TKO
    if "KO" in mercado or "ko" in pl:
        return (ganador in _norm(pick_txt)) and (metodo == "KO/TKO")
    # Gana por Sumisión
    if "SUB" in mercado or "sumis" in pl:
        return (ganador in _norm(pick_txt)) and (metodo == "Sumisión")
    # Ganador (moneyline)
    if "GANADOR" in mercado or pl.startswith("gana") or "gana " in pl:
        return ganador in _norm(pick_txt)
    return None


def _match_pelea_ufc(evento, peleas):
    """Empareja 'Fighter A vs Fighter B' con una pelea real (por apellido, cualquier orden)."""
    partes = re.split(r"\s+vs\.?\s+", evento or "", flags=re.I)
    if len(partes) != 2:
        return None
    a, b = _norm(partes[0]), _norm(partes[1])

    def _coincide(x, y):
        if not x or not y:
            return False
        return x in y or y in x or x.split()[-1] == y.split()[-1]

    for pel in peleas:
        n1, n2 = _norm(pel.get("p1_nombre", "")), _norm(pel.get("p2_nombre", ""))
        if (_coincide(a, n1) and _coincide(b, n2)) or (_coincide(a, n2) and _coincide(b, n1)):
            return pel
    return None


def _resolver_ufc(pendientes, progreso_cb=None):
    """Resuelve picks UFC pendientes contra resultados reales de ESPN MMA
    (reutiliza motors.ufc_backtester). Cierra el ciclo de aprendizaje de UFC."""
    ufc_picks = [p for p in pendientes if (p.get("deporte") or "").upper() == "UFC"]
    if not ufc_picks:
        return 0
    try:
        from motors.ufc_backtester import UFCBacktester
        bt = UFCBacktester()
        fechas = [p.get("fecha_evento") or p.get("fecha") for p in ufc_picks
                  if (p.get("fecha_evento") or p.get("fecha"))]
        dias = 120
        if fechas:
            try:
                mas_viejo = min(datetime.strptime(f[:10], "%Y-%m-%d") for f in fechas)
                dias = max(7, min(365, (datetime.now() - mas_viejo).days + 3))
            except Exception:
                pass
        peleas = bt.obtener_peleas_historicas(dias=dias)
    except Exception as e:
        if progreso_cb:
            progreso_cb(f"UFC: no se pudieron traer resultados ({e})")
        return 0
    if not peleas:
        return 0

    metodo_cache = {}

    def _metodo(pel):
        key = pel.get("comp_id")
        if key not in metodo_cache:
            try:
                metodo_cache[key] = bt._obtener_metodo(pel)
            except Exception:
                metodo_cache[key] = None
        return metodo_cache[key]

    n = 0
    for p in ufc_picks:
        pel = _match_pelea_ufc(p.get("evento", ""), peleas)
        if not pel:
            continue
        mercado = (p.get("mercado") or "").upper()
        # El método solo se pide (1 llamada extra) para los mercados que lo necesitan
        met = _metodo(pel) if any(k in mercado or k in p.get("pick", "").lower()
                                  for k in ("DISTANCIA", "KO", "SUB", "decis", "sumis", "ko")) else None
        res = _grade_ufc(mercado, p.get("pick", ""), pel, met)
        if res is not None:
            marcador = f'Gana {pel.get("ganador_real","?")} (R{pel.get("round_final",0)}, {met or "?"})'
            pick_memory.resolver(p["id"], _estado_de(res), marcador)
            n += 1
    if progreso_cb:
        progreso_cb(f"UFC: {n} resueltos")
    return n


# ══════════════════════════ FÚTBOL ══════════════════════════
def _resolver_futbol(pendientes, progreso_cb=None):
    """Resuelve picks de fútbol pendientes contra resultados reales de ESPN.
    Antes esta lógica vivía suelta en main_vision_completo; ahora es parte del
    resolver unificado para que el ciclo de aprendizaje cierre TODO de una vez."""
    soccer = [p for p in pendientes if (p.get("deporte") or "").upper() == "SOCCER"]
    if not soccer:
        return 0
    try:
        from espn_futbol import ESPN_FUTBOL
        from motors.futbol_backtest_real import _grade_pick, LIGAS_DEFAULT
    except Exception as e:
        if progreso_cb:
            progreso_cb(f"Fútbol: no se pudo importar el resolver ({e})")
        return 0

    scraper = ESPN_FUTBOL()
    resultados = {}   # "home|away" normalizado → (gl, gv, local_real, visit_real)
    for liga in LIGAS_DEFAULT:
        try:
            for p in scraper.gestor.obtener_partidos(liga, dias_atras=5):
                if p.get("completado") and p.get("goles_local") is not None:
                    h = (p.get("home") or p.get("local", "")).lower().strip()
                    a = (p.get("away") or p.get("visitante", "")).lower().strip()
                    resultados[f"{h}|{a}"] = (int(p["goles_local"]), int(p["goles_visitante"]),
                                              p.get("home", ""), p.get("away", ""))
        except Exception:
            continue

    n = 0
    for pk in soccer:
        evento = pk.get("evento", "")
        if " vs " not in evento:
            continue
        local, visitante = [x.strip() for x in evento.split(" vs ", 1)]
        clave = f"{local.lower()}|{visitante.lower()}"
        if clave not in resultados:
            continue
        gl, gv, loc_real, vis_real = resultados[clave]
        _, acierto = _grade_pick(pk.get("pick", ""), gl, gv, loc_real, vis_real)
        if acierto is None:
            continue
        pick_memory.resolver(pk["id"], "ganado" if acierto else "perdido", f"{gl}-{gv}")
        n += 1
    if progreso_cb:
        progreso_cb(f"Fútbol: {n} resueltos")
    return n


# ══════════════════════════ API ══════════════════════════
def resolver_todo(progreso_cb=None):
    """Resolver UNIFICADO: cierra el ciclo de aprendizaje COMPLETO de una sola
    llamada — picks de MLB + NBA + UFC + FÚTBOL contra resultados reales, y luego
    los PARLAYS cuyas legs ya quedaron resueltas. Una sola fuente de verdad."""
    pendientes = pick_memory.pendientes()
    n_mlb = _resolver_mlb(pendientes, progreso_cb)
    n_nba = _resolver_nba(pendientes, progreso_cb)
    n_ufc = _resolver_ufc(pendientes, progreso_cb)
    n_soccer = _resolver_futbol(pendientes, progreso_cb)
    # Cerrar también los parlays cuyas legs ya se resolvieron (no usa red).
    n_parlays = 0
    try:
        from motors.parlay_brain import resolver_parlays_pendientes
        n_parlays = resolver_parlays_pendientes() or 0
        if progreso_cb:
            progreso_cb(f"Parlays: {n_parlays} resueltos")
    except Exception as _e:
        if progreso_cb:
            progreso_cb(f"Parlays: {_e}")
    return {"mlb": n_mlb, "nba": n_nba, "ufc": n_ufc, "soccer": n_soccer,
            "parlays": n_parlays, "total": n_mlb + n_nba + n_ufc + n_soccer}
