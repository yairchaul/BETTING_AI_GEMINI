# -*- coding: utf-8 -*-
"""
UFCSTATS SCRAPER CON PLAYWRIGHT - Supera Cloudflare y extrae datos reales
"""

import json
import os
from playwright.sync_api import sync_playwright
import time

class UFCStatsPlaywrightScraper:
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
    
    def _init_browser(self):
        """Inicializa el navegador"""
        if not self.browser:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=True)
            self.context = self.browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            self.page = self.context.new_page()
    
    def _close_browser(self):
        """Cierra el navegador"""
        if self.browser:
            self.browser.close()
            self.playwright.stop()
            self.browser = None
    
    def get_fighter_stats(self, url):
        """Extrae estadísticas de un peleador usando Playwright"""
        if not url:
            return None
        
        self._init_browser()
        
        try:
            print(f"  🌐 Cargando: {url}")
            self.page.goto(url, timeout=30000)
            
            # Esperar a que cargue el contenido (Cloudflare puede tardar)
            self.page.wait_for_selector('.b-content__title-record', timeout=30000)
            time.sleep(2)  # Espera adicional para que cargue todo
            
            # Extraer récord
            record_elem = self.page.query_selector('.b-content__title-record')
            record_text = record_elem.inner_text() if record_elem else "Record: 0-0-0"
            record = record_text.replace('Record:', '').strip()
            
            # Extraer datos físicos
            stats = {
                'record': record,
                'wins': 0,
                'losses': 0,
                'draws': 0,
                'altura': 'N/A',
                'peso': 'N/A',
                'alcance': 'N/A',
                'postura': 'Desconocida',
                'edad': 0,
                'apodo': '',
                'metricas': {}
            }
            
            # Parsear récord
            parts = record.split('-')
            if len(parts) >= 2:
                stats['wins'] = int(parts[0]) if parts[0].isdigit() else 0
                stats['losses'] = int(parts[1]) if parts[1].isdigit() else 0
                if len(parts) > 2:
                    stats['draws'] = int(parts[2]) if parts[2].isdigit() else 0
            
            # Extraer nickname
            nickname_elem = self.page.query_selector('.b-content__Nickname')
            if nickname_elem:
                stats['apodo'] = nickname_elem.inner_text().strip('"')
            
            # Extraer datos de la lista (Height, Weight, Reach, STANCE, DOB)
            items = self.page.query_selector_all('.b-list__box-list-item')
            for item in items:
                text = item.inner_text()
                if 'Height:' in text:
                    stats['altura'] = text.replace('Height:', '').strip()
                elif 'Weight:' in text:
                    stats['peso'] = text.replace('Weight:', '').strip()
                elif 'Reach:' in text:
                    stats['alcance'] = text.replace('Reach:', '').strip()
                elif 'STANCE:' in text:
                    stats['postura'] = text.replace('STANCE:', '').strip()
                elif 'DOB:' in text:
                    dob_text = text.replace('DOB:', '').strip()
                    stats['edad'] = dob_text
            
            # Extraer estadísticas de carrera (tabla)
            rows = self.page.query_selector_all('.b-list__box-list-row')
            for row in rows:
                cols = row.query_selector_all('td')
                if len(cols) >= 2:
                    label = cols[0].inner_text().strip()
                    value = cols[1].inner_text().strip()
                    stats['metricas'][label] = value
            
            print(f"  ✅ Récord extraído: {stats['record']}")
            return stats
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            return None
        finally:
            self._close_browser()
    
    def get_fighter_stats_batch(self, urls):
        """Extrae stats de múltiples peleadores"""
        results = {}
        for name, url in urls.items():
            print(f"\n🔍 Procesando: {name}")
            stats = self.get_fighter_stats(url)
            if stats:
                results[name] = stats
            time.sleep(1)  # Pausa entre requests
        return results

# Mapeo de URLs reales
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
    scraper = UFCStatsPlaywrightScraper()
    
    # Probar con Ilia Topuria
    stats = scraper.get_fighter_stats(FIGHTER_URLS["Ilia Topuria"])
    if stats:
        print(f"\n📊 Resultado:")
        print(json.dumps(stats, indent=2, ensure_ascii=False))
