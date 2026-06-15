# -*- coding: utf-8 -*-
"""
Módulo de Normalización de Equipos - BETTING_AI
Cumple con la Regla 14: Fuzzy Matching y Equivalencias.
"""
import os
import json
import logging
from utils.mapeo_equipos import TRADUCCION_MLB, EQUIPOS_A_ABREV

logger = logging.getLogger("BETTING_AI.utils.fuzzy")

# Mapeo inverso de abreviaturas para normalización (NYY -> New York Yankees)
REVERSE_ABREV = {v.upper(): k for k, v in EQUIPOS_A_ABREV.items()}

def normalizar_equipo(nombre_sucio):
    """
    Convierte nombres de ESPN (Español/Inglés) al nombre estándar de la DB.
    Ejemplo: 'Rayos de Tampa Bay' -> 'Tampa Bay Rays'
    """
    if not nombre_sucio:
        return "TBD"
    
    nombre_limpio = nombre_sucio.strip()
    nombre_upper = nombre_limpio.upper()
    
    # 1. Búsqueda por Abreviatura (Ej: NYY -> New York Yankees)
    if nombre_upper in REVERSE_ABREV:
        return REVERSE_ABREV[nombre_upper]

    # 2. Búsqueda directa en el diccionario de Traducción
    if nombre_limpio in TRADUCCION_MLB:
        return TRADUCCION_MLB[nombre_limpio]
    
    # 3. Verificación si ya es el nombre estándar en inglés
    if nombre_limpio in TRADUCCION_MLB.values():
        return nombre_limpio

    # 4. Lógica de respaldo: Búsqueda parcial simple
    for esp, eng in TRADUCCION_MLB.items():
        if esp.lower() in nombre_limpio.lower() or eng.lower() in nombre_limpio.lower():
            return eng

    logger.warning(f"No se encontró coincidencia exacta para: {nombre_limpio}")
    return nombre_limpio

if __name__ == "__main__":
    # Prueba rápida
    test = "Rayos de Tampa Bay"
    print(f"Original: {test} | Normalizado: {normalizar_equipo(test)}")