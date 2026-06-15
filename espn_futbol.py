# -*- coding: utf-8 -*-
"""
ESPN FÚTBOL V25 — Ligas + Torneos (Mundial 2026, EURO, Copa América)
Extrae logos, cuotas, récords, fecha y fase directamente del scoreboard.
"""

import requests
import logging

logger = logging.getLogger(__name__)

# Mapa liga/torneo → código ESPN. Los torneos van marcados con es_torneo=True.
LIGAS_IDS = {
    # ── Torneos internacionales (prioridad Mundial 2026) ──
    "FIFA World Cup": ("fifa.world", True),
    "World Cup Qualifying - UEFA": ("fifa.worldq.uefa", True),
    "World Cup Qualifying - CONMEBOL": ("fifa.worldq.conmebol", True),
    "World Cup Qualifying - CONCACAF": ("fifa.worldq.concacaf", True),
    "World Cup Qualifying - AFC": ("fifa.worldq.afc", True),
    "World Cup Qualifying - CAF": ("fifa.worldq.caf", True),
    "UEFA Champions League": ("uefa.champions", True),
    "UEFA Europa League": ("uefa.europa", True),
    "UEFA Europa Conference League": ("uefa.europa.conf", True),
    "UEFA European Championship": ("uefa.euro", True),
    "UEFA Nations League": ("uefa.nations", True),
    "Copa América": ("conmebol.america", True),
    "Copa Libertadores": ("conmebol.libertadores", True),
    "Copa Sudamericana": ("conmebol.sudamericana", True),
    "Concacaf Gold Cup": ("concacaf.gold", True),
    "Concacaf Champions Cup": ("concacaf.champions", True),
    "AFC Champions League": ("afc.champions", True),
    "FIFA Club World Cup": ("fifa.cwc", True),
    "International Friendly": ("fifa.friendly", True),
    # ── Copas nacionales ──
    "FA Cup": ("eng.fa", True),
    "Copa del Rey": ("esp.copa_del_rey", True),
    "Coppa Italia": ("ita.coppa_italia", True),
    "DFB Pokal": ("ger.dfb_pokal", True),
    "Coupe de France": ("fra.coupe_de_france", True),
    # ── Ligas europeas top ──
    "Premier League": ("eng.1", False),
    "Championship": ("eng.2", False),
    "League One": ("eng.3", False),
    "La Liga": ("esp.1", False),
    "La Liga 2": ("esp.2", False),
    "Serie A": ("ita.1", False),
    "Serie B": ("ita.2", False),
    "Bundesliga": ("ger.1", False),
    "2. Bundesliga": ("ger.2", False),
    "Ligue 1": ("fra.1", False),
    "Ligue 2": ("fra.2", False),
    "Eredivisie": ("ned.1", False),
    "Primeira Liga": ("por.1", False),
    "Scottish Premiership": ("sco.1", False),
    "Belgian Pro League": ("bel.1", False),
    "Turkish Super Lig": ("tur.1", False),
    "Greek Super League": ("gre.1", False),
    "Austrian Bundesliga": ("aut.1", False),
    "Swiss Super League": ("sui.1", False),
    "Danish Superliga": ("den.1", False),
    "Norwegian Eliteserien": ("nor.1", False),
    "Swedish Allsvenskan": ("swe.1", False),
    "Russian Premier League": ("rus.1", False),
    "Ukrainian Premier League": ("ukr.1", False),
    # ── Américas ──
    "Liga MX": ("mex.1", False),
    "MLS": ("usa.1", False),
    "Brazilian Serie A": ("bra.1", False),
    "Argentine Liga Profesional": ("arg.1", False),
    "Colombian Primera A": ("col.1", False),
    "Chilean Primera Division": ("chi.1", False),
    "Uruguayan Primera Division": ("uru.1", False),
    "Ecuadorian Serie A": ("ecu.1", False),
    "Paraguayan Primera Division": ("par.1", False),
    "Peruvian Primera Division": ("per.1", False),
    # ── Asia / Oceanía ──
    "Saudi Pro League": ("ksa.1", False),
    "J1 League": ("jpn.1", False),
    "K League 1": ("kor.1", False),
    "Chinese Super League": ("chn.1", False),
    "A-League": ("aus.1", False),
    "Qatar Stars League": ("qat.1", False),
    "UAE Pro League": ("are.1", False),
}


