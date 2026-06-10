# -*- coding: utf-8 -*-
"""
UFCSTATS DEFINITIVE SCRAPER
Soporta extracción completa de eventos (peleas, resultados, métodos) 
y perfiles de peleadores (récord, datos biográficos y métricas de carrera).
"""

import requests
from bs4 import BeautifulSoup
import json
import re
import os

class UFCStatsScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

    def _clean_text(self, text):
        if not text:
            return ""
        return re.sub(r'\s+', ' ', text).strip()

    def scrape_url(self, url):
        """Detecta automáticamente el tipo de URL y lo parsea"""
        print(f"📡 Extrayendo datos de: {url}")
        if "event-details" in url:
            return {"type": "event", "data": self.scrape_event(url)}
        elif "fighter-details" in url:
            return {"type": "fighter", "data": self.scrape_fighter(url)}
        else:
            print("❌ URL no soportada por este scraper.")
            return None

    def scrape_event(self, url):
        """Extrae todos los detalles de una cartelera/evento completo"""
        try:
            response = requests.get(url, headers=self.headers, timeout=12)
            if response.status_code != 200:
                return {"error": f"Status code {response.status_code}"}
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            title_tag = soup.find('span', class_='b-content__title-highlight')
            event_name = self._clean_text(title_tag.text) if title_tag else "N/A"
            
            event_details = {}
            info_items = soup.find_all('li', class_='b-list__box-list-item')
            for item in info_items:
                label_tag = item.find('i', class_='b-list__box-item-title')
                if label_tag:
                    label = self._clean_text(label_tag.text).replace(':', '')
                    value = self._clean_text(item.text.replace(label_tag.text, ''))
                    event_details[label.lower()] = value

            fights = []
            table = soup.find('table', class_='b-fight-details__table')
            if table:
                rows = table.find_all('tr', class_='b-fight-details__table-row')[1:]
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) < 10: 
                        continue
                    
                    outcome_p = cols[0].find_all('p')
                    res_f1 = self._clean_text(outcome_p[0].text) if len(outcome_p) > 0 else ""
                    res_f2 = self._clean_text(outcome_p[1].text) if len(outcome_p) > 1 else ""
                    
                    fighter_links = cols[1].find_all('a', class_='b-link_style_black')
                    f1_name = self._clean_text(fighter_links[0].text) if len(fighter_links) > 0 else "N/A"
                    f2_name = self._clean_text(fighter_links[1].text) if len(fighter_links) > 1 else "N/A"
                    f1_url = fighter_links[0]['href'] if len(fighter_links) > 0 else ""
                    f2_url = fighter_links[1]['href'] if len(fighter_links) > 1 else ""
                    
                    weight_class = self._clean_text(cols[6].text)
                    
                    method_p = cols[7].find_all('p')
                    method = self._clean_text(method_p[0].text) if len(method_p) > 0 else "N/A"
                    method_details = self._clean_text(method_p[1].text) if len(method_p) > 1 else ""
                    
                    round_end = self._clean_text(cols[8].text)
                    time_end = self._clean_text(cols[9].text)
                    
                    fights.append({
                        "fighter_1": {"nombre": f1_name, "resultado": res_f1, "url": f1_url},
                        "fighter_2": {"nombre": f2_name, "resultado": res_f2, "url": f2_url},
                        "division": weight_class,
                        "metodo": method,
                        "metodo_detalles": method_details,
                        "ronda_final": round_end,
                        "tiempo_final": time_end
                    })
            
            return {
                "evento": event_name,
                "detalles": event_details,
                "peleas": fights
            }
            
        except Exception as e:
            return {"error": str(e)}

    def scrape_fighter(self, url):
        """Extrae el perfil completo, récord y estadísticas de un peleador"""
        try:
            response = requests.get(url, headers=self.headers, timeout=12)
            if response.status_code != 200:
                return {"error": f"Status code {response.status_code}"}
                
            soup = BeautifulSoup(response.content, 'html.parser')
            
            name_tag = soup.find('span', class_='b-content__title-highlight')
            name = self._clean_text(name_tag.text) if name_tag else "N/A"
            
            nickname_tag = soup.find('p', class_='b-content__Nickname')
            nickname = self._clean_text(nickname_tag.text).replace('"', '') if nickname_tag else ""
            
            record_tag = soup.find('span', class_='b-content__title-record')
            record = self._clean_text(record_tag.text).replace('Record:', '').strip() if record_tag else "0-0-0"
            
            stats = {}
            info_items = soup.find_all('li', class_='b-list__box-list-item')
            for item in info_items:
                label_tag = item.find('i', class_='b-list__box-item-title')
                if label_tag:
                    label = self._clean_text(label_tag.text).replace(':', '').replace('.', '')
                    value = self._clean_text(item.text.replace(label_tag.text, ''))
                    if label:
                        stats[label] = value

            return {
                "nombre": name,
                "apodo": nickname,
                "record": record,
                "metricas": stats
            }
            
        except Exception as e:
            return {"error": str(e)}


if __name__ == "__main__":
    scraper = UFCStatsScraper()
    
    url_evento = "http://ufcstats.com/event-details/48544433372ecfa6"
    url_peleador = "http://ufcstats.com/fighter-details/54f64b5e283b0ce7"
    
    resultado_evento = scraper.scrape_url(url_evento)
    resultado_peleador = scraper.scrape_url(url_peleador)
    
    output_data = {
        "evento_ejemplo": resultado_evento,
        "peleador_ejemplo": resultado_peleador
    }
    
    os.makedirs("data", exist_ok=True)
    with open("data/ufcstats_scraped.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
        
    print("\n✅ Extracción completada. Archivo guardado en 'data/ufcstats_scraped.json'")
