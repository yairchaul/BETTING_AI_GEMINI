# -*- coding: utf-8 -*-
"""
mlb_scraper.py - ALIAS PARA espn_mlb.py
Mantiene compatibilidad con el sistema eliminando duplicidad.
"""
from espn_mlb import ESPN_MLB_Mejorado
from utils.fuzzy_matching import normalizar_equipo

def neon_name(name):
    return normalizar_equipo(name)

# Redirección de clase para evitar errores de importación en otros módulos
ESPN_MLB = ESPN_MLB_Mejorado

if __name__ == "__main__":
    scraper = ESPN_MLB_Mejorado()
    for p in scraper.get_games():
        print(f"✅ {p['visitante']} vs {p['local']} | Odds: {p['odds']['moneyline']['visitante']}")
