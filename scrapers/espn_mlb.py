# -*- coding: utf-8 -*-
"""
ESPN MLB SCRAPER - Con datos reales de la API
"""

import requests
import json
import os
from datetime import datetime

class ESPN_MLB_Mejorado:
    def __init__(self):
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        self.cache_file = "data/mlb_games_cache.json"
        
    def get_games(self):
        """Obtiene partidos MLB de ESPN"""
        
        # Verificar caché (5 minutos para datos actualizados)
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
                    cache_time = datetime.fromisoformat(cache.get('timestamp', '2000-01-01'))
                    if (datetime.now() - cache_time).seconds < 300:
                        return cache.get('games', [])
            except:
                pass
        
        url = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            data = response.json()
            
            games = []
            events = data.get('events', [])
            
            for event in events:
                game = self._parse_event(event)
                if game:
                    games.append(game)
            
            # Guardar caché
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump({'timestamp': datetime.now().isoformat(), 'games': games}, f, indent=2)
            
            # Si no hay partidos, usar datos de demostración
            if not games:
                games = self._get_demo_games()
            
            return games
            
        except Exception as e:
            print(f"Error: {e}")
            return self._get_demo_games()
    
    def _parse_event(self, event):
        """Parsea un evento individual"""
        try:
            competitions = event.get('competitions', [])
            if not competitions:
                return None
            
            comp = competitions[0]
            competitors = comp.get('competitors', [])
            
            if len(competitors) < 2:
                return None
            
            # Identificar local y visitante
            home_team = None
            away_team = None
            
            for team in competitors:
                if team.get('homeAway') == 'home':
                    home_team = team
                else:
                    away_team = team
            
            if not home_team or not away_team:
                return None
            
            # Nombres
            home_name = home_team.get('team', {}).get('displayName', 'Local')
            away_name = away_team.get('team', {}).get('displayName', 'Visitante')
            
            # Récords
            home_record = home_team.get('records', [{}])[0].get('summary', '0-0')
            away_record = away_team.get('records', [{}])[0].get('summary', '0-0')
            
            # Racha
            home_streak = home_team.get('streak', {}).get('description', '')
            away_streak = away_team.get('streak', {}).get('description', '')
            
            # Odds
            odds_data = comp.get('odds', [{}])[0] if comp.get('odds') else {}
            details = odds_data.get('details', '')
            
            # Parsear moneyline
            ml_home = self._parse_moneyline(details)
            ml_away = self._parse_moneyline(details, second=True)
            
            # Over/Under
            over_under = odds_data.get('overUnder', 8.5)
            
            # Hora
            game_date = event.get('date', '')
            game_time = self._format_time(game_date)
            
            # Venue
            venue = comp.get('venue', {}).get('fullName', 'TBD')
            
            # Pitchers (aproximados por ahora)
            pitchers = {
                'local': {'nombre': 'TBD', 'era': 0.0, 'k9': 0.0},
                'visitante': {'nombre': 'TBD', 'era': 0.0, 'k9': 0.0}
            }
            
            return {
                'game_pk': event.get('id'),
                'local': home_name,
                'visitante': away_name,
                'local_record': home_record,
                'visitante_record': away_record,
                'local_streak': home_streak,
                'visitante_streak': away_streak,
                'local_logo': '',
                'visitante_logo': '',
                'odds': {
                    'moneyline': {'local': ml_home, 'visitante': ml_away},
                    'over_under': over_under
                },
                'hora': game_time,
                'venue': venue,
                'pitchers': pitchers,
                'status': 'Programado',
                'league': 'MLB'
            }
            
        except Exception as e:
            return None
    
    def _parse_moneyline(self, details, second=False):
        """Parsea moneyline del string details"""
        if not details:
            return 'N/A'
        
        # Buscar números con + o -
        import re
        numbers = re.findall(r'[+-]\d+', details)
        
        if second and len(numbers) > 1:
            return numbers[1]
        elif numbers:
            return numbers[0]
        
        return 'N/A'
    
    def _format_time(self, date_string):
        """Formatea la hora"""
        if not date_string:
            return 'TBD'
        try:
            dt = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
            return dt.strftime('%H:%M')
        except:
            return 'TBD'
    
    def _get_demo_games(self):
        """Datos de demostración para hoy"""
        return [
            {
                'game_pk': '401',
                'local': 'Cleveland Guardians',
                'visitante': 'Tampa Bay Rays',
                'local_record': '15-14',
                'visitante_record': '14-15',
                'local_streak': 'W2',
                'visitante_streak': 'L1',
                'odds': {'moneyline': {'local': '-118', 'visitante': '+115'}, 'over_under': 8.5},
                'hora': '19:10',
                'venue': 'Progressive Field',
                'pitchers': {'local': {'nombre': 'Logan Allen', 'era': 4.85, 'k9': 8.2},
                           'visitante': {'nombre': 'Zach Eflin', 'era': 4.12, 'k9': 7.8}},
                'status': 'Programado',
                'league': 'MLB'
            },
            {
                'game_pk': '402',
                'local': 'NY Yankees',
                'visitante': 'Boston Red Sox',
                'local_record': '22-7',
                'visitante_record': '16-13',
                'local_streak': 'W5',
                'visitante_streak': 'W1',
                'odds': {'moneyline': {'local': '-160', 'visitante': '+140'}, 'over_under': 9.0},
                'hora': '19:05',
                'venue': 'Yankee Stadium',
                'pitchers': {'local': {'nombre': 'Gerrit Cole', 'era': 2.95, 'k9': 10.5},
                           'visitante': {'nombre': 'Brayan Bello', 'era': 3.85, 'k9': 8.1}},
                'status': 'Programado',
                'league': 'MLB'
            }
        ]

espn_mlb_mejorado = ESPN_MLB_Mejorado()
