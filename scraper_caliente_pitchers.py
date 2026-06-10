# -*- coding: utf-8 -*-
"""SCRAPER CALIENTE.MX - ODDS + PITCHERS EN VIVO"""
import requests
import json
import re
from datetime import datetime

def extraer_odds_y_pitchers_caliente():
    """Extrae odds y pitchers desde Caliente.mx"""
    print("=" * 60)
    print("🎲 SCRAPER CALIENTE.MX - ODDS + PITCHERS")
    print("=" * 60)
    
    url = "https://sports.caliente.mx/es_MX/MLB"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200:
            print(f"❌ Error HTTP: {r.status_code}")
            return None
        
        content = r.text
        
        # Buscar nombres de equipos MLB y pitchers
        # Caliente muestra: "Equipo (Pitcher)" en los nombres
        patron_partido = re.findall(
            r'([A-Za-z\s]+(?:\([A-Za-z\s.]+\))?)\s*[-+]\d{3,4}',
            content
        )
        
        # Buscar odds (+/- números de 3-4 dígitos)
        odds_encontradas = re.findall(r'[-+]\d{3,4}', content)
        
        # Buscar nombres de equipos con pitchers
        equipos_con_pitcher = re.findall(
            r'([A-Za-z\s]+)\s*\(([A-Za-z\s.]+)\)',
            content
        )
        
        print(f"   Equipos con pitcher: {len(equipos_con_pitcher)}")
        print(f"   Odds encontradas: {len(odds_encontradas)}")
        
        # Mapeo de equipos
        mapeo_equipos = {
            "Rays": "Tampa Bay Rays", "Guardians": "Cleveland Guardians",
            "Cardinals": "St. Louis Cardinals", "Pirates": "Pittsburgh Pirates",
            "Red Sox": "Boston Red Sox", "Blue Jays": "Toronto Blue Jays",
            "Angels": "Los Angeles Angels", "White Sox": "Chicago White Sox",
            "Mariners": "Seattle Mariners", "Twins": "Minnesota Twins",
            "Yankees": "New York Yankees", "Rangers": "Texas Rangers",
            "Cubs": "Chicago Cubs", "Padres": "San Diego Padres",
            "Marlins": "Miami Marlins", "Dodgers": "Los Angeles Dodgers",
            "Tigers": "Detroit Tigers", "Reds": "Cincinnati Reds",
            "Orioles": "Baltimore Orioles", "Astros": "Houston Astros",
            "Braves": "Atlanta Braves", "Phillies": "Philadelphia Phillies",
            "Mets": "New York Mets", "Brewers": "Milwaukee Brewers",
            "Diamondbacks": "Arizona Diamondbacks", "Giants": "San Francisco Giants",
            "Rockies": "Colorado Rockies", "Nationals": "Washington Nationals",
            "Athletics": "Athletics", "Royals": "Kansas City Royals",
        }
        
        # Construir partidos con odds y pitchers
        partidos = []
        pitchers_extraidos = {}
        
        for equipo_corto, pitcher in equipos_con_pitcher:
            for corto, completo in mapeo_equipos.items():
                if corto.lower() in equipo_corto.lower():
                    pitchers_extraidos[completo] = pitcher.strip()
                    print(f"   🥎 {completo}: {pitcher.strip()}")
                    break
        
        # Guardar pitchers
        if pitchers_extraidos:
            # Actualizar resultados_finales_corregidos.json
            try:
                with open("resultados_finales_corregidos.json", "r", encoding="utf-8") as f:
                    partidos_json = json.load(f)
                
                for p in partidos_json:
                    v = p.get("visitante", "")
                    l = p.get("local", "")
                    if v in pitchers_extraidos:
                        p["pitchers"]["visitante"]["nombre"] = pitchers_extraidos[v]
                    if l in pitchers_extraidos:
                        p["pitchers"]["local"]["nombre"] = pitchers_extraidos[l]
                
                with open("resultados_finales_corregidos.json", "w", encoding="utf-8") as f:
                    json.dump(partidos_json, f, indent=2, ensure_ascii=False)
                print(f"\n✅ resultados_finales_corregidos.json actualizado con {len(pitchers_extraidos)} pitchers")
            except Exception as e:
                print(f"⚠️ No se pudo actualizar: {e}")
            
            # También guardar en pitchers_hoy
            juegos = []
            with open("resultados_finales_corregidos.json", "r", encoding="utf-8") as f:
                partidos_json = json.load(f)
            for p in partidos_json:
                juegos.append({
                    "away_team": p.get("visitante", ""),
                    "home_team": p.get("local", ""),
                    "away_pitcher": p.get("pitchers", {}).get("visitante", {}).get("nombre", "TBD"),
                    "home_pitcher": p.get("pitchers", {}).get("local", {}).get("nombre", "TBD"),
                })
            
            with open("pitchers_hoy_selenium.json", "w", encoding="utf-8") as f:
                json.dump({"juegos": juegos, "fuente": "Caliente.mx", "actualizado": datetime.now().strftime("%Y-%m-%d %H:%M")}, f, indent=2, ensure_ascii=False)
            print(f"✅ pitchers_hoy_selenium.json actualizado")
        
        return pitchers_extraidos
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == "__main__":
    pitchers = extraer_odds_y_pitchers_caliente()
    if pitchers:
        print(f"\n✅ {len(pitchers)} pitchers extraídos de Caliente.mx")
    else:
        print("\n⚠️ No se pudieron extraer pitchers. Usando datos manuales...")
        # Fallback a datos manuales
        import subprocess
        subprocess.run(["python", "inyectar_pitchers_reales.py"])
