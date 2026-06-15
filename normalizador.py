# -*- coding: utf-8 -*-
"""Módulo de Traducción para Sincronizar NEON"""

TRADUCCIONES = {
    "Tampa Bay Rays": "Rayos de Tampa Bay",
    "Cleveland Guardians": "Guardianes de Cleveland",
    "Houston Astros": "Astros de Houston",
    "Atlanta Braves": "Bravos de Atlanta",
    "Washington Nationals": "Nacionales de Washington",
    "Detroit Tigers": "Tigres de Detroit",
    "Los Angeles Dodgers": "Dodgers de Los Angeles",
    "San Diego Padres": "Padres de San Diego",
    "Texas Rangers": "Vigilantes de Texas",
    "New York Yankees": "Yankees de Nueva York",
    "Boston Red Sox": "Medias Rojas de Boston",
    "Chicago Cubs": "Cachorros de Chicago",
    "Chicago White Sox": "Medias Blancas de Chicago",
    "Miami Marlins": "Marlins de Miami",
    "Colorado Rockies": "Rockies de Colorado",
    "Arizona Diamondbacks": "Cascabeles de Arizona",
    "San Francisco Giants": "Gigantes de San Francisco",
    "Minnesota Twins": "Mellizos de Minnesota",
    "New York Mets": "Mets de Nueva York",
    "Pittsburgh Pirates": "Piratas de Pittsburgh",
    "St. Louis Cardinals": "Cardenales de San Luis",
    "Oakland Athletics": "Atleticos",
    "Athletics": "Atleticos"
}

def normalizar_equipo(nombre_espn):
    """Convierte 'Tampa Bay Rays' -> 'Rayos de Tampa Bay'"""
    nombre_espn = nombre_espn.strip()
    return TRADUCCIONES.get(nombre_espn, nombre_espn)
