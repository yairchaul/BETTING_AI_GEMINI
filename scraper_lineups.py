# -*- coding: utf-8 -*-
"""SCRAPER DE LINEUPS - MLB Stats API"""
import requests, json
from datetime import datetime

def obtener_lineups_hoy():
    """Obtiene lineups confirmados desde MLB API"""
    hoy = datetime.now().strftime("%Y-%m-%d")
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={hoy}&hydrate=probablePitcher,lineup"
    
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        data = r.json()
        
        juegos = []
        for date in data.get("dates", []):
            for game in date.get("games", []):
                away = game["teams"]["away"]["team"]["name"]
                home = game["teams"]["home"]["team"]["name"]
                
                # Pitchers probables
                probables = game.get("probablePitchers", {})
                away_pitcher = probables.get("away", {}).get("fullName", "TBD")
                home_pitcher = probables.get("home", {}).get("fullName", "TBD")
                
                # Lineups (si están disponibles)
                away_lineup = []
                home_lineup = []
                
                juegos.append({
                    "visitante": away,
                    "local": home,
                    "pitcher_visitante": away_pitcher,
                    "pitcher_local": home_pitcher,
                    "lineup_visitante": away_lineup,
                    "lineup_local": home_lineup,
                    "hora": game.get("gameDate", "")[11:16] if game.get("gameDate") else "TBD",
                    "venue": game.get("venue", {}).get("name", "TBD"),
                })
                
                print(f"   {away} @ {home}: {away_pitcher} vs {home_pitcher}")
        
        # Guardar
        with open("lineups_hoy.json", "w", encoding="utf-8") as f:
            json.dump(juegos, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ {len(juegos)} juegos con lineups guardados")
        return juegos
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

if __name__ == "__main__":
    obtener_lineups_hoy()
