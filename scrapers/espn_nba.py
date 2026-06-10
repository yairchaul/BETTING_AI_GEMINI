"""
ESPN NBA - Extrae TODOS los datos necesarios para la imagen
"""
import requests
import re

try:
    from balldontlie_client import balldontlie
except ImportError:
    balldontlie = None

class ESPN_NBA:
    def __init__(self):
        self.url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
        self.base_team_url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/"
        self.headers = {'User-Agent': 'Mozilla/5.0'}

    def get_player_props_auto(self, team_id):
        """Extrae automáticamente props de jugadores usando Balldontlie API real"""
        if not balldontlie:
            return []
            
        props_analizadas = []
        try:
            players_data = balldontlie.get_players(team_id=team_id)
            for player in players_data.get('data', [])[:4]: # Tomar los 4 principales
                stats = balldontlie.get_player_stats(player['id'])
                if stats and stats.get('pts', 0) > 12: # Filtrar jugadores con impacto real
                    props_analizadas.append({
                        "jugador": f"{player['first_name']} {player['last_name']}",
                        "linea": round(stats.get('pts', 0) - 1.5, 1),
                        "prop": "puntos",
                        "prediccion": "OVER",
                        "confianza": 72
                    })
            return props_analizadas
        except Exception as e:
            return []
    
    def get_games(self):
        try:
            response = requests.get(self.url, timeout=10)
            if response.status_code != 200:
                return []
            
            data = response.json()
            partidos = []
            events = data.get('events', [])
            
            for event in events:
                competitions = event.get('competitions', [])
                if not competitions:
                    continue
                
                comp = competitions[0]
                competitors = comp.get('competitors', [])
                
                if len(competitors) >= 2:
                    # Equipos
                    local_team = competitors[0].get('team', {})
                    visit_team = competitors[1].get('team', {})
                    
                    local = local_team.get('displayName', 'Local')
                    visitante = visit_team.get('displayName', 'Visitante')
                    local_id = local_team.get('id')
                    visit_id = visit_team.get('id')
                    # Extraer logos
                    local_logo = local_team.get('logo', '')
                    visit_logo = visit_team.get('logo', '')
                    
                    # Récords - IMPORTANTE: extraer del campo correcto
                    record_local = '0-0'
                    record_visit = '0-0'
                    
                    # Los records están en 'records' como lista
                    if competitors[0].get('records'):
                        records_list = competitors[0].get('records', [])
                        for r in records_list:
                            if r.get('type') == 'total':
                                record_local = r.get('summary', '0-0')
                                local_streak = r.get('streak', {}).get('abbreviation', '')
                                break
                    
                    if competitors[1].get('records'):
                        records_list = competitors[1].get('records', [])
                        for r in records_list:
                            if r.get('type') == 'total':
                                record_visit = r.get('summary', '0-0')
                                visit_streak = r.get('streak', {}).get('abbreviation', '')
                                break
                    
                    # Odds
                    odds_list = comp.get('odds', [{}])
                    odds = odds_list[0] if odds_list and isinstance(odds_list[0], dict) else {}
                    
                    partidos.append({
                        'local': local,
                        'visitante': visitante,
                        'fecha': event.get('date', ''),
                        'odds': odds,
                        'local_id': local_id,
                        'visitante_id': visit_id,
                        'local_logo': local_logo,
                        'visitante_logo': visit_logo,
                        'records': {
                            'local': record_local, # e.g., "10-5"
                            'visitante': record_visit,
                            'local_streak': local_streak, # e.g., "W3"
                            'visitante_streak': visit_streak
                        },
                        'game_id': event.get('id') # Añadir game_id
                    })
            
            print(f"🏀 NBA: {len(partidos)} partidos cargados desde API")
            return partidos
            
        except Exception as e:
            print(f"Error NBA: {e}")
            return []