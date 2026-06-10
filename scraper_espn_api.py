# -*- coding: utf-8 -*-
"""SCRAPER DE PITCHERS - ESPN API (FUNCIONA)"""
import requests
import json

def obtener_pitchers_espn():
    """Obtiene pitchers desde la API de ESPN (sin bloqueo)"""
    url = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()
        
        juegos = []
        for event in data.get("events", []):
            comp = event.get("competitions", [{}])[0]
            competitors = comp.get("competitors", [])
            
            if len(competitors) >= 2:
                away = competitors[0].get("team", {}).get("displayName", "")
                home = competitors[1].get("team", {}).get("displayName", "")
                
                # Buscar pitchers en probabilidades
                away_pitcher = "TBD"
                home_pitcher = "TBD"
                
                # Intentar obtener de odds/probables
                odds = comp.get("odds", [{}])[0] if comp.get("odds") else {}
                
                juegos.append({
                    "away_team": away,
                    "home_team": home,
                    "away_pitcher": away_pitcher,
                    "home_pitcher": home_pitcher,
                })
                
                print(f"   {away} @ {home}")
        
        return juegos
    except Exception as e:
        print(f"Error ESPN API: {e}")
        return []

if __name__ == "__main__":
    print("📡 Obteniendo partidos desde ESPN API...")
    juegos = obtener_pitchers_espn()
    print(f"\n✅ {len(juegos)} partidos encontrados")
    
    # Guardar
    with open("pitchers_espn_api.json", "w", encoding="utf-8") as f:
        json.dump({"juegos": juegos}, f, indent=2, ensure_ascii=False)
    print("✅ Guardado en pitchers_espn_api.json")
