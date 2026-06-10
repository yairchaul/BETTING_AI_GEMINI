# -*- coding: utf-8 -*-
"""SCRAPER DINÁMICO - Extrae L10, Pitchers, y resultados de ayer"""
import requests
from datetime import datetime, timedelta

class MLBScraperDinamico:
    def __init__(self):
        self.base_url = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb"
        self.headers = {'User-Agent': 'Mozilla/5.0'}
    
    def get_games_complete(self):
        try:
            url = f"{self.base_url}/scoreboard"
            response = requests.get(url, headers=self.headers, timeout=10)
            data = response.json()
            events = data.get('events', [])
            
            games = []
            for event in events:
                comp = event.get('competitions', [{}])[0]
                teams = comp.get('competitors', [])
                
                if len(teams) < 2:
                    continue
                
                away = next((t for t in teams if t.get('homeAway') == 'away'), teams[0])
                home = next((t for t in teams if t.get('homeAway') == 'home'), teams[1])
                
                # Pitchers
                details = comp.get('details', {})
                pitchers = {"away": {"name": "TBD"}, "home": {"name": "TBD"}}
                for p in details.get('probablePitchers', []):
                    side = p.get('homeAway')
                    if side in pitchers:
                        pitchers[side] = {"name": p.get('athlete', {}).get('displayName', 'TBD')}
                
                # Récord y L10
                away_records = away.get('records', [])
                home_records = home.get('records', [])
                
                games.append({
                    'id': event.get('id'),
                    'away': away.get('team', {}).get('displayName', 'N/A'),
                    'home': home.get('team', {}).get('displayName', 'N/A'),
                    'away_record': away_records[0].get('summary', '0-0') if away_records else '0-0',
                    'home_record': home_records[0].get('summary', '0-0') if home_records else '0-0',
                    'time': event.get('status', {}).get('type', {}).get('shortDetail', 'TBD'),
                    'pitchers': pitchers,
                    'last_10': {
                        'away': away_records[2].get('summary', 'N/A') if len(away_records) > 2 else 'N/A',
                        'home': home_records[2].get('summary', 'N/A') if len(home_records) > 2 else 'N/A'
                    },
                    'odds': self._extract_odds(comp)
                })
            return games
        except Exception as e:
            print(f"Error scraper: {e}")
            return []
    
    def _extract_odds(self, comp):
        odds = comp.get('odds', [{}])[0] if comp.get('odds') else {}
        return {
            'moneyline_away': odds.get('awayTeamOdds', {}).get('american', 'N/A'),
            'moneyline_home': odds.get('homeTeamOdds', {}).get('american', 'N/A'),
            'total': odds.get('overUnder', 8.5),
            'over_odds': odds.get('overOdds', -110),
            'under_odds': odds.get('underOdds', -110)
        }
    
    def obtener_lecciones_ayer(self):
        """Aprende de los resultados de ayer"""
        yesterday = (datetime.now() - timedelta(1)).strftime('%Y%m%d')
        url = f"{self.base_url}/scoreboard?dates={yesterday}"
        try:
            r = requests.get(url, headers=self.headers, timeout=10)
            eventos = r.json().get('events', [])
            lecciones = {}
            for e in eventos:
                if e.get('status', {}).get('type', {}).get('name') == 'STATUS_FINAL':
                    comp = e.get('competitions', [{}])[0]
                    teams = comp.get('competitors', [])
                    if len(teams) >= 2:
                        score_away = int(teams[0].get('score', 0))
                        score_home = int(teams[1].get('score', 0))
                        diferencia = abs(score_away - score_home)
                        lecciones[e.get('id')] = {
                            'margen': diferencia,
                            'cerrado': diferencia <= 1,
                            'ganador': teams[0].get('team', {}).get('displayName') if score_away > score_home else teams[1].get('team', {}).get('displayName')
                        }
            return lecciones
        except:
            return {}
