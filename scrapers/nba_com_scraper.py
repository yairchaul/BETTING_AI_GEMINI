# -*- coding: utf-8 -*-
import requests
import json
import time

class NBAComScraper:
    """Scraper para obtener datos de jugadores de NBA.com"""
    
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.nba.com/"
        }
    
    def get_players_stats(self, season="2025-26"):
        """Obtiene estadísticas de jugadores de NBA.com"""
        url = f"https://stats.nba.com/stats/leaguedashplayerstats?Season={season}&SeasonType=Regular%20Season&PerMode=PerGame"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            if response.status_code == 200:
                data = response.json()
                headers = data['resultSets'][0]['headers']
                rows = data['resultSets'][0]['rowSet']
                
                players = []
                for row in rows:
                    player_data = dict(zip(headers, row))
                    players.append({
                        "nombre": f"{player_data.get('PLAYER_NAME', '')}",
                        "equipo": player_data.get('TEAM_ABBREVIATION', ''),
                        "puntos": player_data.get('PTS', 0),
                        "triples": player_data.get('FG3M', 0),
                        "asistencias": player_data.get('AST', 0),
                        "rebotes": player_data.get('REB', 0),
                        "minutos": player_data.get('MIN', 0)
                    })
                return players
            else:
                return []
        except Exception as e:
            print(f"Error scraping NBA.com: {e}")
            return []
    
    def get_team_players(self, team_abbr):
        """Obtiene jugadores de un equipo específico"""
        team_ids = {
            "LAL": 1610612747, "GSW": 1610612744, "BOS": 1610612738, "MIL": 1610612749, "BKN": 1610612751,
            "PHX": 1610612756, "PHI": 1610612755, "DAL": 1610612742, "DEN": 1610612743, "MIA": 1610612748,
            "NYK": 1610612752, "LAC": 1610612746, "MEM": 1610612763, "SAC": 1610612758, "NOP": 1610612740,
            "ORL": 1610612753, "IND": 1610612754, "CHI": 1610612741, "ATL": 1610612737, "CHA": 1610612766,
            "CLE": 1610612739, "DET": 1610612765, "TOR": 1610612761, "MIN": 1610612750, "POR": 1610612757,
            "OKC": 1610612760, "UTA": 1610612762, "SAS": 1610612759, "HOU": 1610612745, "WAS": 1610612744
        }
        
        team_id = team_ids.get(team_abbr.upper())
        if not team_id: return []
        
        url = f"https://stats.nba.com/stats/commonteamroster?TeamID={team_id}"
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            if response.status_code == 200:
                data = response.json()
                rows = data['resultSets'][0]['rowSet']
                players = [row[3] for row in rows]
                return players
            return []
        except Exception as e:
            print(f"Error obteniendo roster: {e}")
            return []

if __name__ == "__main__":
    scraper = NBAComScraper()
    players = scraper.get_players_stats()
    print(f"✅ {len(players)} jugadores obtenidos de NBA.com")