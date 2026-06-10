# -*- coding: utf-8 -*-
import re
import json
from bs4 import BeautifulSoup
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("❌ Instala playwright: pip install playwright && playwright install")

class TapologyScraper:
    def __init__(self):
        self.base_url = "https://www.tapology.com"

    def scrape_event(self, event_url):
        print(f"🔍 Scrapeando Tapology: {event_url}")
        results = []
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            
            try:
                page.goto(event_url, wait_until="networkidle", timeout=60000)
                html = page.content()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Buscar las filas de las peleas
                fights = soup.select('.fightCard li')
                for fight in fights:
                    names = fight.select('.fightCardFighterName a')
                    if len(names) >= 2:
                        p1 = names[0].text.strip()
                        p2 = names[1].text.strip()
                        
                        # Extraer predicciones de la comunidad si existen
                        pick_info = fight.select_one('.fightCardPickPercent')
                        predictions = pick_info.text.strip() if pick_info else "N/A"
                        
                        results.append({
                            "p1": p1, "p2": p2,
                            "tapology_predictions": predictions
                        })
                
                browser.close()
                return results
            except Exception as e:
                print(f"❌ Fallo Tapology: {e}")
                browser.close()
                return []

if __name__ == "__main__":
    scraper = TapologyScraper()
    data = scraper.scrape_event("https://www.tapology.com/fightcenter/events/139238-ufc-fight-night")
    print(json.dumps(data, indent=2))