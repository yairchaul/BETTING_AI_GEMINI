# -*- coding: utf-8 -*-
"""
UFC STATS SCRAPER - Datos reales de UFCStats.com
Extrae: récord, altura, alcance, KO rate, guardia
"""

import requests
from bs4 import BeautifulSoup
import re
import time
import json
import os
from datetime import datetime

class UFCStatsScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.cache_file = "data/ufc_unificado_cache.json"
        self.cache = self._load_cache()
        
    def _load_cache(self):
        """Carga caché de peleadores"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_cache(self):
        """Guarda caché"""
        os.makedirs("data", exist_ok=True)
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, indent=2, ensure_ascii=False)
    
    def _normalize_name(self, name):
        """Normaliza nombre para URL de UFCStats"""
        name = name.lower().strip()
        name = re.sub(r'[^\w\s-]', '', name)
        name = re.sub(r'\s+', '-', name)
        return name
    
    def _parse_record(self, record_str):
        """Parsea récord '20-5-0' a dict"""
        if not record_str:
            return {'wins': 0, 'losses': 0, 'draws': 0, 'win_rate': 0.5}
        parts = record_str.split('-')
        wins = int(parts[0]) if len(parts) > 0 else 0
        losses = int(parts[1]) if len(parts) > 1 else 0
        draws = int(parts[2]) if len(parts) > 2 else 0
        total = wins + losses + draws
        win_rate = wins / total if total > 0 else 0.5
        return {'wins': wins, 'losses': losses, 'draws': draws, 'win_rate': win_rate, 'total': total}
    
    def _parse_ko_rate(self, wins, ko_wins):
        """Calcula KO rate"""
        if wins > 0:
            return round(ko_wins / wins, 3)
        return 0.0
    
    def get_fighter_stats(self, name):
        """Obtiene estadísticas completas de un peleador"""
        normalized = self._normalize_name(name)
        
        # Verificar caché (válido por 7 días)
        if normalized in self.cache:
            cached = self.cache[normalized]
            cached_date = datetime.fromisoformat(cached.get('cached_date', '2000-01-01'))
            if (datetime.now() - cached_date).days < 7:
                return cached
        
        # Datos por defecto (se actualizarán si el scraper funciona)
        stats = {
            'nombre': name,
            'record': '0-0-0',
            'wins': 0,
            'losses': 0,
            'ko_wins': 0,
            'ko_rate': 0.0,
            'altura': 0,
            'alcance': 0,
            'stance': 'Orthodox',
            'edad': 0,
            'url': f'http://ufcstats.com/fighter-details/{normalized}'
        }
        
        try:
            # Intentar obtener datos reales de UFCStats
            url = f"http://ufcstats.com/fighter-details/{normalized}"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Récord
                record_elem = soup.find('span', class_='b-content__title-record')
                if record_elem:
                    record_text = record_elem.text.strip().replace('Record:', '').strip()
                    record_data = self._parse_record(record_text)
                    stats['record'] = record_text
                    stats['wins'] = record_data['wins']
                    stats['losses'] = record_data['losses']
                
                # Estadísticas físicas
                bio_items = soup.find_all('li', class_='b-list__box-list-item')
                for item in bio_items:
                    text = item.text.strip()
                    if 'Height:' in text:
                        height = re.search(r'(\d+)\'?\s*(\d+)?', text)
                        if height:
                            feet = int(height.group(1)) if height.group(1) else 0
                            inches = int(height.group(2)) if height.group(2) else 0
                            stats['altura'] = feet * 30.48 + inches * 2.54
                    elif 'Reach:' in text:
                        reach = re.search(r'(\d+\.?\d*)', text)
                        if reach:
                            stats['alcance'] = float(reach.group(1)) * 2.54
                    elif 'STANCE:' in text:
                        stance = text.replace('STANCE:', '').strip()
                        stats['stance'] = stance if stance else 'Orthodox'
                    elif 'DOB:' in text:
                        dob = re.search(r'(\w+ \d+, \d{4})', text)
                        if dob:
                            try:
                                dob_date = datetime.strptime(dob.group(1), '%b %d, %Y')
                                stats['edad'] = (datetime.now() - dob_date).days // 365
                            except:
                                pass
                
                # KO/TKO wins
                ko_count = 0
                win_rows = soup.find_all('tr', class_='b-fight-details__table-row')
                for row in win_rows:
                    result = row.find('i', class_='b-flag__text')
                    if result and 'W' in result.text:
                        method = row.find_all('td')
                        if len(method) > 7:
                            method_text = method[7].text.strip().upper()
                            if 'KO' in method_text or 'TKO' in method_text:
                                ko_count += 1
                
                stats['ko_wins'] = ko_count
                stats['ko_rate'] = self._parse_ko_rate(stats['wins'], ko_count)
                
                # Guardar en caché
                stats['cached_date'] = datetime.now().isoformat()
                self.cache[normalized] = stats
                self._save_cache()
                
        except Exception as e:
            print(f"⚠️ Error obteniendo {name}: {e}")
        
        return stats
    
    def get_rankings(self):
        """Obtiene rankings P4P actuales"""
        rankings = []
        try:
            url = "http://ufcstats.com/rankings"
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                # Extraer rankings (simplificado)
                table = soup.find('table', class_='b-list__table')
                if table:
                    rows = table.find_all('tr')[1:16]
                    for i, row in enumerate(rows, 1):
                        cols = row.find_all('td')
                        if len(cols) > 1:
                            name = cols[1].text.strip()
                            rankings.append({'rank': i, 'name': name})
        except Exception as e:
            print(f"⚠️ Error rankings: {e}")
        
        return rankings

if __name__ == "__main__":
    scraper = UFCStatsScraper()
    test = scraper.get_fighter_stats("Jon Jones")
    print(json.dumps(test, indent=2))
