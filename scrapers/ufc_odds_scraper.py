# -*- coding: utf-8 -*-
"""
ODDS UFC - BestFightOdds.com
"""

import requests
from bs4 import BeautifulSoup
import re

class UFCOddsScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.url = "https://www.bestfightodds.com/"
    
    def get_ufc_odds(self):
        """Obtiene odds de UFC"""
        try:
            response = requests.get(self.url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            odds = {}
            # Buscar tabla de odds
            table = soup.find('table', class_='odds-table')
            if not table:
                return {}
            
            rows = table.find_all('tr')
            for row in rows:
                fighters = row.find_all('th', class_='odds-fighter')
                odds_cells = row.find_all('td', class_='odds')
                
                if len(fighters) >= 2 and len(odds_cells) >= 2:
                    fighter1 = fighters[0].get_text(strip=True)
                    fighter2 = fighters[1].get_text(strip=True)
                    odd1 = odds_cells[0].get_text(strip=True)
                    odd2 = odds_cells[1].get_text(strip=True)
                    
                    odds[fighter1] = odd1
                    odds[fighter2] = odd2
            
            return odds
        except Exception as e:
            print(f"Error: {e}")
            return {}
