# -*- coding: utf-8 -*-
"""
SCRAPER UNIFICADO - UFCStats + Betway
"""

import requests
from bs4 import BeautifulSoup
import re
import json
import os
import time
import unicodedata

class UFCUnifiedScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.cache_path = 'data/ufc_unified_cache.json'
        os.makedirs('data', exist_ok=True)
        self.cache = self._load_cache()
        self.fighters_db = {}

    def _load_cache(self):
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {"fighters": {}, "odds": {}}

    def _save_cache(self):
        with open(self.cache_path, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, indent=2, ensure_ascii=False)

    def clean_name(self, name):
        if not name:
            return ""
        text = unicodedata.normalize('NFD', name)
        text = text.encode('ascii', 'ignore').decode("utf-8")
        return text.strip().lower()

    def get_fighter_stats_ufcstats(self, name):
        """Extrae datos de UFCStats.com"""
        clean = self.clean_name(name)
        
        if clean in self.cache["fighters"]:
            return self.cache["fighters"][clean]
        
        print(f"  🔍 {name}: Buscando en UFCStats...")
        
        parts = name.split()
        if len(parts) == 0:
            return None
        
        last_name = parts[-1]
        letter = last_name[0].lower()
        
        # Obtener lista de peleadores por letra
        url = f"http://ufcstats.com/statistics/fighters?char={letter}&page=all"
        try:
            res = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            rows = soup.find_all('tr')
            
            profile_url = None
            for row in rows:
                cols = row.find_all('td')
                if len(cols) > 3:
                    link = cols[0].find('a')
                    if link:
                        first_name = cols[0].get_text(strip=True)
                        last_name_col = cols[1].get_text(strip=True)
                        full_name = f"{first_name} {last_name_col}"
                        if self.clean_name(full_name) == clean:
                            profile_url = link['href']
                            break
            
            if not profile_url:
                print(f"    ❌ No encontrado")
                return None
            
            # Extraer datos del perfil
            res = requests.get(profile_url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            full_text = soup.get_text(separator=" ", strip=True)
            
            stats = {
                'nombre': name,
                'record': 'N/A',
                'wins': 0,
                'losses': 0,
                'altura': 0,
                'alcance': 0,
                'ko_rate': 0
            }
            
            # Récord
            rec_match = re.search(r'Record:\s*(\d+)-(\d+)-(\d+)', full_text)
            if rec_match:
                stats['record'] = f"{rec_match.group(1)}-{rec_match.group(2)}-{rec_match.group(3)}"
                stats['wins'] = int(rec_match.group(1))
                stats['losses'] = int(rec_match.group(2))
                print(f"    📊 Récord: {stats['record']}")
            
            # Altura
            height_match = re.search(r'Height:\s*(\d+)\'?\s*(\d+)?\"?', full_text)
            if height_match:
                feet = int(height_match.group(1))
                inches = int(height_match.group(2)) if height_match.group(2) else 0
                stats['altura'] = int((feet * 30.48) + (inches * 2.54))
                print(f"    📏 Altura: {stats['altura']}cm")
            
            # Alcance
            reach_match = re.search(r'Reach:\s*(\d+\.?\d*)\"', full_text)
            if reach_match:
                reach = float(reach_match.group(1))
                stats['alcance'] = int(reach * 2.54)
                print(f"    📐 Alcance: {stats['alcance']}cm")
            
            # KO Rate
            ko_wins = 0
            total_wins = 0
            rows = soup.find_all('tr', class_='b-fight-details__table-row')
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 8:
                    win_tag = cols[0].find('i')
                    result = win_tag.get_text(strip=True).lower() if win_tag else ""
                    if result == 'win':
                        total_wins += 1
                        methods = cols[7].find_all('p')
                        method_text = " ".join([m.get_text(strip=True).upper() for m in methods])
                        if 'KO' in method_text or 'TKO' in method_text:
                            ko_wins += 1
            
            if total_wins > 0:
                stats['ko_rate'] = ko_wins / total_wins
                print(f"    💥 KO Rate: {int(stats['ko_rate']*100)}%")
            
            self.cache["fighters"][clean] = stats
            self._save_cache()
            return stats
            
        except Exception as e:
            print(f"    ❌ Error: {str(e)[:50]}")
            return None

    def get_odds_betway(self):
        """Extrae odds de Betway (simulado - requiere API real)"""
        # En tu captura se ven odds como +175, -225, +150, -188
        # Esto requiere scraping de Betway o usar su API interna
        return {}

    def obtener_cartelera_completa(self):
        """Obtiene cartelera de ESPN + odds de Betway"""
        url = "https://site.api.espn.com/apis/site/v2/sports/mma/ufc/scoreboard"
        try:
            res = requests.get(url, headers=self.headers, timeout=10)
            data = res.json()
            eventos = data.get('events', [])
            
            if not eventos:
                return []
            
            evento = eventos[0]
            peleas = []
            
            for comp in evento.get('competitions', []):
                competidores = comp.get('competitors', [])
                if len(competidores) >= 2:
                    p1 = competidores[0].get('athlete', {}).get('displayName', '')
                    p2 = competidores[1].get('athlete', {}).get('displayName', '')
                    
                    # Intentar obtener odds de ESPN (puede estar vacío)
                    odds_p1 = competidores[0].get('odds', {}).get('moneyline', 'N/A')
                    odds_p2 = competidores[1].get('odds', {}).get('moneyline', 'N/A')
                    
                    # Si no hay odds en ESPN, buscar en caché de Betway
                    if odds_p1 == 'N/A':
                        odds_p1 = self.cache["odds"].get(p1, 'N/A')
                    if odds_p2 == 'N/A':
                        odds_p2 = self.cache["odds"].get(p2, 'N/A')
                    
                    if p1 and p2:
                        peleas.append({
                            'evento': evento.get('name', 'UFC'),
                            'fecha': evento.get('date', ''),
                            'peleador1': p1,
                            'peleador2': p2,
                            'odds': {'p1': odds_p1, 'p2': odds_p2}
                        })
            
            return peleas
        except:
            return []


if __name__ == "__main__":
    scraper = UFCUnifiedScraper()
    
    print("="*70)
    print("🧪 TEST UNIFICADO - UFCSTATS")
    print("="*70)
    
    # Probar con peleadores
    peleadores = ["Gilbert Burns", "Mike Malott", "Charles Jourdain"]
    
    for nombre in peleadores:
        print(f"\n🔍 {nombre}:")
        stats = scraper.get_fighter_stats_ufcstats(nombre)
        if stats:
            print(f"  ✅ Récord: {stats['record']}")
            print(f"  ✅ Altura: {stats['altura']}cm")
            print(f"  ✅ Alcance: {stats['alcance']}cm")
            print(f"  ✅ KO Rate: {int(stats['ko_rate']*100)}%")
        else:
            print(f"  ❌ No encontrado")
