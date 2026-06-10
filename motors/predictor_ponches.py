# -*- coding: utf-8 -*-
"""PREDICTOR DE PONCHES (STRIKEOUTS) - MLB"""
import json
import os
import sqlite3
import pandas as pd
from datetime import datetime
from collections import defaultdict

class PredictorPonches:
    """Predice probabilidad de ponches para pitchers y bateadores"""
    
    def __init__(self, ruta_lanzadores="data/stats_lanzadores_hoy.json"):
        self.pitchers_k = {}  # K/9 de pitchers
        self.bateadores_k = {}  # Tasa de ponches de bateadores
        self.ruta_lanzadores = ruta_lanzadores
        self.cargar_datos()
    
    def cargar_datos(self):
        """Carga datos dinámicos de la API de MLB y stats de bateadores"""
        if os.path.exists(self.ruta_lanzadores):
            try:
                with open(self.ruta_lanzadores, "r", encoding="utf-8") as f:
                    datos_api = json.load(f)
                    for equipo, info in datos_api.items():
                        self.pitchers_k[info['nombre']] = {
                            "k9": info['k9'],
                            "equipo": equipo,
                            "avg_innings": info.get('avg_innings', 5.6)
                        }
            except Exception as e: print(f"Error cargando pitchers: {e}")
        
        # --- CARGA DINÁMICA DE BATEADORES DESDE DB ---
        try:
            conn = sqlite3.connect("data/betting_stats.db")
            df = pd.read_sql("SELECT nombre, equipo, avg as k_rate FROM player_stats WHERE deporte = 'mlb'", conn)
            # Aquí asumimos que guardas la tasa de K en el campo avg o similar
            self.bateadores_k = df.set_index('nombre').to_dict('index')
            conn.close()
        except:
            self.bateadores_k = {} # Fallback a vacío para forzar scraping
    
    def predecir_ponches_pitcher(self, pitcher_nombre, equipo_rival, over_under_line=5.5):
        """
        Predicción dinámica basada en (K/9 / 9) * Innings_Proyectados * Factor_Matchup
        """
        if pitcher_nombre not in self.pitchers_k:
            return {"recomendacion": "SIN DATOS", "confianza": 0, "k_proyectados": 0}
        
        pitcher = self.pitchers_k[pitcher_nombre]
        k9 = pitcher["k9"]
        innings_proy = pitcher.get("avg_innings", 5.6)
        
        # Cálculo base profesional
        k_esperados = (k9 / 9) * innings_proy
        
        # Cruce con bateadores del equipo rival
        bateadores_rivales = [n for n, d in self.bateadores_k.items() if d.get('equipo') == equipo_rival]
        if bateadores_rivales:
            k_avg_rivales = sum(self.bateadores_k.get(b, {}).get("k_rate", 20) for b in bateadores_rivales) / max(len(bateadores_rivales), 1)
            factor_matchup = k_avg_rivales / 22.0  # 22% es el benchmark MLB
            k_esperados *= factor_matchup
        
        k_esperados = round(k_esperados, 1)
        diff = k_esperados - over_under_line
        confianza = min(95, 50 + int(abs(diff) * 15))

        return {
            "pitcher": pitcher_nombre,
            "k_proyectados": k_esperados,
            "recomendacion": f"{'OVER' if diff > 0 else 'UNDER'} {over_under_line}",
            "confianza": f"{confianza}%"
        }
    
    def obtener_top_pitchers_k(self, limite=5):
        """Retorna los pitchers con más K/9"""
        return sorted(self.pitchers_k.items(), key=lambda x: x[1]["k9"], reverse=True)[:limite]

# Prueba
if __name__ == "__main__":
    pp = PredictorPonches()
    
    # Probar con algunos pitchers
    for pitcher in ["Gerrit Cole", "Spencer Strider", "Steven Matz"]:
        resultado = pp.predecir_ponches_pitcher(
            pitcher,
            ["Aaron Judge", "Kyle Schwarber"],  # bateadores que se ponchan mucho
            5.5
        )
        print(f"\n{resultado['pitcher']}:")
        print(f"   K/9: {resultado['k9']}")
        print(f"   K proyectados: {resultado['k_proyectados']}")
        print(f"   Recomendación: {resultado['recomendacion']}")
        print(f"   Confianza: {resultado['confianza']}%")
