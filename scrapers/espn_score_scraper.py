# -*- coding: utf-8 -*-
"""SCRAPER DE RESULTADOS ESPN - Basado en tablas HTML"""
import re
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

class ESPNScoreScraper:
    def __init__(self, game_id):
        self.game_id = game_id
        # URL directa al scoreboard del día
        self.url = f"https://www.espn.com.mx/beisbol/mlb/calendario/_/fecha/20260420"
        self.result_data = {
            "away_team": None, "home_team": None,
            "away_score": None, "home_score": None,
            "winning_pitcher": None, "losing_pitcher": None,
            "status": "FINAL"
        }

    def scrape(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            page = context.new_page()
            
            try:
                print(f"🌐 Navegando a {self.url}")
                page.goto(self.url, wait_until="networkidle", timeout=30000)
                
                # Obtener el HTML y parsear con BeautifulSoup
                html = page.content()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Buscar TODAS las tablas de resultados
                tables = soup.find_all('table')
                print(f"📊 Tablas encontradas: {len(tables)}")
                
                for table in tables:
                    rows = table.find_all('tr')
                    for row in rows:
                        # Buscar el texto "Detroit" y "Boston" en la misma fila
                        row_text = row.get_text()
                        if 'Detroit' in row_text and 'Boston' in row_text:
                            print(f"🔍 Fila encontrada: {row_text[:100]}...")
                            
                            # Extraer equipos
                            teams = row.find_all('a', href=re.compile(r'/equipo/'))
                            if len(teams) >= 2:
                                self.result_data['away_team'] = teams[0].get_text().strip()
                                self.result_data['home_team'] = teams[1].get_text().strip()
                            
                            # Extraer scores (buscar patrones como "8, DET 6" o "DET 6, BOS 8")
                            score_pattern = r'([A-Z]{3})\s*(\d+).*?([A-Z]{3})\s*(\d+)'
                            match = re.search(score_pattern, row_text)
                            if match:
                                if match.group(1) == 'DET':
                                    self.result_data['away_score'] = match.group(2)
                                    self.result_data['home_score'] = match.group(4)
                                else:
                                    self.result_data['away_score'] = match.group(4)
                                    self.result_data['home_score'] = match.group(2)
                                print(f"   -> Score: {self.result_data['away_score']} @ {self.result_data['home_score']}")
                            
                            # Extraer pitchers (buscar en celdas siguientes o en el texto)
                            cells = row.find_all('td')
                            for i, cell in enumerate(cells):
                                cell_text = cell.get_text()
                                if 'Ganado' in cell_text or 'W:' in cell_text:
                                    # El pitcher ganador suele estar en esta celda
                                    self.result_data['winning_pitcher'] = cell_text.replace('Ganado', '').replace('W:', '').strip()
                                if 'Perdido' in cell_text or 'L:' in cell_text:
                                    self.result_data['losing_pitcher'] = cell_text.replace('Perdido', '').replace('L:', '').strip()
                            
                            break
                    
                # Si no encontramos los scores, intentar con patrones más generales
                if not self._is_data_complete():
                    print(f"🔍 Buscando en todo el HTML...")
                    visible_text = soup.get_text()
                    
                    # Buscar "Detroit 6" o "Boston 8"
                    detroit_match = re.search(r'Detroit\s*(\d+)', visible_text)
                    boston_match = re.search(r'Boston\s*(\d+)', visible_text)
                    
                    if detroit_match and boston_match:
                        self.result_data['away_team'] = 'Detroit Tigers'
                        self.result_data['home_team'] = 'Boston Red Sox'
                        self.result_data['away_score'] = detroit_match.group(1)
                        self.result_data['home_score'] = boston_match.group(1)
                        print(f"   -> Score (método 2): {self.result_data['away_score']} @ {self.result_data['home_score']}")
                    
            except Exception as e:
                print(f"❌ Error: {e}")
            finally:
                browser.close()
                
        return self.result_data

    def _is_data_complete(self):
        return (self.result_data["away_score"] is not None and 
                self.result_data["home_score"] is not None)
