# -*- coding: utf-8 -*-
"""SCRAPER HÍBRIDO - ESPN API (rápido) + Selenium (datos profundos)"""
import requests
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

class MLBHybridScraper:
    def __init__(self):
        self.espn_url = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard"
    
    def get_games_complete(self):
        """Obtiene juegos combinando ESPN API y Selenium para lineup"""
        # 1. Obtener datos básicos de ESPN (rápido)
        games = self._get_espn_games()
        
        # 2. Enriquecer con lineup de Selenium (solo si hay juegos)
        if games:
            games = self._enrich_with_lineup(games)
        
        return games
    
    def _get_espn_games(self):
        """Obtiene datos básicos de la API de ESPN"""
        try:
            r = requests.get(self.espn_url, timeout=10)
            data = r.json()
            events = data.get('events', [])
            
            games = []
            for e in events[:10]:
                comps = e.get('competitions', [])
                if not comps:
                    continue
                
                teams = comps[0].get('competitors', [])
                if len(teams) < 2:
                    continue
                
                away = teams[0]
                home = teams[1]
                
                # Extraer récords
                away_rec = away.get('records', [{}])[0].get('summary', '0-0')
                home_rec = home.get('records', [{}])[0].get('summary', '0-0')
                
                # Extraer odds
                odds_data = comps[0].get('odds', [{}])[0] if comps[0].get('odds') else {}
                
                # Extraer enlace al partido para lineup
                links = e.get('links', [])
                gameday_link = None
                for link in links:
                    if 'playbyplay' in link.get('href', ''):
                        gameday_link = link.get('href')
                        break
                
                games.append({
                    'away': away.get('team', {}).get('displayName', 'N/A'),
                    'home': home.get('team', {}).get('displayName', 'N/A'),
                    'away_record': away_rec,
                    'home_record': home_rec,
                    'time': e.get('status', {}).get('type', {}).get('shortDetail', 'TBD'),
                    'odds': {
                        'moneyline': odds_data.get('details', 'N/A')
                    },
                    'gameday_link': gameday_link,
                    'lineup': {'away': [], 'home': []},
                    'pitchers': {'away': {}, 'home': {}},
                    '_validated': True
                })
            
            print(f"✅ ESPN: {len(games)} juegos obtenidos")
            return games
            
        except Exception as e:
            print(f"❌ Error ESPN: {e}")
            return []
    
    def _enrich_with_lineup(self, games):
        """Enriquece juegos con lineup usando Selenium"""
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        driver = webdriver.Chrome(options=options)
        
        try:
            for i, game in enumerate(games[:5]):  # Limitar a 5 para no tardar mucho
                if game.get('gameday_link'):
                    try:
                        driver.get(game['gameday_link'])
                        time.sleep(2)
                        
                        # Extraer lineup
                        lineup_away = []
                        lineup_home = []
                        
                        players = driver.find_elements(By.CSS_SELECTOR, '.lineup__player-name')
                        for p in players[:18]:
                            name = p.text.strip()
                            if name:
                                if len(lineup_away) < 9:
                                    lineup_away.append(name)
                                elif len(lineup_home) < 9:
                                    lineup_home.append(name)
                        
                        game['lineup'] = {'away': lineup_away, 'home': lineup_home}
                        print(f"  ✅ Lineup {game['away']}: {len(lineup_away)} jugadores")
                        
                    except Exception as e:
                        print(f"  ⚠️ Error lineup {game['away']}: {str(e)[:50]}")
            
            return games
            
        finally:
            driver.quit()

# Test
if __name__ == "__main__":
    scraper = MLBHybridScraper()
    games = scraper.get_games_complete()
    print(f"\n📊 Total juegos: {len(games)}")
    for g in games[:3]:
        print(f"\n{g['away']} ({g['away_record']}) @ {g['home']} ({g['home_record']})")
        print(f"  Lineup Away: {len(g['lineup']['away'])} | Home: {len(g['lineup']['home'])}")
