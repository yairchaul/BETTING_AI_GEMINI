# -*- coding: utf-8 -*-
"""
ESPN FÚTBOL - Módulo con estadísticas de equipos (últimos 5 partidos)
"""

import requests
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class GestorLigasUniversal:
    """Gestor de ligas que obtiene datos desde API de ESPN con estadísticas"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
        }
        # El scraper de córners se inicializa en main_vision_completo.py y se pasa aquí
        self.corners_scraper = None 
        self._ligas_cache = None
    
    def obtener_ligas(self):
        """Obtiene todas las ligas desde API de ESPN"""
        if self._ligas_cache:
            return self._ligas_cache
        
        try:
            api_url = "https://site.api.espn.com/apis/site/v2/sports/soccer/all/leagues"
            response = requests.get(api_url, headers=self.headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                ligas = []
                for league in data.get('leagues', []):
                    name = league.get('name') or league.get('displayName')
                    if name:
                        ligas.append(name)
                
                if ligas:
                    self._ligas_cache = ligas
                    return ligas
        except Exception as e:
            logger.error(f"Error obteniendo ligas: {e}")
        
        # Fallback con todas las ligas soportadas
        self._ligas_cache = [
            # Internacionales (prioridad alta — Mundial 2026 empieza 12 Jun 2026)
            "Copa del Mundo", "Copa America", "EURO",
            "Champions League", "Europa League", "Nations League",
            "Copa Libertadores", "Copa Sudamericana",
            "CONCACAF Nations League", "Gold Cup",
            # Europa
            "Premier League", "La Liga", "Serie A", "Bundesliga", "Ligue 1",
            "Eredivisie", "Primeira Liga", "Scottish Premiership", "Süper Lig",
            # Americas
            "Liga MX", "MLS", "Argentine Liga Profesional", "Brazilian Serie A",
            "Chilean Primera Division", "Colombian Primera A", "Peruvian Liga 1",
            "Uruguayan Primera", "Ecuadorian Liga Pro", "Paraguayan Apertura",
            # Asia / Oceanía
            "A-League", "J1 League", "K League 1", "Saudi Pro League",
        ]
        return self._ligas_cache
    
    def obtener_estadisticas_equipo(self, equipo_nombre, liga_id):
        """Obtiene últimos 5 partidos de un equipo"""
        try:
            # Buscar ID del equipo
            api_url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{liga_id}/teams"
            response = requests.get(api_url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                for team in data.get('teams', []):
                    if equipo_nombre.lower() in team.get('displayName', '').lower():
                        team_id = team.get('id')
                        if team_id:
                            # Obtener resultados del equipo
                            schedule_url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{liga_id}/teams/{team_id}/schedule"
                            schedule_resp = requests.get(schedule_url, headers=self.headers, timeout=10)
                            
                            if schedule_resp.status_code == 200:
                                schedule_data = schedule_resp.json()
                                events = schedule_data.get('events', [])[:5]
                                
                                resultados = []
                                goles = []
                                for event in events:
                                    competitions = event.get('competitions', [])
                                    for comp in competitions:
                                        competitors = comp.get('competitors', [])
                                        for c in competitors:
                                            if c.get('team', {}).get('id') == team_id:
                                                score = c.get('score', '0')
                                                goles.append(int(score) if score.isdigit() else 0)
                                                resultados.append(c.get('winner', False))
                                
                                if resultados:
                                    return {
                                        'goles': goles,
                                        'promedio': sum(goles) / len(goles) if goles else 0,
                                        'victorias': sum(resultados),
                                        'partidos': len(resultados)
                                    }
            return None
        except Exception as e:
            logger.debug(f"Error obteniendo estadísticas de {equipo_nombre}: {e}")
            return None
    
    def obtener_partidos(self, liga_nombre, fecha=None):
        """
        Obtiene partidos de una liga específica. Si no hay partidos para la fecha
        dada (o para hoy), busca en los próximos 7 días.
        """
        # Mapeo de ligas a IDs ESPN
        ligas_ids = {
            # ── Europa ────────────────────────────────────────────────────────
            "Premier League":       "eng.1",
            "La Liga":              "esp.1",
            "Serie A":              "ita.1",
            "Bundesliga":           "ger.1",
            "Ligue 1":              "fra.1",
            "Eredivisie":           "ned.1",
            "Primeira Liga":        "por.1",
            "Scottish Premiership": "sco.1",
            "Süper Lig":            "tur.1",
            "Brasileirao Serie A":  "bra.1",  # alias
            # ── Americas ──────────────────────────────────────────────────────
            "Liga MX":              "mex.1",
            "MLS":                  "usa.1",
            "Argentine Liga Profesional": "arg.1",
            "Brazilian Serie A":    "bra.1",
            "Chilean Primera Division": "chi.1",
            "Colombian Primera A":  "col.1",
            "Peruvian Liga 1":      "per.1",
            "Uruguayan Primera":    "uru.1",
            "Ecuadorian Liga Pro":  "ecu.1",
            "Paraguayan Apertura":  "par.1",
            "Bolivian Liga":        "bol.1",
            "Venezuelan Primera":   "ven.1",
            # ── Asia / Oceanía ────────────────────────────────────────────────
            "A-League":             "aus.1",
            "J1 League":            "jpn.1",
            "K League 1":           "kor.1",
            "Saudi Pro League":     "sau.1",
            # ── Torneos internacionales ───────────────────────────────────────
            "Copa del Mundo":       "fifa.world",    # FIFA World Cup 2026
            "Copa America":         "conmebol.america",
            "EURO":                 "uefa.euro",
            "Champions League":     "uefa.champions",
            "Europa League":        "uefa.europa",
            "Nations League":       "uefa.nations",
            "Copa Libertadores":    "conmebol.libertadores",
            "Copa Sudamericana":    "conmebol.sudamericana",
            "CONCACAF Nations League": "concacaf.nations.league",
            "Gold Cup":             "concacaf.gold",
            "AFC Asian Cup":        "afc.asian.qual",
        }
        
        league_id = ligas_ids.get(liga_nombre)
        if not league_id:
            return []
        
        todos_partidos = []  # acumulador de TODOS los días (hoy + próximos)
        # Bucle para acumular partidos de hoy + próximos 7 días
        for i in range(8): # 0 a 7 (hoy + 7 días)
            if fecha:
                current_date_str = fecha # Si se especifica una fecha, solo buscar esa
                search_range = 1
            else:
                current_date = datetime.now() + timedelta(days=i)
                current_date_str = current_date.strftime("%Y%m%d")
                search_range = 8

            try:
                api_url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_id}/scoreboard?dates={current_date_str}"
                response = requests.get(api_url, headers=self.headers, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    partidos = []
                    
                    for event in data.get('events', []):
                        for comp in event.get('competitions', []):
                            competitors = comp.get('competitors', [])
                            if len(competitors) >= 2:
                                local_data = competitors[0].get('team', {})
                                visitante_data = competitors[1].get('team', {})
                                
                                # Extraer logos
                                local_logo = local_data.get('logo', '')
                                visitante_logo = visitante_data.get('logo', '')
                                
                                # Extraer récords y rachas
                                local_record_obj = competitors[0].get('records', [{}])[0]
                                visitante_record_obj = competitors[1].get('records', [{}])[0]
                                local_record = local_record_obj.get('summary', '0-0-0') # Soccer often has W-L-D
                                visitante_record = visitante_record_obj.get('summary', '0-0-0')
                                local_streak = local_record_obj.get('streak', {}).get('abbreviation', '')
                                visitante_streak = visitante_record_obj.get('streak', {}).get('abbreviation', '')

                                local = local_data.get('displayName', '')
                                visitante = visitante_data.get('displayName', '')
                                
                                # Obtener estadísticas de ambos equipos
                                stats_local = self.obtener_estadisticas_equipo(local, league_id)
                                stats_visitante = self.obtener_estadisticas_equipo(visitante, league_id)

                                # Extracción de cuotas (Betting Odds)
                                odds_data = {}
                                if comp.get('odds'):
                                    raw_odds = comp.get('odds')[0]
                                    odds_data = {
                                        'moneyline': {
                                            'home': raw_odds.get('homeTeamOdds', {}).get('american', 'N/A'),
                                            'away': raw_odds.get('awayTeamOdds', {}).get('american', 'N/A'),
                                            'draw': raw_odds.get('drawOdds', {}).get('american', 'N/A')
                                        },
                                        'over_under': raw_odds.get('overUnder', 'N/A'),
                                        'detalles': raw_odds.get('details', 'N/A')
                                    }

                                # Obtener datos de córners (simulados por ahora)
                                corners_data = {}
                                if self.corners_scraper: # Assuming this is in scrapers/
                                    corners_data = self.corners_scraper.get_corners_data(local, visitante, league_id) # Usar el nuevo scraper

                                # Detectar fase del torneo (grupo, octavos, semifinal, final)
                                fase = ""
                                notas = comp.get("notes", [])
                                if notas:
                                    fase = notas[0].get("headline", "")

                                partidos.append({
                                    "local":            local,
                                    "visitante":        visitante,
                                    "home":             local,
                                    "away":             visitante,
                                    "liga":             liga_nombre,
                                    "status":           event.get('status', {}).get('type', {}).get('state', 'pre'),
                                    "completado":       bool(event.get('status', {}).get('type', {}).get('completed', False)),
                                    "fase":             fase,
                                    "es_torneo":        liga_nombre in (
                                        "Copa del Mundo", "Copa America", "EURO",
                                        "Champions League", "Europa League",
                                        "Copa Libertadores", "Copa Sudamericana",
                                        "Gold Cup", "CONCACAF Nations League",
                                    ),
                                    "stats_local":      stats_local,
                                    "stats_visitante":  stats_visitante,
                                    "odds":             odds_data,
                                    "fecha_partido":    event.get("date", "")[:10],
                                    "fecha_hora":       event.get("date", ""),  # ISO completo (UTC) → CDMX en el visual
                                    "local_logo":       local_logo,
                                    "visitante_logo":   visitante_logo,
                                    "local_record":     local_record,
                                    "visitante_record": visitante_record,
                                    "local_streak":     local_streak,
                                    "visitante_streak": visitante_streak,
                                    **corners_data,
                                })

                    # Acumular los partidos de ESTE día (NO salir al primero):
                    # queremos hoy + próximos días, no solo el primer día con juegos.
                    if partidos:
                        logger.info(f"{len(partidos)} partidos de {liga_nombre} para {current_date_str}")
                        todos_partidos.extend(partidos)
            except Exception as e:
                logger.error(f"Error obteniendo partidos para {liga_nombre} en fecha {current_date_str}: {e}")
            
            if i >= search_range - 1:
                break # Salir si ya buscamos el rango completo
        
        if not todos_partidos:
            logger.warning(f"No se encontraron partidos para {liga_nombre} en los próximos 7 días.")
        else:
            logger.info(f"TOTAL {liga_nombre}: {len(todos_partidos)} partidos (hoy + próximos días)")
        return todos_partidos


class ESPN_FUTBOL:
    def __init__(self):
        self.gestor = GestorLigasUniversal()
    
    def get_available_leagues(self):
        """Retorna todas las ligas disponibles"""
        return self.gestor.obtener_ligas()
    
    def get_games(self, liga, fecha=None):
        """Obtiene partidos de una liga específica con estadísticas"""
        return self.gestor.obtener_partidos(liga, fecha=fecha)