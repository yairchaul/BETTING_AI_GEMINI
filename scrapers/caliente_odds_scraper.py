# -*- coding: utf-8 -*-
import requests
from bs4 import BeautifulSoup
import json
import re
import sys
import io
import logging

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
logger = logging.getLogger(__name__)

class CalienteOddsScraper:
    def __init__(self):
        self.base_url = "https://www.caliente.mx"
        self.urls_mlb = [
            "/ofertas/mlb",
            "/deportes/beisbol/mlb",
            "/ofertas/beisbol",
        ]
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-MX,es;q=0.9,en;q=0.8',
        }
        self.cache_file = "caliente_odds_cache.json"
        
        # Mapeo de nombres Caliente -> ESPN/MLB
        self.team_mapping = {
            "NY YANKEES": "New York Yankees",
            "YANKEES": "New York Yankees",
            "BOSTON": "Boston Red Sox",
            "RED SOX": "Boston Red Sox",
            "TORONTO": "Toronto Blue Jays",
            "BLUE JAYS": "Toronto Blue Jays",
            "TAMPA BAY": "Tampa Bay Rays",
            "RAYS": "Tampa Bay Rays",
            "BALTIMORE": "Baltimore Orioles",
            "ORIOLES": "Baltimore Orioles",
            "MINNESOTA": "Minnesota Twins",
            "TWINS": "Minnesota Twins",
            "CLEVELAND": "Cleveland Guardians",
            "GUARDIANS": "Cleveland Guardians",
            "DETROIT": "Detroit Tigers",
            "TIGERS": "Detroit Tigers",
            "CHI WHITE SOX": "Chicago White Sox",
            "WHITE SOX": "Chicago White Sox",
            "KANSAS CITY": "Kansas City Royals",
            "ROYALS": "Kansas City Royals",
            "HOUSTON": "Houston Astros",
            "ASTROS": "Houston Astros",
            "SEATTLE": "Seattle Mariners",
            "MARINERS": "Seattle Mariners",
            "TEXAS": "Texas Rangers",
            "RANGERS": "Texas Rangers",
            "OAKLAND": "Athletics",
            "ATHLETICS": "Athletics",
            "LA ANGELS": "Los Angeles Angels",
            "ANGELS": "Los Angeles Angels",
            "NY METS": "New York Mets",
            "METS": "New York Mets",
            "ATLANTA": "Atlanta Braves",
            "BRAVES": "Atlanta Braves",
            "PHILADELPHIA": "Philadelphia Phillies",
            "PHILLIES": "Philadelphia Phillies",
            "MIAMI": "Miami Marlins",
            "MARLINS": "Miami Marlins",
            "WASHINGTON": "Washington Nationals",
            "NATIONALS": "Washington Nationals",
            "ST LOUIS": "St. Louis Cardinals",
            "CARDINALS": "St. Louis Cardinals",
            "MILWAUKEE": "Milwaukee Brewers",
            "BREWERS": "Milwaukee Brewers",
            "CHI CUBS": "Chicago Cubs",
            "CUBS": "Chicago Cubs",
            "CINCINNATI": "Cincinnati Reds",
            "REDS": "Cincinnati Reds",
            "PITTSBURGH": "Pittsburgh Pirates",
            "PIRATES": "Pittsburgh Pirates",
            "LA DODGERS": "Los Angeles Dodgers",
            "DODGERS": "Los Angeles Dodgers",
            "SAN DIEGO": "San Diego Padres",
            "PADRES": "San Diego Padres",
            "SAN FRANCISCO": "San Francisco Giants",
            "GIANTS": "San Francisco Giants",
            "ARIZONA": "Arizona Diamondbacks",
            "DIAMONDBACKS": "Arizona Diamondbacks",
            "COLORADO": "Colorado Rockies",
            "ROCKIES": "Colorado Rockies",
        }
    
    def normalizar_nombre(self, nombre):
        """Convierte nombres de Caliente al formato estándar MLB"""
        nombre_upper = nombre.upper().strip()
        
        # Buscar en mapeo exacto
        if nombre_upper in self.team_mapping:
            return self.team_mapping[nombre_upper]
        
        # Buscar coincidencia parcial
        for key, value in self.team_mapping.items():
            if key in nombre_upper or nombre_upper in key:
                return value
        
        return nombre.strip()
    
    def get_mlb_odds(self):
        """Obtiene odds de MLB desde Caliente.mx"""
        print("=" * 60)
        print("🎲 OBTENIENDO ODDS MLB - CALIENTE.MX")
        print("=" * 60)
        
        odds_totales = {}
        
        for url_path in self.urls_mlb:
            url = f"{self.base_url}{url_path}"
            
            try:
                print(f"\n🌐 Probando: {url}")
                response = requests.get(url, headers=self.headers, timeout=15)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Buscar elementos con odds
                    # Método 1: Buscar por clases comunes de Caliente
                    odds_elements = []
                    
                    # Clases típicas de Caliente para odds
                    for class_name in ['mkt_cupon', 'event-row', 'odds-row', 'bet-option']:
                        elements = soup.find_all(['tr', 'div'], class_=class_name)
                        if elements:
                            odds_elements.extend(elements)
                    
                    # Método 2: Buscar texto con formato de odds
                    text_content = soup.get_text()
                    
                    # Patrón: Nombre equipo + (+/- número)
                    pattern = re.compile(r'([A-Za-z]{3,15}(?:\s[A-Za-z]{3,15})?)\s*([+-]\d{3,4})')
                    matches = pattern.findall(text_content)
                    
                    print(f"  📊 {len(matches)} parejas equipo/odds encontradas")
                    
                    for match in matches[:30]:  # Máximo 30
                        equipo = self.normalizar_nombre(match[0])
                        odds = match[1]
                        
                        if equipo and len(equipo) > 3:
                            odds_totales[equipo] = odds
                            print(f"    ✅ {equipo}: {odds}")
                    
                    if len(odds_totales) >= 4:
                        break
                        
            except Exception as e:
                logger.error(f"Fallo al obtener odds de Caliente en URL {url_path}: {e}")
                continue
        
        # Guardar caché
        if odds_totales:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(odds_totales, f, ensure_ascii=False, indent=2)
            print(f"\n✅ {len(odds_totales)} odds guardadas en caché")
        else:
            print("\n⚠️ No se encontraron odds, usando caché anterior...")
            odds_totales = self._cargar_cache()
        
        return odds_totales
    
    def _cargar_cache(self):
        """Carga odds desde archivo caché"""
        import os
        if os.path.exists(self.cache_file):
            with open(self.cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    
    def get_odds_para_equipo(self, equipo_mlb):
        """Obtiene odds para un equipo específico"""
        todas_odds = self.get_mlb_odds()
        
        # Buscar coincidencia exacta
        if equipo_mlb in todas_odds:
            return todas_odds[equipo_mlb]
        
        # Buscar coincidencia parcial
        for nombre, odds in todas_odds.items():
            if equipo_mlb.upper() in nombre.upper() or nombre.upper() in equipo_mlb.upper():
                return odds
        
        return "N/A"
    
    def actualizar_resultados(self, resultados_json_path):
        """Actualiza resultados_finales_corregidos.json con odds de Caliente"""
        import os
        
        if not os.path.exists(resultados_json_path):
            print(f"❌ No existe {resultados_json_path}")
            return 0
        
        with open(resultados_json_path, "r", encoding="utf-8") as f:
            resultados = json.load(f)
        
        odds = self.get_mlb_odds()
        actualizados = 0
        
        for resultado in resultados:
            away = resultado.get('away', '')
            home = resultado.get('home', '')
            
            away_odds = self.get_odds_para_equipo(away)
            home_odds = self.get_odds_para_equipo(home)
            
            if away_odds != "N/A" or home_odds != "N/A":
                if 'odds' not in resultado:
                    resultado['odds'] = {
                        "moneyline": {
                            "away": away_odds,
                            "home": home_odds
                        },
                        "over_under": "N/A"
                    }
                else:
                    resultado['odds']['moneyline']['away'] = away_odds
                    resultado['odds']['moneyline']['home'] = home_odds
                
                actualizados += 1
        
        with open(resultados_json_path, "w", encoding="utf-8") as f:
            json.dump(resultados, f, ensure_ascii=False, indent=2)
        
        print(f"✅ {actualizados} juegos actualizados con odds")
        return actualizados


# Prueba rápida
if __name__ == "__main__":
    scraper = CalienteOddsScraper()
    odds = scraper.get_mlb_odds()
    
    if odds:
        print(f"\n🎯 RESUMEN: {len(odds)} equipos con odds")
        print("\n📊 PRIMEROS 10:")
        for i, (equipo, odd) in enumerate(list(odds.items())[:10]):
            print(f"  {i+1}. {equipo}: {odd}")
        
        # Actualizar resultados
        scraper.actualizar_resultados("resultados_finales_corregidos.json")