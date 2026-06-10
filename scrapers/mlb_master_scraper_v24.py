# -*- coding: utf-8 -*-
"""
MLB MASTER SCRAPER V24 - Fuentes Oficiales MLB.com
Extrae: Lineups, Probables, Stats y Sincroniza Caliente + Clima
"""
import os
import sys
import json
import time
import subprocess
import io
from datetime import datetime
from bs4 import BeautifulSoup # Added for parsing HTML
from motors.predictor_hr import predictor_hr # Importación para enriquecimiento en memoria

# Parche de consola Windows (UTF-8)
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    print("❌ Error: Selenium o WebdriverManager no instalados.")
    sys.exit(1)

class MLBMasterScraperV24:
    def __init__(self):
        self.options = Options()
        self.options.add_argument("--headless")
        self.options.add_argument("--no-sandbox")
        self.options.add_argument("--disable-dev-shm-usage")
        self.options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        try:
            self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=self.options)
        except Exception as e:
            print(f"⚠️ No se pudo iniciar Chrome: {e}")
            self.driver = None

        self.output_file = "data/resultados_finales_corregidos.json"
        self.urls = {
            "probable": "https://www.mlb.com/es/probable-pitchers",
            "lineups": "https://www.mlb.com/es/starting-lineups",
            "stats_hitting": "https://www.mlb.com/stats/",
            "stats_pitching": "https://www.mlb.com/stats/pitching",
            "gameday": "https://www.mlb.com/es/gameday/" # Base for individual game scraping
        }
        self.mlb_games_data = [] # To store the scraped data before saving

    def _extract_probable_pitchers(self):
        pitchers_data = {}
        try:
            self.driver.get(self.urls["probable"])
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "probable-pitchers__matchup")))
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            matchups = soup.find_all('div', class_='probable-pitchers__matchup')
            for matchup in matchups:
                teams = matchup.find_all('div', class_='probable-pitchers__team-name')
                pitchers = matchup.find_all('div', class_='probable-pitchers__pitcher-name')
                
                if len(teams) == 2 and len(pitchers) == 2:
                    away_team = teams[0].text.strip()
                    home_team = teams[1].text.strip()
                    away_pitcher = pitchers[0].text.strip()
                    home_pitcher = pitchers[1].text.strip()
                    
                    pitchers_data[away_team] = away_pitcher
                    pitchers_data[home_team] = home_pitcher
            print(f"   ✅ {len(pitchers_data)} probable pitchers extraídos.")
        except Exception as e:
            print(f"   ❌ Error extrayendo probable pitchers: {e}")
        return pitchers_data

    def _extract_lineups(self):
        lineups_data = {} # Key: "AwayTeam vs HomeTeam", Value: {"away": [], "home": []}
        try:
            self.driver.get(self.urls["lineups"])
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "starting-lineups__matchup")))
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            matchups = soup.find_all('div', class_='starting-lineups__matchup')
            for matchup in matchups:
                game_title_elem = matchup.find('div', class_='starting-lineups__matchup-title')
                if not game_title_elem: continue
                
                game_title = game_title_elem.text.strip() # e.g., "New York Yankees vs Boston Red Sox"
                teams = game_title.split(' vs ')
                if len(teams) != 2: continue
                
                away_team_name = teams[0].strip()
                home_team_name = teams[1].strip()
                
                away_lineup_list = []
                home_lineup_list = []
                
                away_players_elem = matchup.find('div', class_='starting-lineups__team--away')
                if away_players_elem:
                    for player_elem in away_players_elem.find_all('div', class_='starting-lineups__player-name'):
                        away_lineup_list.append(player_elem.text.strip())
                
                home_players_elem = matchup.find('div', class_='starting-lineups__team--home')
                if home_players_elem:
                    for player_elem in home_players_elem.find_all('div', class_='starting-lineups__player-name'):
                        home_lineup_list.append(player_elem.text.strip())
                
                lineups_data[f"{away_team_name} vs {home_team_name}"] = {
                    "away": away_lineup_list,
                    "home": home_lineup_list
                }
            print(f"   ✅ {len(lineups_data)} lineups extraídos.")
        except Exception as e:
            print(f"   ❌ Error extrayendo lineups: {e}")
        return lineups_data

    def scrape_scores_ayer(self):
        """Extrae resultados reales de MLB.com/scores para auditoría"""
        print("📡 Extrayendo Scores oficiales de MLB.com...")
        try:
            self.driver.get("https://www.mlb.com/es/scores")
            time.sleep(5)
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            juegos_finalizados = []
            cards = soup.find_all('div', class_='gameday-game-card') # Basado en estructura actual
            
            for card in cards:
                try:
                    away = card.find('div', {'data-tst': 'away-team-name'}).text.strip()
                    home = card.find('div', {'data-tst': 'home-team-name'}).text.strip()
                    score_a = int(card.find('div', {'data-tst': 'away-team-score'}).text)
                    score_h = int(card.find('div', {'data-tst': 'home-team-score'}).text)
                    
                    juegos_finalizados.append({
                        "away": away, "home": home,
                        "ganador": home if score_h > score_a else away,
                        "total_runs": score_h + score_a,
                        "status": "FINAL"
                    })
                except: continue
            return juegos_finalizados
        except Exception as e:
            print(f"❌ Error en scores: {e}"); return []

    def _extract_hr_leaders(self):
        """Extrae líderes de HR directamente de MLB.com para alimentar el PredictorHR"""
        leaders = {}
        try:
            self.driver.get(self.urls["stats_hitting"])
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "bui-table")))
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            rows = soup.find_all('tr')
            for row in rows[1:50]: # Top 50
                cols = row.find_all('td')
                if len(cols) > 5:
                    name = cols[1].text.strip()
                    hr = int(cols[5].text.strip())
                    leaders[name] = hr
            print(f"   ✅ {len(leaders)} líderes de HR sincronizados.")
        except Exception as e:
            print(f"   ⚠️ No se pudieron extraer líderes HR: {e}")
        return leaders

    def scrape_mlb_official(self):
        if not self.driver: return
        
        print("="*60)
        print("🚀 INICIANDO MLB MASTER SCRAPER V24 (Oficial MLB.com)")
        print("="*60)
        
        try:
            # 1. Scrapear Pitchers Probables
            probable_pitchers = self._extract_probable_pitchers()
            
            # 1.1 Scrapear Líderes HR
            hr_stats = self._extract_hr_leaders()

            # 2. Scrapear Starting Lineups
            lineups = self._extract_lineups()

            # 3. Obtener datos básicos de juegos (similar a espn_mlb.py)
            # This part needs to be robust. Let's use ESPN API as a base for games.
            # Then enrich with MLB.com data.
            from .espn_mlb import ESPN_MLB_Mejorado # Relative import
            espn_scraper = ESPN_MLB_Mejorado()
            self.mlb_games_data = espn_scraper.get_games() # Get base games from ESPN API

            # SINCRONIZACIÓN QUIRÚRGICA: Configurar predictor con datos frescos en memoria
            predictor_hr.mlb_partidos_hoy = self.mlb_games_data
            # Sincronizar pitchers probables internos con lo que acabamos de obtener
            predictor_hr.juegos_hoy = [{"away_team": g['visitante'], "home_team": g['local'], 
                                        "away_pitcher": g['pitchers']['visitante']['nombre'], 
                                        "home_pitcher": g['pitchers']['local']['nombre']} for g in self.mlb_games_data]

            # Enrich ESPN games with MLB.com data
            for game in self.mlb_games_data:
                away_team = game.get('visitante', '')
                home_team = game.get('local', '')
                game['fecha'] = datetime.now().strftime("%Y-%m-%d")
                
                # ASEGURAR LLAVES DE RÉCORD PARA EL VISUALIZADOR
                if 'visit_record' not in game and 'visitante_record' in game:
                    game['visit_record'] = game['visitante_record']
                
                # Add probable pitchers
                if away_team in probable_pitchers:
                    game['pitchers']['visitante']['nombre'] = probable_pitchers[away_team]
                if home_team in probable_pitchers:
                    game['pitchers']['local']['nombre'] = probable_pitchers[home_team]
                
                # Add lineups
                game_key = f"{away_team} vs {home_team}"
                if game_key in lineups:
                    game['lineups'] = lineups[game_key]
                else:
                    game['lineups'] = {"away": [], "home": []} # Default empty if not found
                
                # 3.1 Integrar Predicciones HR directamente (Enriquecimiento en memoria)
                try:
                    game['hr_candidates_local'] = predictor_hr.obtener_predicciones_para_equipo(home_team, game_pk=game.get('game_pk'))
                    game['hr_candidates_visit'] = predictor_hr.obtener_predicciones_para_equipo(away_team, game_pk=game.get('game_pk'))
                except Exception as e:
                    print(f"   ⚠️ No se pudieron precalcular HR para {game_key}: {e}")

            # 4. Stats Globales (Visita rápida para asegurar refresco de CDN)
            print("📊 Verificando Rankings y Stats en MLB.com...")
            self.driver.get(self.urls["stats_hitting"])
            time.sleep(2)
            self.driver.get(self.urls["stats_pitching"])
            print("   ✅ Navegación por fuentes oficiales completada.")
            
            # Save the enriched data
            with open(self.output_file, "w", encoding="utf-8") as f:
                json.dump(self.mlb_games_data, f, indent=2, ensure_ascii=False)
            print(f"   ✅ Datos de MLB (pitchers, lineups) guardados en {self.output_file}")

        except Exception as e:
            print(f"❌ Error durante el scraping oficial: {e}")
        finally:
            if self.driver:
                self.driver.quit()

    def sincronizar_sistema(self):
        """Llama a los scripts dependientes para completar el set de datos"""
        print("\n" + "-"*40)
        print("🔗 SINCRONIZANDO CABLES DE DATOS...")
        
        # 1. Llamar a Caliente para Momios y Pitchers Realtime (actualiza el mismo output_file)
        try:
            print("🎲 Ejecutando scraper_caliente_selenium.py...")
            subprocess.run([sys.executable, "scraper_caliente_selenium.py"], check=True)
        except Exception as e:
            print(f"⚠️ Error en sincronización Caliente: {e}")

        # 2. Llamar a Clima para actualizar factores ambientales (actualiza el mismo output_file)
        try:
            print("☁️ Ejecutando update_clima_data.py...")
            subprocess.run([sys.executable, "update_clima_data.py"], check=True)
        except Exception as e:
            print(f"⚠️ Error en sincronización Clima: {e}")
            
        print("-"*40)
        print("🎉 PROCESO MAESTRO V24 FINALIZADO")
        print("="*60)

if __name__ == "__main__":
    master = MLBMasterScraperV24()
    master.scrape_mlb_official()
    master.sincronizar_sistema()