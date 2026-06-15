# -*- coding: utf-8 -*-
"""MÓDULO DE CLIMA - Simulado + Preparado para API real"""
import json
import random
from datetime import datetime

class ClimaMLB:
    """Obtiene condiciones climáticas para partidos MLB"""
    
    def __init__(self):
        self.estadios_clima = {
            "Fenway Park": {"temp_base": 55, "viento_base": 8, "viento_dir": "Out"},
            "Yankee Stadium": {"temp_base": 60, "viento_base": 6, "viento_dir": "Out"},
            "Dodger Stadium": {"temp_base": 72, "viento_base": 5, "viento_dir": "Out"},
            "Wrigley Field": {"temp_base": 58, "viento_base": 12, "viento_dir": "Out"},
            "Coors Field": {"temp_base": 65, "viento_base": 4, "viento_dir": "Out"},
            "Progressive Field": {"temp_base": 55, "viento_base": 9, "viento_dir": "In"},
            "Globe Life Field": {"temp_base": 75, "viento_base": 3, "viento_dir": "None"},
            "Rogers Centre": {"temp_base": 68, "viento_base": 0, "viento_dir": "None"},
            "PNC Park": {"temp_base": 58, "viento_base": 7, "viento_dir": "Out"},
            "Petco Park": {"temp_base": 70, "viento_base": 6, "viento_dir": "Out"},
            "Target Field": {"temp_base": 50, "viento_base": 10, "viento_dir": "In"},
            "Tropicana Field": {"temp_base": 72, "viento_base": 0, "viento_dir": "None"},
            "Rate Field": {"temp_base": 55, "viento_base": 8, "viento_dir": "Out"},
        }
    
    def obtener_clima(self, estadio):
        """Obtiene clima para un estadio (simulado o real)"""
        if estadio in self.estadios_clima:
            base = self.estadios_clima[estadio]
            
            # Variación aleatoria realista
            temp = base["temp_base"] + random.randint(-8, 8)
            viento = base["viento_base"] + random.randint(-3, 5)
            viento = max(0, viento)
            
            # Determinar descripción
            if temp > 85:
                desc = "Caluroso"
            elif temp > 70:
                desc = "Templado"
            elif temp > 55:
                desc = "Fresco"
            else:
                desc = "Frío"
            
            if random.random() > 0.7:
                desc += " con lluvia ligera"
            elif random.random() > 0.8:
                desc += " con nubes dispersas"
            
            return {
                "estadio": estadio,
                "descripcion": desc,
                "temp": temp,
                "wind_speed": viento,
                "wind_dir": base["viento_dir"] if viento > 3 else "None",
                "humedad": random.randint(30, 80),
            }
        
        # Datos por defecto
        return {
            "estadio": estadio,
            "descripcion": "Normal",
            "temp": 70,
            "wind_speed": 5,
            "wind_dir": "None",
            "humedad": 50,
        }
    
    def condiciones_extremas(self, clima):
        """Detecta condiciones que afectan significativamente el juego"""
        alertas = []
        
        if clima["wind_speed"] > 15:
            alertas.append(f"💨 VIENTO FUERTE: {clima['wind_speed']}mph - Favorece OVER")
        if clima["temp"] > 90:
            alertas.append(f"🌡️ CALOR EXTREMO: {clima['temp']}°F - Bola viaja +10%")
        if clima["temp"] < 45:
            alertas.append(f"🥶 FRÍO: {clima['temp']}°F - Bola viaja -8%")
        if clima["humedad"] > 75:
            alertas.append(f"💧 HUMEDAD ALTA: {clima['humedad']}% - Bola pesa más")
        
        return alertas

# Prueba
if __name__ == "__main__":
    clima_mlb = ClimaMLB()
    
    for estadio in ["Fenway Park", "Wrigley Field", "Coors Field"]:
        c = clima_mlb.obtener_clima(estadio)
        print(f"\n{estadio}:")
        print(f"   {c['descripcion']}, {c['temp']}°F, Viento {c['wind_speed']}mph {c['wind_dir']}")
        
        alertas = clima_mlb.condiciones_extremas(c)
        for a in alertas:
            print(f"   {a}")
