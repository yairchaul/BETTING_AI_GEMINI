# -*- coding: utf-8 -*-
"""
SCRAPER UFC UNIFICADO - Con extracción de fight details CORREGIDA
"""

import requests
from bs4 import BeautifulSoup
import re
import json
import os
import unicodedata
import time

class UFCScraperUnificado:
    def __init__(self):
        self.headers = {'User-Agent': 'Mozilla/5.0'}
        self.cache_path = 'data/ufc_unificado_cache.json'
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
        return {"fighters": {}}
    
    def _save_cache(self):
        with open(self.cache_path, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, indent=2, ensure_ascii=False)
    
    def clean_name(self, name):
        text = unicodedata.normalize('NFD', name)
        text = text.encode('ascii', 'ignore').decode("utf-8")
        return text.strip().lower()
    
    def _extract_fight_details(self, fight_url, fighter_name):
        """Extrae estadísticas detalladas de una pelea específica"""
        try:
            res = requests.get(fight_url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            stats = {
                'strikes_landed': 0,
                'strikes_attempted': 0,
                'td_landed': 0,
                'td_attempted': 0,
                'knockdowns': 0
            }
            
            # Buscar todas las filas de la tabla de estadísticas
            rows = soup.find_all('tr', class_='b-fight-details__table-row')
            
            for row in rows:
                # Buscar el nombre del peleador en la fila
                name_cell = row.find('td', class_='b-fight-details__table-col')
                if name_cell:
                    link = name_cell.find('a')
                    if link and fighter_name.lower() in link.get_text(strip=True).lower():
                        # Encontramos al peleador - extraer sus stats
                        cols = row.find_all('td')
                        
                        # Los índices varían, buscar por texto
                        for i, col in enumerate(cols):
                            text = col.get_text(strip=True)
                            
                            # Strikes
                            if 'of' in text and ('strikes' in text.lower() or i == 2):
                                match = re.search(r'(\d+)\s*of\s*(\d+)', text)
                                if match:
                                    stats['strikes_landed'] = int(match.group(1))
                                    stats['strikes_attempted'] = int(match.group(2))
                            
                            # Takedowns
                            if 'of' in text and ('takedown' in text.lower() or i == 5):
                                match = re.search(r'(\d+)\s*of\s*(\d+)', text)
                                if match:
                                    stats['td_landed'] = int(match.group(1))
                                    stats['td_attempted'] = int(match.group(2))
                            
                            # Knockdowns (primera columna numérica)
                            if text.isdigit() and i == 1:
                                stats['knockdowns'] = int(text)
                        
                        break
            
            return stats
            
        except Exception as e:
            print(f"      ⚠️ Error extrayendo fight details: {e}")
            return None
    
    def get_fighter_stats_ufcstats(self, name):
        """Extrae datos COMPLETOS incluyendo fight details"""
        clean = self.clean_name(name)
        
        if clean in self.cache["fighters"]:
            cached = self.cache["fighters"][clean]
            # Verificar que tenga los nuevos campos
            if 'striking_accuracy' in cached:
                print(f"  📦 {name}: Usando caché")
                return cached
        
        print(f"  🔍 {name}: Buscando en UFCStats...")
        
        parts = name.split()
        if len(parts) == 0:
            return None
        
        last_name = parts[-1]
        letter = last_name[0].lower()
        
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
            
            res = requests.get(profile_url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            stats = {
                'nombre': name,
                'record': 'N/A',
                'wins': 0,
                'losses': 0,
                'altura': 0,
                'alcance': 0,
                'ko_rate': 0,
                'sub_rate': 0,
                'striking_accuracy': 0,
                'takedown_accuracy': 0,
                'takedown_defense': 0,
                'knockdowns_avg': 0,
                'last_fights': []
            }
            
            # 1. RÉCORD
            record_span = soup.find('span', class_='b-content__title-record')
            if record_span:
                record_text = record_span.get_text(strip=True)
                match = re.search(r'Record:\s*(\d+)-(\d+)-(\d+)', record_text)
                if match:
                    stats['record'] = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
                    stats['wins'] = int(match.group(1))
                    stats['losses'] = int(match.group(2))
                    print(f"    ✅ Récord: {stats['record']}")
            
            # 2. DATOS FÍSICOS
            bio_div = soup.find('div', class_='b-list__info-box')
            if bio_div:
                for li in bio_div.find_all('li'):
                    text = li.get_text(strip=True)
                    if 'Height:' in text:
                        match = re.search(r'Height:\s*(\d+)\'\s*(\d+)?\"?', text)
                        if match:
                            feet = int(match.group(1))
                            inches = int(match.group(2)) if match.group(2) else 0
                            stats['altura'] = int((feet * 30.48) + (inches * 2.54))
                            print(f"    ✅ Altura: {stats['altura']}cm")
                    elif 'Reach:' in text:
                        match = re.search(r'Reach:\s*(\d+\.?\d*)\"?', text)
                        if match:
                            reach = float(match.group(1))
                            stats['alcance'] = int(reach * 2.54)
                            print(f"    ✅ Alcance: {stats['alcance']}cm")
            
            # 3. EXTRAER HISTORIAL DE PELEAS
            fight_rows = soup.find_all('tr', class_='b-fight-details__table-row')
            
            total_strikes_landed = 0
            total_strikes_attempted = 0
            total_td_landed = 0
            total_td_attempted = 0
            total_knockdowns = 0
            ko_wins = 0
            sub_wins = 0
            total_wins = 0
            fights_analyzed = 0
            
            for row in fight_rows[:5]:
                cols = row.find_all('td')
                if len(cols) >= 8:
                    result_cell = cols[0]
                    result_text = result_cell.get_text(strip=True).lower()
                    is_win = 'win' in result_text
                    
                    if is_win:
                        total_wins += 1
                        method_cell = cols[7]
                        method_text = method_cell.get_text(strip=True).upper()
                        if 'KO' in method_text or 'TKO' in method_text:
                            ko_wins += 1
                        elif 'SUB' in method_text:
                            sub_wins += 1
                    
                    # Extraer link a fight details
                    fight_link = cols[0].find('a')
                    if fight_link and fight_link.get('href'):
                        fight_url = fight_link['href']
                        fight_stats = self._extract_fight_details(fight_url, name)
                        
                        if fight_stats:
                            total_strikes_landed += fight_stats.get('strikes_landed', 0)
                            total_strikes_attempted += fight_stats.get('strikes_attempted', 0)
                            total_td_landed += fight_stats.get('td_landed', 0)
                            total_td_attempted += fight_stats.get('td_attempted', 0)
                            total_knockdowns += fight_stats.get('knockdowns', 0)
                            fights_analyzed += 1
                            
                            stats['last_fights'].append(fight_stats)
                    
                    time.sleep(0.2)
            
            # Calcular promedios
            if fights_analyzed > 0:
                if total_strikes_attempted > 0:
                    stats['striking_accuracy'] = round(total_strikes_landed / total_strikes_attempted, 2)
                if total_td_attempted > 0:
                    stats['takedown_accuracy'] = round(total_td_landed / total_td_attempted, 2)
                stats['knockdowns_avg'] = round(total_knockdowns / fights_analyzed, 1)
                
                print(f"    ✅ Striking Acc: {int(stats['striking_accuracy']*100)}%")
                print(f"    ✅ Takedown Acc: {int(stats['takedown_accuracy']*100)}%")
            
            if total_wins > 0:
                stats['ko_rate'] = ko_wins / total_wins
                stats['sub_rate'] = sub_wins / total_wins
                print(f"    ✅ KO Rate: {int(stats['ko_rate']*100)}%")
                print(f"    ✅ Sub Rate: {int(stats['sub_rate']*100)}%")
            
            self.cache["fighters"][clean] = stats
            self._save_cache()
            return stats
            
        except Exception as e:
            print(f"    ❌ Error: {e}")
            return None
