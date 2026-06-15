# -*- coding: utf-8 -*-
import requests
import json
import os
from datetime import datetime, timedelta

class BacktestCollector:
    """Recolecta resultados históricos masivos de ESPN para todos los deportes"""
    
    def __init__(self):
        self.base_url = "https://site.api.espn.com/apis/site/v2/sports"
        self.sports = {
            "mlb": "baseball/mlb",
            "nba": "basketball/nba",
            "futbol": "soccer/eng.1", # Premier League por defecto
            "ufc": "mma/ufc"
        }

    def collect_history(self, days=30):
        all_data = []
        end_date = datetime.now()
        
        for sport_name, path in self.sports.items():
            print(f"📡 Recolectando {sport_name}...")
            sport_results = []
            
            for i in range(days):
                date_str = (end_date - timedelta(days=i)).strftime("%Y%m%d")
                url = f"{self.base_url}/{path}/scoreboard?dates={date_str}"
                
                try:
                    resp = requests.get(url).json()
                    for event in resp.get('events', []):
                        competition = event.get('competitions', [{}])[0]
                        teams = competition.get('competitors', [])
                        if len(teams) < 2: continue
                        
                        # Manejo dinámico para UFC (Atletas) vs Deportes de Equipo (Home/Away)
                        if sport_name == "ufc":
                            home, away = teams[0], teams[1]
                        else:
                            home = next((t for t in teams if t.get('homeAway') == 'home'), teams[0])
                            away = next((t for t in teams if t.get('homeAway') == 'away'), teams[1])
                        
                        home_name = home.get('team', {}).get('displayName') or home.get('athlete', {}).get('displayName')
                        away_name = away.get('team', {}).get('displayName') or away.get('athlete', {}).get('displayName')
                        
                        status = event.get('status', {}).get('type', {}).get('name')
                        winner = None
                        if status == "STATUS_FINAL":
                            # En UFC 'winner' es un booleano en la data de ESPN
                            winner = home_name if home.get('winner') else away_name
                        
                        # Extraer Cuotas (Closing Odds)
                        odds_raw = competition.get('odds', [{}])[0]
                        closing_odds = {
                            "details": odds_raw.get('details', 'N/A'),
                            "over_under": odds_raw.get('overUnder', 'N/A'),
                            "spread": odds_raw.get('spread', 'N/A')
                        }

                        sport_results.append({
                            "fecha": date_str,
                            "deporte": sport_name,
                            "nombre": event.get('name'),
                            "home": home_name,
                            "away": away_name,
                            "home_score": home.get('score'),
                            "away_score": away.get('score'),
                            "ganador_real": winner,
                            "closing_odds": closing_odds,
                            "status": status
                        })
                except: continue
            
            output_path = f"data/history_{sport_name}.json"
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(sport_results, f, indent=2)
            print(f"✅ Guardados {len(sport_results)} eventos en {output_path}")

if __name__ == "__main__":
    if not os.path.exists("data"): os.makedirs("data")
    collector = BacktestCollector()
    collector.collect_history(days=15)