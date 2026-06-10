# -*- coding: utf-8 -*-
"""
ESPN FÚTBOL - Módulo con estadísticas de equipos (últimos 5 partidos)
"""

import requests
import logging
from datetime import datetime

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
        
        # Fallback: ligas populares (dinámico, se actualizará cuando API funcione)
        self._ligas_cache = [
            "Premier League", "La Liga", "Serie A", "Bundesliga", "Ligue 1",
            "Liga MX", "MLS", "Eredivisie", "Primeira Liga", "Scottish Premiership",
            "A-League", "J1 League", "K League 1", "Saudi Pro League",
            "Argentine Liga Profesional", "Brazilian Serie A", "Chilean Primera Division"
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
    
    def obtener_partidos(self, liga_nombre):
        """Obtiene partidos de una liga específica con estadísticas"""
        # Mapeo de ligas a IDs
        ligas_ids = {
            "Premier League": "eng.1",
            "La Liga": "esp.1",
            "Serie A": "ita.1",
            "Bundesliga": "ger.1",
            "Ligue 1": "fra.1",
            "Liga MX": "mex.1",
            "MLS": "usa.1",
            "Eredivisie": "ned.1",
            "Primeira Liga": "por.1",
            "Scottish Premiership": "sco.1",
            "A-League": "aus.1",
            "J1 League": "jpn.1",
            "K League 1": "kor.1",
        }
        
        league_id = ligas_ids.get(liga_nombre)
        if not league_id:
            return []
        
        try:
            api_url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_id}/scoreboard"
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
                            
                            local = local_data.get('displayName', '')
                            visitante = visitante_data.get('displayName', '')
                            
                            # Obtener estadísticas de ambos equipos
                            stats_local = self.obtener_estadisticas_equipo(local, league_id)
                            stats_visitante = self.obtener_estadisticas_equipo(visitante, league_id)

                            # Obtener datos de córners (simulados por ahora)
                            corners_data = {}
                            if self.corners_scraper:
                                corners_data = self.corners_scraper.get_corners_data(local, visitante, league_id) # Usar el nuevo scraper


                            partidos.append({
                                'home': local,
                                'away': visitante,
                                'liga': liga_nombre,
                                'status': 'programado',
                                'stats_local': stats_local,
                                'stats_visitante': stats_visitante,
                                **corners_data # Añadir datos de córners al partido
                            })

                
                return partidos
        except Exception as e:
            logger.error(f"Error obteniendo partidos: {e}")
        
        return []


class ESPN_FUTBOL:
    def __init__(self):
        self.gestor = GestorLigasUniversal()
    
    def get_available_leagues(self):
        """Retorna todas las ligas disponibles"""
        return self.gestor.obtener_ligas()
    
    def get_games(self, liga):
        """Obtiene partidos de una liga específica con estadísticas"""
        return self.gestor.obtener_partidos(liga)
