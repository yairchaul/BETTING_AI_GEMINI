# -*- coding: utf-8 -*-
"""
espn_mlb.py - NEON V3.3
Scraper con normalización de nombres para Predictor HR
"""
import requests
import json
from datetime import datetime
from utils.fuzzy_matching import normalizar_equipo
from utils.mapeo_equipos import TRADUCCION_MLB

class ESPN_MLB_Mejorado:
    def __init__(self):
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    def _normalizar_equipo(self, nombre):
        return normalizar_equipo(nombre)

    def get_games(self):
        hoy = datetime.now().strftime("%Y%m%d")
        print(f"📅 Sincronizando MLB para NEON: {hoy}")
        partidos = self._get_from_api(hoy)
        if not partidos:
            partidos = self._get_backup_data()
        
        for p in partidos:
            p['visitante'] = self._normalizar_equipo(p['visitante'])
            p['local'] = self._normalizar_equipo(p['local'])
        
        self._guardar_pitchers(partidos)
        return partidos

    def _get_from_api(self, fecha):
        url = f"https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard?dates={fecha}"
        try:
            r = requests.get(url, headers=self.headers, timeout=10)
            if r.status_code == 200 and 'events' in r.json():
                events = r.json().get('events', [])
                partidos = []
                for event in events:
                    comp = event.get('competitions', [{}])[0]
                    competitors = comp.get('competitors', [])
                    away = next(c for c in competitors if c['homeAway'] == 'away')
                    home = next(c for c in competitors if c['homeAway'] == 'home')
                    odds = comp.get('odds', [{}])[0] if comp.get('odds') else {}
                    partidos.append({
                        'visitante': away['team']['displayName'],
                        'local': home['team']['displayName'],
                        'hora': datetime.strptime(event['date'], "%Y-%m-%dT%H:%MZ").strftime("%H:%M") if 'date' in event else "TBD",
                        'venue': comp.get('venue', {}).get('fullName', 'TBD'),
                        'odds': {
                            'over_under': odds.get('overUnder', 8.5),
                            'moneyline': {
                                'visitante': odds.get('awayTeamOdds', {}).get('value', 'N/A'),
                                'local': odds.get('homeTeamOdds', {}).get('value', 'N/A')
                            }
                        },
                        'pitchers': {'visitante': {'nombre': 'TBD', 'id': 'N/A'}, 'local': {'nombre': 'TBD', 'id': 'N/A'}},
                        'game_pk': event.get('id') # Añadir el ID del juego
                    })
                return partidos
        except Exception as e:
            print(f"⚠️ Error en API de ESPN: {e}")
        return []

    def _guardar_pitchers(self, partidos):
        data = {'juegos': []}
        for p in partidos:
            data['juegos'].append({
                'away_team': p['visitante'],
                'home_team': p['local'],
                'away_pitcher': p['pitchers']['visitante']['nombre'],
                'home_pitcher': p['pitchers']['local']['nombre']
            })
        with open('pitchers_hoy_selenium.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _get_backup_data(self):
        # Datos de emergencia (Regla 10)
        return [{
            "visitante": "Tampa Bay Rays", 
            "local": "Cleveland Guardians", 
            "odds": {"over_under": 8.0, "moneyline": {"visitante": "-110", "local": "-110"}}, 
            "pitchers": {"visitante": {"nombre": "TBD"}, "local": {"nombre": "TBD"}},
            "game_pk": "000000"
        }]

if __name__ == "__main__":
    scraper = ESPN_MLB_Mejorado()
    for p in scraper.get_games():
        print(f"🚀 {p['visitante']} vs {p['local']} | Sincronizado")
