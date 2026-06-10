import sys
# -*- coding: utf-8 -*-
"""SCRAPER CALIENTE.MX - PITCHERS + ODDS (SELENIUM)"""
import json
import time
import os
from datetime import datetime

# --- PARCHE DE CONSOLA WINDOWS (UTF-8) ---
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_OK = True # Activado para usar Selenium
except ImportError:
    SELENIUM_OK = False
    print("⚠️ Selenium no instalado. Usa: pip install selenium webdriver-manager")

class CalienteMLBScraper:
    def __init__(self):
        if not SELENIUM_OK:
            self.driver = None
            return
            
        try:
            self.options = Options()
            self.options.add_argument("--headless")  # Quitar para ver el navegador
            self.options.add_argument("--no-sandbox")
            self.options.add_argument("--disable-dev-shm-usage")
            self.options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            
            self.driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=self.options
            )
        except Exception as e:
            print(f"⚠️ No se pudo iniciar Chrome: {e}")
            self.driver = None
        
        self.url = "https://www.caliente.mx/deportes/beisbol/mlb"
    
    def extraer_lanzadores_y_odds(self):
        if not self.driver:
            print("❌ Selenium no disponible. Usando datos manuales...")
            return self._usar_datos_manuales()
        
        print(f"🔍 Accediendo a Caliente MLB...")
        
        try:
            self.driver.get(self.url)
            time.sleep(5)  # Esperar carga
            
            juegos_data = []
            
            # Intentar diferentes selectores
            selectores = ['event-card', 'ms-event-card', 'matchup-card', 'game-card']
            
            eventos = []
            for selector in selectores:
                try:
                    eventos = self.driver.find_elements(By.CLASS_NAME, selector)
                    if eventos:
                        print(f"   ✅ Selector '{selector}': {len(eventos)} eventos")
                        break
                except:
                    continue
            
            if not eventos: # Si no encuentra eventos por clase, intenta por texto
                # Buscar por cualquier elemento que contenga odds
                body_text = self.driver.find_element(By.TAG_NAME, 'body').text
                print(f"   Body preview: {body_text[:200]}...")
                return self._usar_datos_manuales()
            
            for evento in eventos:
                try:
                    text = evento.text
                    
                    # Buscar patrones de equipos y pitchers
                    import re
                    
                    # Patrón: "Equipo (Pitcher)" con odds
                    matches = re.findall(r'([A-Za-z\s]+)\s*\(([^)]+)\)', text)
                    odds_matches = re.findall(r'[-+]\d{3,4}', text)
                    
                    if len(matches) >= 2:
                        v_team, v_pitcher = matches[0]
                        h_team, h_pitcher = matches[1]
                        
                        juegos_data.append({
                            "visitante": v_team.strip(),
                            "lanzador_v": v_pitcher.strip(),
                            "momio_v": odds_matches[0] if len(odds_matches) > 0 else "N/A",
                            "local": h_team.strip(),
                            "lanzador_h": h_pitcher.strip(),
                            "momio_h": odds_matches[1] if len(odds_matches) > 1 else "N/A",
                        })
                        print(f"   ✅ {v_team.strip()} ({v_pitcher.strip()}) @ {h_team.strip()} ({h_pitcher.strip()})")
                
                except Exception as e:
                    continue
            
            if juegos_data:
                self._guardar_y_actualizar(juegos_data)
                return juegos_data
            else:
                return self._usar_datos_manuales()
        
        except Exception as e:
            sys.stdout.write(f"❌ Error en Caliente Scraper: {e}\n")
            return self._usar_datos_manuales()
        finally:
            if self.driver:
                self.driver.quit()
    
    def _usar_datos_manuales(self):
        """Fallback: usa datos manuales"""
        sys.stdout.write("📋 Usando datos manuales de pitchers...\n")
        
        PITCHERS_REALES = {
            "Tampa Bay Rays": "Steven Matz",
            "Cleveland Guardians": "Logan Allen",
            "St. Louis Cardinals": "Sonny Gray",
            "Pittsburgh Pirates": "Mitch Keller",
            "Boston Red Sox": "Brayan Bello",
            "Toronto Blue Jays": "Kevin Gausman",
            "Los Angeles Angels": "Reid Detmers",
            "Chicago White Sox": "Garrett Crochet",
            "Seattle Mariners": "Luis Castillo",
            "Minnesota Twins": "Pablo Lopez",
            "New York Yankees": "Gerrit Cole",
            "Texas Rangers": "Jacob deGrom",
            "Chicago Cubs": "Justin Steele",
            "San Diego Padres": "Yu Darvish",
            "Miami Marlins": "Jesus Luzardo",
            "Los Angeles Dodgers": "Yoshinobu Yamamoto",
        }
        
        try:
            with open("resultados_finales_corregidos.json", "r", encoding="utf-8") as f:
                partidos = json.load(f)
            
            juegos = []
            for p in partidos:
                v = p.get("visitante", "")
                l = p.get("local", "")
                pv = PITCHERS_REALES.get(v, "TBD")
                pl = PITCHERS_REALES.get(l, "TBD")
                
                p["pitchers"] = {
                    "visitante": {"nombre": pv},
                    "local": {"nombre": pl}
                }
                
                juegos.append({
                    "visitante": v, "lanzador_v": pv,
                    "local": l, "lanzador_h": pl,
                    "momio_v": p.get("odds", {}).get("moneyline", {}).get("visitante", "N/A"),
                    "momio_h": p.get("odds", {}).get("moneyline", {}).get("local", "N/A"),
                })
            
            self._guardar_y_actualizar(juegos)
            return juegos
        except Exception as e:
            sys.stdout.write(f"❌ Error en datos manuales: {e}\n")
            return []
    
    def _guardar_y_actualizar(self, juegos_data):
        """Guarda datos y actualiza archivos del sistema"""
        os.makedirs("data", exist_ok=True)
        
        # Guardar odds de Caliente
        with open("data/odds_caliente_hoy.json", "w", encoding="utf-8") as f:
            json.dump(juegos_data, f, indent=2, ensure_ascii=False)
        sys.stdout.write(f"\n📂 data/odds_caliente_hoy.json: {len(juegos_data)} juegos\n")
        
        # Actualizar pitchers_hoy_selenium.json
        juegos_pitchers = []
        for j in juegos_data:
            juegos_pitchers.append({
                "away_team": j["visitante"],
                "home_team": j["local"],
                "away_pitcher": j["lanzador_v"],
                "home_pitcher": j["lanzador_h"],
            })
        
        with open("pitchers_hoy_selenium.json", "w", encoding="utf-8") as f:
            json.dump({
                "juegos": juegos_pitchers,
                "fuente": "Caliente.mx",
                "actualizado": datetime.now().strftime("%Y-%m-%d %H:%M")
            }, f, indent=2, ensure_ascii=False)
        sys.stdout.write("✅ pitchers_hoy_selenium.json actualizado\n")
        # Actualizar resultados_finales_corregidos.json
        try:
            with open("resultados_finales_corregidos.json", "r", encoding="utf-8") as f:
                partidos = json.load(f)
            
            for j in juegos_data:
                for p in partidos:
                    if j["visitante"].lower() in p.get("visitante", "").lower():
                        p["pitchers"] = {
                            "visitante": {"nombre": j["lanzador_v"]},
                            "local": {"nombre": j["lanzador_h"]}
                        }
                        if j["momio_v"] != "N/A":
                            p["odds"]["moneyline"] = {
                                "visitante": j["momio_v"],
                                "local": j["momio_h"]
                            }
                        break
            
            with open("resultados_finales_corregidos.json", "w", encoding="utf-8") as f:
                json.dump(partidos, f, indent=2, ensure_ascii=False)
            sys.stdout.write("✅ resultados_finales_corregidos.json actualizado\n")
        except Exception as e:
            sys.stdout.write(f"⚠️ Error actualizando resultados_finales_corregidos.json: {e}\n")

if __name__ == "__main__":
    scraper = CalienteMLBScraper()
    datos = scraper.extraer_lanzadores_y_odds()
    
    if datos:
        sys.stdout.write(f"\n✅ {len(datos)} juegos con pitchers y odds\n")
        sys.stdout.write("\n📋 PITCHERS EXTRAÍDOS:\n")
        for d in datos[:5]:
            sys.stdout.write(f"   {d['visitante']}: {d['lanzador_v']} ({d['momio_v']})\n")
            sys.stdout.write(f"   {d['local']}: {d['lanzador_h']} ({d['momio_h']})\n")
            sys.stdout.write("\n")
    
    sys.stdout.write("\n🚀 streamlit run main_vision_completo.py\n")

