# -*- coding: utf-8 -*-
"""SCRAPER DE LINEUPS MLB - ESPN"""
import requests
from bs4 import BeautifulSoup
import json

EQUIPO_MAP = {
    "D-backs": "ARI", "Braves": "ATL", "Orioles": "BAL", "Red Sox": "BOS",
    "Cubs": "CHC", "White Sox": "CHW", "Reds": "CIN", "Guardians": "CLE",
    "Rockies": "COL", "Tigers": "DET", "Astros": "HOU", "Royals": "KC",
    "Angels": "LAA", "Dodgers": "LAD", "Marlins": "MIA", "Brewers": "MIL",
    "Twins": "MIN", "Mets": "NYM", "Yankees": "NYY", "Athletics": "ATH",
    "Phillies": "PHI", "Pirates": "PIT", "Padres": "SD", "Giants": "SF",
    "Mariners": "SEA", "Cardinals": "STL", "Rays": "TB", "Rangers": "TEX",
    "Blue Jays": "TOR", "Nationals": "WSH"
}

def obtener_lineups():
    print("🔍 Extrayendo lineups desde ESPN...")
    url = "https://www.espn.com.mx/beisbol/mlb/lineups"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        cards = soup.find_all('div', class_='lineup__container')
        
        juegos = []
        for card in cards:
            teams = card.find_all('span', class_='lineup__mteam')
            if len(teams) < 2: continue
            
            vis_name = teams[0].text.strip()
            loc_name = teams[1].text.strip()
            abr_vis = EQUIPO_MAP.get(vis_name, vis_name[:3].upper())
            abr_loc = EQUIPO_MAP.get(loc_name, loc_name[:3].upper())
            
            pitchers = card.find_all('div', class_='lineup__player-highlight')
            p_vis = pitchers[0].find('a').text if len(pitchers) > 0 else "TBD"
            p_loc = pitchers[1].find('a').text if len(pitchers) > 1 else "TBD"
            
            bateadores = []
            lists = card.find_all('ul', class_='lineup__list')
            for i, side in enumerate(lists):
                team_abr = abr_vis if i == 0 else abr_loc
                for li in side.find_all('li', class_='lineup__player'):
                    nombre = li.find('a').text if li.find('a') else li.text.strip()
                    bateadores.append({"nombre": nombre, "equipo": team_abr})
            
            juegos.append({
                "visitante": abr_vis, "local": abr_loc,
                "p_visitante": p_vis, "p_local": p_loc,
                "bateadores": bateadores
            })
        
        print(f"✅ {len(juegos)} juegos extraidos")
        return juegos
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

if __name__ == "__main__":
    juegos = obtener_lineups()
    if juegos:
        with open("lineups_hoy.json", "w", encoding="utf-8") as f:
            json.dump(juegos, f, indent=2, ensure_ascii=False)
        print("✅ Guardado en lineups_hoy.json")
