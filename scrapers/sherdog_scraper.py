# -*- coding: utf-8 -*-
"""
SHERDOG SCRAPER - Datos 100% reales de Sherdog.com
"""

import requests
from bs4 import BeautifulSoup
import re
import json
import os
import time
from urllib.parse import quote

class SherdogScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.cache_path = 'data/sherdog_cache.json'
        os.makedirs('data', exist_ok=True)
        self.cache = self._load_cache()

    def _load_cache(self):
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {}

    def _save_cache(self):
        with open(self.cache_path, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, indent=2, ensure_ascii=False)

    def search_fighter(self, name):
        """Busca un peleador en Sherdog"""
        if name in self.cache:
            print(f"  📦 {name}: Usando caché")
            return self.cache[name]
        
        print(f"  🔍 {name}: Buscando en Sherdog...")
        
        try:
            # Buscar en Google: "name Sherdog"
            query = f"{name} Sherdog fighter"
            search_url = f"https://www.google.com/search?q={quote(query)}"
            
            res = requests.get(search_url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # Buscar link de Sherdog
            sherdog_link = None
            for link in soup.find_all('a'):
                href = link.get('href', '')
                if 'sherdog.com/fighter/' in href:
                    sherdog_link = href.split('&')[0].replace('/url?q=', '')
                    break
            
            if not sherdog_link:
                # Intentar búsqueda directa en Sherdog
                sherdog_link = f"https://www.sherdog.com/fighter/{name.replace(' ', '-')}"
            
            # Extraer datos del perfil
            res = requests.get(sherdog_link, headers=self.headers, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            stats = {
                'nombre': name,
                'record': 'N/A',
                'wins': 0,
                'losses': 0,
                'altura': 0,
                'alcance': 0,
                'ko_rate': 0,
                'pais': 'N/A',
                'edad': 0
            }
            
            # Récord
            record_elem = soup.find('span', class_='record')
            if record_elem:
                record_text = record_elem.get_text(strip=True)
                match = re.search(r'(\d+)-(\d+)-(\d+)', record_text)
                if match:
                    stats['record'] = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
                    stats['wins'] = int(match.group(1))
                    stats['losses'] = int(match.group(2))
                    print(f"    📊 Récord: {stats['record']}")
            
            # Datos físicos
            bio_table = soup.find('div', class_='bio')
            if bio_table:
                bio_text = bio_table.get_text(strip=True)
                
                # Altura
                altura_match = re.search(r'Height[:\s]*(\d+)\'?\s*(\d+)?\"?', bio_text, re.I)
                if altura_match:
                    feet = int(altura_match.group(1))
                    inches = int(altura_match.group(2)) if altura_match.group(2) else 0
                    stats['altura'] = int((feet * 30.48) + (inches * 2.54))
                    print(f"    📏 Altura: {stats['altura']}cm")
                
                # Peso
                peso_match = re.search(r'Weight[:\s]*(\d+)\s*lbs', bio_text, re.I)
                if peso_match:
                    stats['peso'] = f"{peso_match.group(1)} lbs"
                
                # Edad
                edad_match = re.search(r'Age[:\s]*(\d+)', bio_text, re.I)
                if edad_match:
                    stats['edad'] = int(edad_match.group(1))
            
            # KO Rate (del historial)
            if stats['wins'] > 0:
                fight_history = soup.find('div', class_='fight_history')
                if fight_history:
                    ko_count = len(re.findall(r'KO|TKO', str(fight_history), re.I))
                    stats['ko_rate'] = min(0.95, ko_count / stats['wins'])
                    print(f"    💥 KO Rate: {int(stats['ko_rate']*100)}%")
            
            self.cache[name] = stats
            self._save_cache()
            return stats
            
        except Exception as e:
            print(f"    ❌ Error: {str(e)[:50]}")
            return {
                'nombre': name,
                'record': 'N/A',
                'wins': 0,
                'losses': 0,
                'altura': 0,
                'alcance': 0,
                'ko_rate': 0
            }

    def obtener_cartelera_ufc(self):
        """Obtiene la cartelera desde ESPN API"""
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
                    
                    if p1 and p2:
                        peleas.append({
                            'evento': evento.get('name', 'UFC'),
                            'fecha': evento.get('date', ''),
                            'peleador1': p1,
                            'peleador2': p2,
                            'odds': {
                                'p1': competidores[0].get('odds', {}).get('moneyline', 'N/A'),
                                'p2': competidores[1].get('odds', {}).get('moneyline', 'N/A')
                            }
                        })
            
            return peleas
        except:
            return []
