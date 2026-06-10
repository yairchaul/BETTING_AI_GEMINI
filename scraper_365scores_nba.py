# scraper_365scores_nba.py
import requests
from bs4 import BeautifulSoup
import json
import time
import re

class Scraper365ScoresNBA:
    """Scraper para obtener datos de jugadores NBA desde 365scores.com"""
    
    def __init__(self):
        self.base_url = "https://www.365scores.com/es-mx/basketball/league/nba-103"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
    
    def get_top_scorers(self):
        """Obtiene los máximos anotadores de la NBA"""
        url = "https://www.365scores.com/es-mx/basketball/league/nba-103/statistics"
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                # Buscar tabla de estadísticas
                tables = soup.find_all('table')
                print(f"Tablas encontradas: {len(tables)}")
                return []
            return []
        except Exception as e:
            print(f"Error en 365scores: {e}")
            return []
    
    def get_team_players(self, team_name):
        """Obtiene los jugadores de un equipo específico"""
        # Mapeo de nombres de equipos a URLs
        team_urls = {
            "Lakers": "los-angeles-lakers",
            "Warriors": "golden-state-warriors",
            "Celtics": "boston-celtics",
            "Knicks": "new-york-knicks",
            "Cavaliers": "cleveland-cavaliers",
            "Bulls": "chicago-bulls",
            "Heat": "miami-heat",
            "Nuggets": "denver-nuggets",
            "Suns": "phoenix-suns",
            "Mavericks": "dallas-mavericks",
            "Bucks": "milwaukee-bucks",
            "76ers": "philadelphia-76ers",
            "Clippers": "la-clippers",
            "Kings": "sacramento-kings",
            "Pelicans": "new-orleans-pelicans",
            "Thunder": "oklahoma-city-thunder",
            "Timberwolves": "minnesota-timberwolves",
            "Trail Blazers": "portland-trail-blazers",
            "Jazz": "utah-jazz",
            "Grizzlies": "memphis-grizzlies",
            "Spurs": "san-antonio-spurs",
            "Rockets": "houston-rockets",
            "Magic": "orlando-magic",
            "Hornets": "charlotte-hornets",
            "Wizards": "washington-wizards",
            "Pistons": "detroit-pistons",
            "Pacers": "indiana-pacers",
            "Raptors": "toronto-raptors",
            "Hawks": "atlanta-hawks",
            "Nets": "brooklyn-nets"
        }
        
        team_slug = None
        for name, slug in team_urls.items():
            if name.lower() in team_name.lower():
                team_slug = slug
                break
        
        if not team_slug:
            return []
        
        url = f"https://www.365scores.com/es-mx/basketball/team/{team_slug}/players"
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                # Aquí se parsearían los nombres de jugadores
                # Por ahora, devolvemos datos de ejemplo
                return []
            return []
        except Exception as e:
            print(f"Error obteniendo jugadores de {team_name}: {e}")
            return []

# Prueba
if __name__ == "__main__":
    scraper = Scraper365ScoresNBA()
    print("Probando scraper de 365scores...")
    scraper.get_top_scorers()