class GestorLigasUniversal:
    """Obtiene ligas y partidos desde la API de ESPN."""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
        }
        self.corners_scraper = None
        self._ligas_cache = None

    def obtener_ligas(self):
        """Todas las ligas + torneos disponibles (orden del mapa: torneos primero)."""
        if self._ligas_cache:
            return self._ligas_cache
        self._ligas_cache = list(LIGAS_IDS.keys())
        return self._ligas_cache

    def _parse_odds(self, comp):
        """Extrae moneyline (home/draw/away), línea O/U y detalle del scoreboard.

        Fallback: si home/away vienen vacíos (común en torneos), parsea el campo
        'details' (ej. 'CAN -125') y lo asigna al equipo cuya abreviatura coincide.
        """
        odds_out = {"moneyline": {}, "over_under": "N/A", "detalles": ""}
        odds_list = comp.get('odds', []) or []
        o = odds_list[0] if odds_list else None
        if not isinstance(o, dict):
            return odds_out
        detalles = o.get('details', '') or ''
        odds_out["detalles"] = detalles
        if o.get('overUnder') is not None:
            odds_out["over_under"] = o.get('overUnder')

        home_ml = (o.get('homeTeamOdds', {}) or {}).get('moneyLine')
        away_ml = (o.get('awayTeamOdds', {}) or {}).get('moneyLine')
        draw_ml = o.get('drawOdds', {}).get('moneyLine') if isinstance(o.get('drawOdds'), dict) else None

        # Fallback: parsear 'details' (ABBR ±NNN) y asignar al equipo correcto
        if home_ml is None and away_ml is None and detalles:
            import re as _re
            m = _re.search(r'([A-Z]{2,4})\s*([+-]\d+)', detalles)
            if m:
                abbr_fav, ml_fav = m.group(1), int(m.group(2))
                competitors = comp.get('competitors', [])
                home_c = next((c for c in competitors if c.get('homeAway') == 'home'), None)
                away_c = next((c for c in competitors if c.get('homeAway') == 'away'), None)
                home_abbr = (home_c or {}).get('team', {}).get('abbreviation', '')
                away_abbr = (away_c or {}).get('team', {}).get('abbreviation', '')
                # Estimar el momio del rival (signo opuesto, ligeramente mayor)
                ml_dog = abs(ml_fav) + 20 if ml_fav < 0 else -(ml_fav + 20)
                if abbr_fav == home_abbr:
                    home_ml, away_ml = ml_fav, ml_dog
                elif abbr_fav == away_abbr:
                    away_ml, home_ml = ml_fav, ml_dog

        odds_out["moneyline"] = {
            "home": home_ml if home_ml is not None else 'N/A',
            "draw": draw_ml if draw_ml is not None else 'N/A',
            "away": away_ml if away_ml is not None else 'N/A',
        }
        return odds_out

    def _record_total(self, competitor):
        """Récord total 'G-E-P' del competidor (si ESPN lo provee)."""
        for r in competitor.get('records', []) or []:
            if r.get('type') == 'total' or r.get('name') == 'overall':
                return r.get('summary', '0-0-0')
        recs = competitor.get('records', [])
        if recs and isinstance(recs[0], dict):
            return recs[0].get('summary', '0-0-0')
        return '0-0-0'

    def obtener_partidos(self, liga_nombre, dias_atras=3):
        """Partidos de una liga/torneo: últimos `dias_atras` días + próximos.

        ESPN no soporta rangos de fecha en fútbol, así que se consulta el
        scoreboard por defecto (próximos) + cada día pasado por separado.
        Incluye marcador y estado (FT/EN VIVO/programado).
        """
        from datetime import datetime, timedelta
        info = LIGAS_IDS.get(liga_nombre)
        if not info:
            logger.warning(f"Liga sin código ESPN: {liga_nombre}")
            return []
        league_id, es_torneo = info

        # URLs a consultar: scoreboard por defecto + cada día pasado
        urls = [f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_id}/scoreboard"]
        for d in range(1, dias_atras + 1):
            fecha = (datetime.now() - timedelta(days=d)).strftime('%Y%m%d')
            urls.append(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_id}/scoreboard?dates={fecha}")

        partidos = []
        vistos = set()  # dedupe por id de evento

        for api_url in urls:
            try:
                response = requests.get(api_url, headers=self.headers, timeout=12)
                if response.status_code != 200:
                    continue
                data = response.json()
            except Exception:
                continue

            for event in data.get('events', []):
              try:
                ev_id = event.get('id')
                if ev_id in vistos:
                    continue
                vistos.add(ev_id)
                fase = ''
                # La fase del torneo suele venir en season.type o en notes
                if es_torneo:
                    fase = (event.get('season', {}) or {}).get('slug', '') or ''
                    notes = event.get('competitions', [{}])[0].get('notes', [])
                    if notes and isinstance(notes, list):
                        fase = notes[0].get('headline', fase) or fase

                for comp in event.get('competitions', []):
                    competitors = comp.get('competitors', [])
                    if len(competitors) < 2:
                        continue

                    # ESPN: competitors[0] suele ser home, [1] away (homeAway lo confirma)
                    home_c = next((c for c in competitors if c.get('homeAway') == 'home'), competitors[0])
                    away_c = next((c for c in competitors if c.get('homeAway') == 'away'), competitors[1])

                    home_team = home_c.get('team', {})
                    away_team = away_c.get('team', {})

                    # Estado y marcador (defensivo: status puede venir None)
                    status_obj = (comp.get('status') or {}).get('type') or {}
                    estado = status_obj.get('description', 'programado')
                    completado = status_obj.get('completed', False)
                    en_vivo = status_obj.get('state', '') == 'in'
                    goles_local = home_c.get('score')
                    goles_visit = away_c.get('score')
                    marcador = ''
                    if goles_local is not None and goles_visit is not None and (completado or en_vivo):
                        marcador = f"{goles_local}-{goles_visit}"

                    partidos.append({
                        'home': home_team.get('displayName', ''),
                        'away': away_team.get('displayName', ''),
                        'local': home_team.get('displayName', ''),
                        'visitante': away_team.get('displayName', ''),
                        'local_id': home_team.get('id', ''),
                        'visitante_id': away_team.get('id', ''),
                        'liga': liga_nombre,
                        'liga_code': league_id,
                        'local_logo': home_team.get('logo', ''),
                        'visitante_logo': away_team.get('logo', ''),
                        'local_record': self._record_total(home_c),
                        'visitante_record': self._record_total(away_c),
                        'odds': self._parse_odds(comp),
                        'fecha_partido': event.get('date', '')[:16].replace('T', ' '),
                        'venue': (comp.get('venue', {}) or {}).get('fullName', ''),
                        'status': estado,
                        'completado': completado,
                        'en_vivo': en_vivo,
                        'marcador': marcador,
                        'goles_local': goles_local,
                        'goles_visitante': goles_visit,
                        'es_torneo': es_torneo,
                        'fase': fase,
                    })
              except Exception as _ev_err:
                logger.debug(f"Evento fútbol omitido ({liga_nombre}): {_ev_err}")
                continue

        # Ordenar: en vivo → próximos → finalizados
        def _orden(p):
            if p.get('en_vivo'):
                return 0
            if not p.get('completado'):
                return 1
            return 2
        partidos.sort(key=_orden)
        logger.info(f"⚽ {liga_nombre}: {len(partidos)} partidos (últimos {dias_atras}d + próximos)")
        return partidos


    def obtener_ultimos_5(self, team_id, league_id=None):
        """Últimos 5 partidos JUGADOS de un equipo (goles favor/contra).

        Usa el código 'all' que agrega TODAS las competiciones — necesario para
        selecciones nacionales (juegan amistosos/eliminatorias, no liga).
        """
        if not team_id:
            return []
        try:
            url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/all/teams/{team_id}/schedule"
            r = requests.get(url, headers=self.headers, timeout=12)
            if r.status_code != 200:
                return []
            eventos = r.json().get('events', [])
            jugados = []
            for e in eventos:
                comp = e.get('competitions', [{}])[0]
                comps = comp.get('competitors', [])
                if len(comps) != 2:
                    continue
                mio = next((c for c in comps if str(c.get('team', {}).get('id')) == str(team_id)), None)
                rival = next((c for c in comps if str(c.get('team', {}).get('id')) != str(team_id)), None)
                if not mio or not rival:
                    continue
                gf = mio.get('score', {}).get('value')
                gc = rival.get('score', {}).get('value')
                if gf is None or gc is None:
                    continue
                jugados.append({'fecha': e.get('date', '')[:10], 'favor': int(gf), 'contra': int(gc)})
            # Más recientes primero
            jugados.sort(key=lambda x: x['fecha'], reverse=True)
            return jugados[:5]
        except Exception as e:
            logger.debug(f"Error últimos 5 de {team_id}: {e}")
            return []

    def poblar_historial(self, partidos, progreso_cb=None):
        """Guarda en historial_equipos los últimos 5 de cada equipo (idempotente)."""
        import sqlite3
        equipos = {}
        for p in partidos:
            if p.get('local_id'):
                equipos[p['local']] = (p['local_id'], p.get('liga_code'))
            if p.get('visitante_id'):
                equipos[p['visitante']] = (p['visitante_id'], p.get('liga_code'))

        total = len(equipos)
        poblados = 0
        for i, (nombre, (tid, lcode)) in enumerate(equipos.items()):
            if progreso_cb:
                progreso_cb(i + 1, total, nombre)
            ultimos = self.obtener_ultimos_5(tid, lcode)
            if not ultimos:
                continue
            try:
                conn = sqlite3.connect("data/betting_stats.db", timeout=10)
                cur = conn.cursor()
                # Borrar historial previo de soccer de este equipo (evita duplicados)
                cur.execute("DELETE FROM historial_equipos WHERE nombre_equipo = ? AND deporte = 'soccer'", (nombre,))
                for u in ultimos:
                    cur.execute(
                        "INSERT INTO historial_equipos (nombre_equipo, deporte, puntos_favor, puntos_ht, puntos_contra, fecha) VALUES (?,?,?,?,?,?)",
                        (nombre, 'soccer', u['favor'], 0, u['contra'], u['fecha']))
                conn.commit()
                conn.close()
                poblados += 1
            except Exception as e:
                logger.warning(f"No se pudo poblar historial de {nombre}: {e}")
        return poblados


class ESPN_FUTBOL:
    def __init__(self):
        self.gestor = GestorLigasUniversal()

    def get_available_leagues(self):
        return self.gestor.obtener_ligas()

    def get_games(self, liga):
        return self.gestor.obtener_partidos(liga)

    def obtener_ultimos_5(self, team_id, league_id):
        return self.gestor.obtener_ultimos_5(team_id, league_id)

    def poblar_historial(self, partidos, progreso_cb=None):
        return self.gestor.poblar_historial(partidos, progreso_cb)
