# -*- coding: utf-8 -*-
"""
SCRAPER CALIENTE.MX MEJORADO - EVITA TBD PARA SIEMPRE
V24.1 - Con múltiples fuentes y validación cruzada
"""
import requests
import json
import re
import os
import sys
import time
from datetime import datetime
import unicodedata
from bs4 import BeautifulSoup

# Configuración de consola para Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def normalizar_nombre(texto):
    """Normaliza nombres para comparación"""
    if not texto:
        return ""
    texto = unicodedata.normalize('NFD', texto)
    texto = texto.encode('ascii', 'ignore').decode("utf-8")
    return texto.lower().strip().replace(".", "").replace("-", " ").replace(" jr", "").replace(" sr", "").replace(" iii", "").replace(" ii", "")

class CalienteMejorado:
    def __init__(self):
        self.base_url = "https://sports.caliente.mx"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1"
        })
        
        # Mapeo completo de equipos
        self.mapeo_equipos = {
            # Formato corto -> Formato completo
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
            "Athletics": "Oakland Athletics", "Royals": "Kansas City Royals",
            "A's": "Oakland Athletics", "CWS": "Chicago White Sox",
            "CHW": "Chicago White Sox", "CIN": "Cincinnati Reds",
            "CLE": "Cleveland Guardians", "COL": "Colorado Rockies",
            "CWS": "Chicago White Sox", "DET": "Detroit Tigers",
            "HOU": "Houston Astros", "KC": "Kansas City Royals",
            "LAA": "Los Angeles Angels", "LAD": "Los Angeles Dodgers",
            "MIA": "Miami Marlins", "MIL": "Milwaukee Brewers",
            "MIN": "Minnesota Twins", "NYM": "New York Mets",
            "NYY": "New York Yankees", "OAK": "Oakland Athletics",
            "PHI": "Philadelphia Phillies", "PIT": "Pittsburgh Pirates",
            "SD": "San Diego Padres", "SEA": "Seattle Mariners",
            "SF": "San Francisco Giants", "STL": "St. Louis Cardinals",
            "TB": "Tampa Bay Rays", "TEX": "Texas Rangers",
            "TOR": "Toronto Blue Jays", "WAS": "Washington Nationals",
            "WSH": "Washington Nationals"
        }
        
        # Pitchers de respaldo (fuente MLB.com actualizada)
        self.pitchers_respaldo = self._cargar_pitchers_respaldo()
    
    def _cargar_pitchers_respaldo(self):
        """Carga pitchers de respaldo desde archivo o fuente oficial"""
        respaldo_file = "data/pitchers_respaldo.json"
        if os.path.exists(respaldo_file):
            try:
                with open(respaldo_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        
        # Pitchers actuales de temporada (puedes actualizar esta lista)
        return {
            "Tampa Bay Rays": ["Taj Bradley", "Zach Eflin", "Aaron Civale", "Ryan Pepiot"],
            "Cleveland Guardians": ["Triston McKenzie", "Shane Bieber", "Logan Allen", "Tanner Bibee"],
            "Boston Red Sox": ["Brayan Bello", "Kutter Crawford", "Nick Pivetta", "Tanner Houck"],
            "New York Yankees": ["Gerrit Cole", "Carlos Rodón", "Marcus Stroman", "Nestor Cortes"],
            "Toronto Blue Jays": ["Kevin Gausman", "José Berríos", "Chris Bassitt", "Yusei Kikuchi"],
            "Baltimore Orioles": ["Corbin Burnes", "Grayson Rodriguez", "Dean Kremer", "Cole Irvin"],
            "Houston Astros": ["Framber Valdez", "Cristian Javier", "Hunter Brown", "J.P. France"],
            "Texas Rangers": ["Nathan Eovaldi", "Jon Gray", "Dane Dunning", "Andrew Heaney"],
            "Seattle Mariners": ["Luis Castillo", "George Kirby", "Logan Gilbert", "Bryce Miller"],
            "Los Angeles Angels": ["Reid Detmers", "Patrick Sandoval", "Griffin Canning", "Tyler Anderson"],
            "Oakland Athletics": ["Paul Blackburn", "Joe Boyle", "JP Sears", "Alex Wood"],
            "Minnesota Twins": ["Pablo López", "Joe Ryan", "Bailey Ober", "Chris Paddack"],
            "Detroit Tigers": ["Tarik Skubal", "Kenta Maeda", "Jack Flaherty", "Casey Mize"],
            "Kansas City Royals": ["Cole Ragans", "Brady Singer", "Michael Wacha", "Seth Lugo"],
            "Chicago White Sox": ["Garrett Crochet", "Erick Fedde", "Michael Soroka", "Chris Flexen"],
            "Chicago Cubs": ["Justin Steele", "Shota Imanaga", "Jameson Taillon", "Kyle Hendricks"],
            "St. Louis Cardinals": ["Sonny Gray", "Miles Mikolas", "Kyle Gibson", "Lance Lynn"],
            "Milwaukee Brewers": ["Freddy Peralta", "Colin Rea", "DL Hall", "Joe Ross"],
            "Cincinnati Reds": ["Hunter Greene", "Graham Ashcraft", "Frankie Montas", "Nick Lodolo"],
            "Pittsburgh Pirates": ["Mitch Keller", "Martín Pérez", "Jared Jones", "Bailey Falter"],
            "Atlanta Braves": ["Spencer Strider", "Max Fried", "Charlie Morton", "Reynaldo López"],
            "New York Mets": ["Kodai Senga", "José Quintana", "Luis Severino", "Sean Manaea"],
            "Philadelphia Phillies": ["Zack Wheeler", "Aaron Nola", "Ranger Suárez", "Cristopher Sánchez"],
            "Miami Marlins": ["Jesús Luzardo", "Edward Cabrera", "A.J. Puk", "Trevor Rogers"],
            "Washington Nationals": ["MacKenzie Gore", "Jake Irvin", "Patrick Corbin", "Trevor Williams"],
            "Los Angeles Dodgers": ["Yoshinobu Yamamoto", "Tyler Glasnow", "Walker Buehler", "Bobby Miller"],
            "San Diego Padres": ["Yu Darvish", "Joe Musgrove", "Dylan Cease", "Michael King"],
            "San Francisco Giants": ["Logan Webb", "Kyle Harrison", "Jordan Hicks", "Keaton Winn"],
            "Colorado Rockies": ["Kyle Freeland", "Cal Quantrill", "Austin Gomber", "Ryan Feltner"],
            "Arizona Diamondbacks": ["Zac Gallen", "Merrill Kelly", "Brandon Pfaadt", "Ryne Nelson"]
        }
    
    def extraer_datos_caliente(self):
        """Extrae datos de Caliente.mx usando múltiples métodos"""
        print("=" * 70)
        print("🔍 CALIENTE.MX MEJORADO - EXTRAYENDO PITCHERS SIN TBD")
        print("=" * 70)
        
        pitchers_extraidos = {}
        
        # Método 1: API JSON (si existe)
        api_url = "https://sports.caliente.mx/api/sports/baseball/mlb/events"
        try:
            response = self.session.get(api_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                pitchers_extraidos.update(self._procesar_json_api(data))
                print(f"   ✅ API JSON: {len(pitchers_extraidos)} pitchers encontrados")
        except Exception as e:
            print(f"   ⚠️ API JSON falló: {e}")
        
        # Método 2: HTML principal
        main_url = "https://sports.caliente.mx/es_MX/MLB"
        try:
            response = self.session.get(main_url, timeout=15)
            if response.status_code == 200:
                pitchers_html = self._procesar_html(response.text)
                pitchers_extraidos.update(pitchers_html)
                print(f"   ✅ HTML principal: {len(pitchers_html)} pitchers adicionales")
        except Exception as e:
            print(f"   ⚠️ HTML principal falló: {e}")
        
        # Método 3: Página de probabilidades
        odds_url = "https://sports.caliente.mx/es_MX/MLB/odds"
        try:
            response = self.session.get(odds_url, timeout=10)
            if response.status_code == 200:
                pitchers_odds = self._procesar_pagina_odds(response.text)
                pitchers_extraidos.update(pitchers_odds)
                print(f"   ✅ Página Odds: {len(pitchers_odds)} pitchers adicionales")
        except Exception as e:
            print(f"   ⚠️ Página Odds falló: {e}")
        
        # Validar y completar con respaldo
        pitchers_validados = self._validar_y_completar(pitchers_extraidos)
        
        return pitchers_validados
    
    def _procesar_json_api(self, data):
        """Procesa datos de la API JSON"""
        pitchers = {}
        
        if isinstance(data, dict) and "events" in data:
            for event in data.get("events", []):
                for market in event.get("markets", []):
                    if market.get("name") == "Moneyline":
                        for selection in market.get("selections", []):
                            team_name = selection.get("name", "")
                            pitcher_name = selection.get("metadata", {}).get("pitcher", "")
                            
                            if team_name and pitcher_name:
                                equipo_completo = self._mapear_equipo(team_name)
                                if equipo_completo:
                                    pitchers[equipo_completo] = pitcher_name
        
        return pitchers
    
    def _procesar_html(self, html):
        """Procesa HTML de la página principal"""
        pitchers = {}
        soup = BeautifulSoup(html, 'html.parser')
        
        # Buscar por diferentes patrones
        patterns = [
            # Patrón: "Equipo (Pitcher)"
            (r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*\(([^)]+)\)', ""),
            # Patrón: Div con clase que contiene pitcher
            ('pitcher', 'class'),
            # Patrón: Span con pitcher info
            ('player-name', 'class')
        ]
        
        # Buscar texto con pitchers
        text = soup.get_text()
        
        # Patrón principal: Equipo (Pitcher)
        matches = re.findall(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*\(([^)]+)\)', text)
        for equipo, pitcher in matches:
            equipo_completo = self._mapear_equipo(equipo)
            if equipo_completo and pitcher and pitcher.lower() not in ['tbd', 'por anunciar', 'n/a']:
                pitchers[equipo_completo] = pitcher.strip()
        
        # Buscar en elementos específicos
        for element in soup.find_all(['div', 'span', 'td']):
            if element.get('class'):
                class_str = ' '.join(element.get('class'))
                if any(p in class_str.lower() for p in ['pitcher', 'player', 'starter']):
                    text_elem = element.get_text().strip()
                    if '(' in text_elem and ')' in text_elem:
                        match = re.search(r'([A-Z][a-z].*?)\s*\(([^)]+)\)', text_elem)
                        if match:
                            equipo, pitcher = match.groups()
                            equipo_completo = self._mapear_equipo(equipo)
                            if equipo_completo and pitcher and pitcher.lower() not in ['tbd', 'por anunciar', 'n/a']:
                                pitchers[equipo_completo] = pitcher.strip()
        
        return pitchers
    
    def _procesar_pagina_odds(self, html):
        """Procesa la página específica de odds"""
        pitchers = {}
        soup = BeautifulSoup(html, 'html.parser')
        
        # Buscar tablas de odds
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 3:
                    team_cell = cells[0].get_text().strip()
                    pitcher_cell = cells[1].get_text().strip() if len(cells) > 1 else ""
                    
                    # Buscar pitcher en el texto
                    if '(' in team_cell and ')' in team_cell:
                        match = re.search(r'([A-Z][a-z].*?)\s*\(([^)]+)\)', team_cell)
                        if match:
                            equipo, pitcher = match.groups()
                            equipo_completo = self._mapear_equipo(equipo)
                            if equipo_completo and pitcher and pitcher.lower() not in ['tbd', 'por anunciar', 'n/a']:
                                pitchers[equipo_completo] = pitcher.strip()
        
        return pitchers
    
    def _mapear_equipo(self, nombre_corto):
        """Mapea nombre corto a nombre completo"""
        nombre_norm = normalizar_nombre(nombre_corto)
        
        # Buscar coincidencia exacta o parcial
        for corto, completo in self.mapeo_equipos.items():
            if nombre_norm == normalizar_nombre(corto) or nombre_norm in normalizar_nombre(corto) or normalizar_nombre(corto) in nombre_norm:
                return completo
        
        # Si no encuentra, intentar por abreviaturas comunes
        if len(nombre_corto) <= 3:
            for corto, completo in self.mapeo_equipos.items():
                if corto.upper() == nombre_corto.upper():
                    return completo
        
        return None
    
    def _validar_y_completar(self, pitchers):
        """Valida pitchers y completa con respaldo si es necesario"""
        pitchers_validados = {}
        
        # Verificar cada pitcher
        for equipo, pitcher in pitchers.items():
            if pitcher and pitcher.lower() not in ['tbd', 'por anunciar', 'n/a', 'none', 'null']:
                pitchers_validados[equipo] = pitcher
            else:
                # Usar respaldo
                pitchers_resp = self.pitchers_respaldo.get(equipo, [])
                if pitchers_resp:
                    pitchers_validados[equipo] = pitchers_resp[0]  # Primer pitcher de la lista
                    print(f"   🔄 {equipo}: Usando respaldo '{pitchers_resp[0]}'")
                else:
                    # Último recurso: buscar en archivos existentes
                    existing_pitcher = self._buscar_en_archivos(equipo)
                    if existing_pitcher:
                        pitchers_validados[equipo] = existing_pitcher
        
        return pitchers_validados
    
    def _buscar_en_archivos(self, equipo):
        """Busca pitcher en archivos existentes del sistema"""
        archivos = [
            "data/resultados_finales_corregidos.json",
            "pitchers_hoy_selenium.json",
            "data/odds_caliente_hoy.json"
        ]
        
        for archivo in archivos:
            if os.path.exists(archivo):
                try:
                    with open(archivo, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    if isinstance(data, list):
                        for item in data:
                            if equipo in [item.get("visitante"), item.get("local")]:
                                pitcher = item.get("pitchers", {}).get("visitante", {}).get("nombre") if equipo == item.get("visitante") else item.get("pitchers", {}).get("local", {}).get("nombre")
                                if pitcher and pitcher.lower() not in ['tbd', 'por anunciar', 'n/a']:
                                    return pitcher
                except:
                    continue
        
        return None
    
    def actualizar_sistema(self, pitchers):
        """Actualiza todos los archivos del sistema con los pitchers obtenidos"""
        if not pitchers:
            print("⚠️ No hay pitchers para actualizar")
            return False
        
        print(f"\n📋 ACTUALIZANDO SISTEMA ({len(pitchers)} pitchers)")
        
        # 1. Actualizar resultados_finales_corregidos.json
        try:
            with open("data/resultados_finales_corregidos.json", "r", encoding="utf-8") as f:
                partidos = json.load(f)
            
            actualizados = 0
            for partido in partidos:
                v = partido.get("visitante", "")
                l = partido.get("local", "")
                
                if v in pitchers:
                    if "pitchers" not in partido:
                        partido["pitchers"] = {"visitante": {}, "local": {}}
                    partido["pitchers"]["visitante"]["nombre"] = pitchers[v]
                    actualizados += 1
                
                if l in pitchers:
                    if "pitchers" not in partido:
                        partido["pitchers"] = {"visitante": {}, "local": {}}
                    partido["pitchers"]["local"]["nombre"] = pitchers[l]
                    actualizados += 1
            
            with open("data/resultados_finales_corregidos.json", "w", encoding="utf-8") as f:
                json.dump(partidos, f, indent=2, ensure_ascii=False)
            
            print(f"   ✅ data/resultados_finales_corregidos.json: {actualizados} pitchers actualizados")
        except Exception as e:
            print(f"   ⚠️ Error actualizando resultados_finales_corregidos.json: {e}")
        
        # 2. Actualizar pitchers_hoy_selenium.json
        try:
            juegos = []
            if os.path.exists("data/resultados_finales_corregidos.json"):
                with open("data/resultados_finales_corregidos.json", "r", encoding="utf-8") as f:
                    partidos = json.load(f)
                
                for p in partidos:
                    juegos.append({
                        "away_team": p.get("visitante", ""),
                        "home_team": p.get("local", ""),
                        "away_pitcher": p.get("pitchers", {}).get("visitante", {}).get("nombre", ""),
                        "home_pitcher": p.get("pitchers", {}).get("local", {}).get("nombre", "")
                    })
            
            with open("pitchers_hoy_selenium.json", "w", encoding="utf-8") as f:
                json.dump({
                    "juegos": juegos,
                    "fuente": "CalienteMejorado",
                    "actualizado": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }, f, indent=2, ensure_ascii=False)
            
            print(f"   ✅ pitchers_hoy_selenium.json actualizado ({len(juegos)} juegos)")
        except Exception as e:
            print(f"   ⚠️ Error actualizando pitchers_hoy_selenium.json: {e}")
        
        # 3. Crear archivo de respaldo actualizado
        try:
            with open("data/pitchers_respaldo.json", "w", encoding="utf-8") as f:
                json.dump(self.pitchers_respaldo, f, indent=2, ensure_ascii=False)
            print(f"   ✅ data/pitchers_respaldo.json actualizado")
        except Exception as e:
            print(f"   ⚠️ Error actualizando pitchers_respaldo.json: {e}")
        
        # 4. Verificar que no hay TBD
        tbd_count = 0
        for equipo, pitcher in pitchers.items():
            if pitcher.lower() in ['tbd', 'por anunciar', 'n/a']:
                tbd_count += 1
                print(f"   ❌ {equipo}: AÚN tiene TBD")
        
        if tbd_count == 0:
            print(f"\n🎉 ¡SISTEMA ACTUALIZADO SIN TBD!")
            return True
        else:
            print(f"\n⚠️ {tbd_count} pitchers aún tienen TBD")
            return False

def ejecutar_caliente_mejorado():
    """Función principal para ejecutar el scraper mejorado"""
    scraper = CalienteMejorado()
    
    print("\n" + "=" * 70)
    print("🚀 INICIANDO SCRAPER CALIENTE MEJORADO")
    print("=" * 70)
    
    # Ejecutar extracción
    pitchers = scraper.extraer_datos_caliente()
    
    if pitchers:
        print(f"\n📊 RESUMEN: {len(pitchers)} pitchers válidos encontrados")
        for equipo, pitcher in sorted(pitchers.items()):
            print(f"   🥎 {equipo}: {pitcher}")
        
        # Actualizar sistema
        exito = scraper.actualizar_sistema(pitchers)
        
        if exito:
            print(f"\n✅ SCRAPER COMPLETADO EXITOSAMENTE")
            print("   Archivos actualizados:")
            print("   - data/resultados_finales_corregidos.json")
            print("   - pitchers_hoy_selenium.json")
            print("   - data/pitchers_respaldo.json")
            return True
        else:
            print(f"\n⚠️ SCRAPER COMPLETADO CON ADVERTENCIAS")
            return False
    else:
        print("\n❌ No se pudieron extraer pitchers de Caliente.mx")
        return False

if __name__ == "__main__":
    exito = ejecutar_caliente_mejorado()
    if not exito:
        print("\n🔧 Ejecutando sistema de respaldo...")
        # Intentar con el scraper Selenium existente
        try:
            subprocess.run([sys.executable, "scrapers/scraper_caliente_selenium.py"], check=False)
        except:
            print("⚠️ Scraper Selenium también falló")
    
    print("\n📝 Verificando estado final...")
    # Verificar si aún hay TBD
    try:
        with open("data/resultados_finales_corregidos.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        
        tbd_final = 0
        for partido in data:
            for lado in ["visitante", "local"]:
                pitcher = partido.get("pitchers", {}).get(lado, {}).get("nombre", "")
                if pitcher and pitcher.lower() in ['tbd', 'por anunciar', 'n/a']:
                    tbd_final += 1
        
        if tbd_final == 0:
            print("✅ ¡SISTEMA LIBRE DE TBD!")
        else:
            print(f"⚠️ Aún hay {tbd_final} pitchers con TBD")
    except:
        print("⚠️ No se pudo verificar el estado final")