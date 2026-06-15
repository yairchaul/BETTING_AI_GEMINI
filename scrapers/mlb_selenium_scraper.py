# -*- coding: utf-8 -*-
"""SCRAPER MLB CON SELENIUM - Selectores corregidos"""
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

class MLBSeleniumScraper:
    def __init__(self, headless=True):
        self.options = Options()
        if headless:
            self.options.add_argument("--headless")
        self.options.add_argument("--no-sandbox")
        self.options.add_argument("--disable-dev-shm-usage")
        self.options.add_argument("--window-size=1920,1080")
        self.options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    def get_games_complete(self):
        driver = webdriver.Chrome(options=self.options)
        games = []
        
        try:
            print("🌐 Navegando a MLB.com/scores...")
            driver.get("https://www.mlb.com/scores")
            time.sleep(5)  # Esperar carga completa
            
            # Intentar múltiples selectores
            selectors = [
                '[class*="GameCard"]',
                '[data-testid*="game"]',
                '.game-card',
                '[class*="matchup"]'
            ]
            
            game_containers = []
            for sel in selectors:
                game_containers = driver.find_elements(By.CSS_SELECTOR, sel)
                if game_containers:
                    print(f"  ✅ Encontrados {len(game_containers)} juegos con selector: {sel}")
                    break
            
            if not game_containers:
                # Último intento: buscar por enlaces de gameday
                links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/gameday/"]')
                print(f"  🔗 Encontrados {len(links)} enlaces a gameday")
                
                # Extraer IDs de juego de los enlaces
                import re
                seen = set()
                for link in links:
                    href = link.get_attribute('href')
                    if href:
                        match = re.search(r'/gameday/(\d+)', href)
                        if match and match.group(1) not in seen:
                            seen.add(match.group(1))
                            games.append({
                                'away': 'Away',
                                'home': 'Home',
                                'away_record': '0-0',
                                'home_record': '0-0',
                                'time': 'TBD',
                                'pitchers': {},
                                'lineup': {'away': [], 'home': []},
                                'game_id': match.group(1),
                                'odds': {}
                            })
            
            # Procesar contenedores encontrados
            for container in game_containers[:10]:
                try:
                    # Extraer texto completo para debug
                    text = container.text[:200]
                    
                    # Buscar nombres de equipos en el texto
                    import re
                    team_pattern = r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
                    teams = re.findall(team_pattern, text)
                    
                    if len(teams) >= 2:
                        # Filtrar palabras comunes no relacionadas con equipos
                        common_words = ['Today', 'Tomorrow', 'Final', 'Preview', 'Game', 'AM', 'PM']
                        teams = [t for t in teams if t not in common_words]
                        
                        if len(teams) >= 2:
                            away = teams[0]
                            home = teams[1]
                            
                            games.append({
                                'away': away,
                                'home': home,
                                'away_record': '0-0',
                                'home_record': '0-0',
                                'time': 'TBD',
                                'pitchers': {},
                                'lineup': {'away': [], 'home': []},
                                'odds': {}
                            })
                            print(f"  ✅ {away} @ {home}")
                            
                except Exception as e:
                    print(f"  ⚠️ Error: {str(e)[:50]}")
                    continue
            
            return games
            
        except Exception as e:
            print(f"❌ Error general: {e}")
            return []
        finally:
            driver.quit()

# Test
if __name__ == "__main__":
    scraper = MLBSeleniumScraper(headless=False)  # Sin headless para ver qué pasa
    games = scraper.get_games_complete()
    print(f"\n✅ Juegos obtenidos: {len(games)}")
