# mlb_balldontlie_scraper.py
import requests
import json

class MLBBalldontlieScraper:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.balldontlie.io/v1"
        self.headers = {"Authorization": api_key}
    
    def get_teams(self):
        """Obtener equipos de MLB"""
        response = requests.get(f"{self.base_url}/mlb/teams", headers=self.headers)
        return response.json()
    
    def get_players(self, team_id=None):
        """Obtener jugadores (incluye pitchers)"""
        url = f"{self.base_url}/mlb/players"
        if team_id:
            url += f"?team_ids[]={team_id}"
        response = requests.get(url, headers=self.headers)
        return response.json()
    
    def get_player_stats(self, player_id, season="2025"):
        """Obtener estadísticas de pitcher (K/9, ERA, WHIP)"""
        url = f"{self.base_url}/mlb/season_averages?season={season}&player_ids[]={player_id}"
        response = requests.get(url, headers=self.headers)
        return response.json()

# Probar conexión
if __name__ == "__main__":
    API_KEY = "c0da27f9-394d-473f-aae3-f8e0b48f27ef"
    scraper = MLBBalldontlieScraper(API_KEY)
    
    # Probar equipos
    teams = scraper.get_teams()
    print(f"Equipos MLB: {len(teams.get('data', []))}")
