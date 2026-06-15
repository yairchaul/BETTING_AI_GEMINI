# -*- coding: utf-8 -*-
"""
SCRAPER MLB - Baseball-Reference
Extrae estadísticas de pitchers, bateadores y parques
"""

import requests
from bs4 import BeautifulSoup
import re
import json
import os
from datetime import datetime

class MLBScraper:
    def __init__(self):
        self.headers = {'User-Agent': 'Mozilla/5.0'}
        self.cache_path = 'data/mlb_cache.json'
        os.makedirs('data', exist_ok=True)
        self.cache = self._load_cache()
    
    def _load_cache(self):
        if os.path.exists(self.cache_path):
            with open(self.cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"pitchers": {}, "hitters": {}, "parks": {}}
    
    def _save_cache(self):
        with open(self.cache_path, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, indent=2, ensure_ascii=False)
    
    def get_pitcher_stats(self, pitcher_name):
        """Extrae estadísticas de un pitcher (ERA, WHIP, K/9, HR/9)"""
        if pitcher_name in self.cache["pitchers"]:
            return self.cache["pitchers"][pitcher_name]
        
        # Buscar en Baseball-Reference
        search_url = f"https://www.baseball-reference.com/search/search.fcgi?search={pitcher_name.replace(' ', '+')}"
        
        try:
            res = requests.get(search_url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # Buscar link al perfil
            profile_link = soup.find('a', href=re.compile(r'/players/.*\.shtml'))
            if not profile_link:
                return None
            
            profile_url = "https://www.baseball-reference.com" + profile_link['href']
            res = requests.get(profile_url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # Extraer stats de la temporada actual
            stats_table = soup.find('table', {'id': 'pitching_standard'})
            if not stats_table:
                stats_table = soup.find('table', {'class': 'stats_table'})
            
            if stats_table:
                rows = stats_table.find_all('tr')
                for row in rows:
                    if '2026' in row.get_text():
                        cols = row.find_all('td')
                        if len(cols) >= 10:
                            stats = {
                                'nombre': pitcher_name,
                                'era': self._safe_float(cols[3].get_text()) if len(cols) > 3 else 0,
                                'whip': self._safe_float(cols[7].get_text()) if len(cols) > 7 else 0,
                                'k9': self._safe_float(cols[10].get_text()) if len(cols) > 10 else 0,
                                'hr9': self._safe_float(cols[11].get_text()) if len(cols) > 11 else 0,
                                'ip': self._safe_float(cols[2].get_text()) if len(cols) > 2 else 0,
                                'wins': self._safe_int(cols[0].get_text()) if len(cols) > 0 else 0,
                                'losses': self._safe_int(cols[1].get_text()) if len(cols) > 1 else 0
                            }
                            self.cache["pitchers"][pitcher_name] = stats
                            self._save_cache()
                            return stats
            
            return None
            
        except Exception as e:
            print(f"Error extrayendo pitcher {pitcher_name}: {e}")
            return None
    
    def get_hitter_stats(self, hitter_name):
        """Extrae estadísticas de un bateador (HR, BA, OPS, últimos 5 juegos)"""
        if hitter_name in self.cache["hitters"]:
            return self.cache["hitters"][hitter_name]
        
        search_url = f"https://www.baseball-reference.com/search/search.fcgi?search={hitter_name.replace(' ', '+')}"
        
        try:
            res = requests.get(search_url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            profile_link = soup.find('a', href=re.compile(r'/players/.*\.shtml'))
            if not profile_link:
                return None
            
            profile_url = "https://www.baseball-reference.com" + profile_link['href']
            res = requests.get(profile_url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # Extraer stats de bateo
            stats_table = soup.find('table', {'id': 'batting_standard'})
            if stats_table:
                rows = stats_table.find_all('tr')
                for row in rows:
                    if '2026' in row.get_text():
                        cols = row.find_all('td')
                        if len(cols) >= 15:
                            stats = {
                                'nombre': hitter_name,
                                'hr': self._safe_int(cols[8].get_text()) if len(cols) > 8 else 0,
                                'ba': self._safe_float(cols[4].get_text()) if len(cols) > 4 else 0,
                                'ops': self._safe_float(cols[10].get_text()) if len(cols) > 10 else 0,
                                'ab': self._safe_int(cols[2].get_text()) if len(cols) > 2 else 0,
                                'hr_rate': 0
                            }
                            # Calcular HR rate (HR por turno al bate)
                            if stats['ab'] > 0:
                                stats['hr_rate'] = stats['hr'] / stats['ab']
                            
                            self.cache["hitters"][hitter_name] = stats
                            self._save_cache()
                            return stats
            
            return None
            
        except Exception as e:
            print(f"Error extrayendo hitter {hitter_name}: {e}")
            return None
    
    def _safe_float(self, text):
        try:
            return float(text.strip()) if text.strip() else 0.0
        except:
            return 0.0
    
    def _safe_int(self, text):
        try:
            return int(text.strip()) if text.strip() else 0
        except:
            return 0


# ==================== TEST ====================
if __name__ == "__main__":
    scraper = MLBScraper()
    
    print("="*60)
    print("🧪 TEST SCRAPER MLB")
    print("="*60)
    
    # Probar con un pitcher famoso
    pitcher = "Yoshinobu Yamamoto"
    print(f"\n🔍 Buscando pitcher: {pitcher}")
    stats = scraper.get_pitcher_stats(pitcher)
    if stats:
        print(f"  ✅ ERA: {stats['era']}")
        print(f"  ✅ WHIP: {stats['whip']}")
        print(f"  ✅ K/9: {stats['k9']}")
    
    # Probar con un bateador
    hitter = "Shohei Ohtani"
    print(f"\n🔍 Buscando hitter: {hitter}")
    stats = scraper.get_hitter_stats(hitter)
    if stats:
        print(f"  ✅ HR: {stats['hr']}")
        print(f"  ✅ BA: {stats['ba']}")
        print(f"  ✅ OPS: {stats['ops']}")
