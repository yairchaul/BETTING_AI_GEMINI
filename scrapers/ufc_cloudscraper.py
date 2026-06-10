# -*- coding: utf-8 -*-
"""
UFCSTATS SCRAPER CON CLOUDSCRAPER - Supera Cloudflare definitivamente
"""

import cloudscraper
from bs4 import BeautifulSoup
import json
import re
import os
import time

class UFCStatsCloudScraper:
    def __init__(self):
        # Crear scraper que supera Cloudflare
        self.scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'mobile': False
            }
        )
    
    def get_fighter_stats(self, url):
        """Extrae estadísticas de un peleador superando Cloudflare"""
        if not url:
            return None
        
        try:
            print(f"  🌐 Extrayendo: {url}")
            
            # Hacer la request con cloudscraper
            response = self.scraper.get(url, timeout=30)
            
            if response.status_code != 200:
                print(f"  ❌ Status code: {response.status_code}")
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extraer récord
            record_elem = soup.find('span', class_='b-content__title-record')
            if not record_elem:
                print(f"  ❌ No se encontró el récord")
                return None
            
            record_text = record_elem.get_text(strip=True)
            record_match = re.search(r'Record:\s*(\d+)-(\d+)-(\d+)', record_text)
            
            if record_match:
                record = f"{record_match.group(1)}-{record_match.group(2)}-{record_match.group(3)}"
                wins = int(record_match.group(1))
                losses = int(record_match.group(2))
                draws = int(record_match.group(3))
            else:
                record = "N/A"
                wins = losses = draws = 0
            
            # Extraer datos físicos
            stats = {
                'record': record,
                'wins': wins,
                'losses': losses,
                'draws': draws,
                'altura': 'N/A',
                'peso': 'N/A',
                'alcance': 'N/A',
                'postura': 'Desconocida',
                'edad': 'N/A',
                'apodo': '',
                'metricas': {}
            }
            
            # Extraer nickname
            nickname_elem = soup.find('p', class_='b-content__Nickname')
            if nickname_elem:
                stats['apodo'] = nickname_elem.get_text(strip=True).strip('"')
            
            # Extraer datos de la lista
            bio_items = soup.find_all('li', class_='b-list__box-list-item')
            for item in bio_items:
                text = item.get_text(strip=True)
                if 'Height:' in text:
                    stats['altura'] = text.replace('Height:', '').strip()
                elif 'Weight:' in text:
                    stats['peso'] = text.replace('Weight:', '').strip()
                elif 'Reach:' in text:
                    stats['alcance'] = text.replace('Reach:', '').strip()
                elif 'STANCE:' in text:
                    stats['postura'] = text.replace('STANCE:', '').strip()
                elif 'DOB:' in text:
                    stats['edad'] = text.replace('DOB:', '').strip()
            
            # Extraer estadísticas de carrera
            stats_rows = soup.find_all('tr', class_='b-list__box-list-row')
            for row in stats_rows:
                cols = row.find_all('td')
                if len(cols) >= 2:
                    label = cols[0].get_text(strip=True)
                    value = cols[1].get_text(strip=True)
                    stats['metricas'][label] = value
            
            print(f"  ✅ {record}")
            return stats
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            return None

# URLs de peleadores (formato correcto)
FIGHTER_URLS = {
    "Ilia Topuria": "http://ufcstats.com/fighter-details/ilia-topuria",
    "Justin Gaethje": "http://ufcstats.com/fighter-details/justin-gaethje",
    "Alex Pereira": "http://ufcstats.com/fighter-details/alex-pereira",
    "Ciryl Gane": "http://ufcstats.com/fighter-details/ciryl-gane",
    "Sean O'Malley": "http://ufcstats.com/fighter-details/sean-omalley",
    "Michael Chandler": "http://ufcstats.com/fighter-details/michael-chandler",
    "Derrick Lewis": "http://ufcstats.com/fighter-details/derrick-lewis",
    "Bo Nickal": "http://ufcstats.com/fighter-details/bo-nickal",
    "Steve Garcia": "http://ufcstats.com/fighter-details/steve-garcia",
    "Diego Lopes": "http://ufcstats.com/fighter-details/diego-lopes",
    "Kyle Daukaus": "http://ufcstats.com/fighter-details/kyle-daukaus",
    "Mauricio Ruffy": "http://ufcstats.com/fighter-details/mauricio-ruffy",
    "Josh Hokit": "http://ufcstats.com/fighter-details/josh-hokit",
    "Aiemann Zahabi": "http://ufcstats.com/fighter-details/aiemann-zahabi",
}

if __name__ == "__main__":
    scraper = UFCStatsCloudScraper()
    
    # Probar con varios peleadores
    test_fighters = ["Ilia Topuria", "Justin Gaethje", "Alex Pereira"]
    
    for name in test_fighters:
        url = FIGHTER_URLS.get(name)
        if url:
            print(f"\n{'='*50}")
            print(f"Extrayendo: {name}")
            print('='*50)
            stats = scraper.get_fighter_stats(url)
            if stats:
                print(f"  Récord: {stats['record']}")
                print(f"  Altura: {stats['altura']}")
                print(f"  Peso: {stats['peso']}")
                print(f"  Alcance: {stats['alcance']}")
                print(f"  Postura: {stats['postura']}")
                if stats['metricas']:
                    print(f"  SLpM: {stats['metricas'].get('SLpM', 'N/A')}")
                    print(f"  Precisión: {stats['metricas'].get('Str. Acc.', 'N/A')}")
            time.sleep(2)  # Pausa entre requests
