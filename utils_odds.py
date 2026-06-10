# -*- coding: utf-8 -*-
"""Módulo de Limpieza y Mapeo de Odds"""

MAPEO_EQUIPOS = {
    "Tampa Bay Rays": "Rayos de Tampa Bay",
    "Cleveland Guardians": "Guardianes de Cleveland",
    "Houston Astros": "Astros de Houston",
    "New York Yankees": "Yankees de Nueva York",
    "Los Angeles Dodgers": "Dodgers de Los Angeles",
    # Agrega más si detectas que faltan
}

def normalizar_nombre(nombre):
    """Convierte nombres sucios o en inglés al formato de NEON"""
    for eng, esp in MAPEO_EQUIPOS.items():
        if eng.lower() in nombre.lower() or esp.lower() in nombre.lower():
            return esp
    return nombre

def obtener_odd_color(odd):
    """Devuelve color para Streamlit según la cuota"""
    try:
        val = float(odd)
        if val < 0: return "green" # Favorito
        return "white"
    except:
        return "gray"
