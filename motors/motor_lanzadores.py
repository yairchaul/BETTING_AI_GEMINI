# -*- coding: utf-8 -*-
"""Motor de lanzadores para MLB"""

import json
import os

def obtener_analisis_lanzadores():
    """Obtiene análisis de lanzadores desde archivo JSON"""
    data_path = "data/stats_lanzadores_hoy.json"
    if os.path.exists(data_path):
        try:
            with open(data_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def guardar_analisis_lanzadores(datos):
    """Guarda análisis de lanzadores en archivo JSON"""
    os.makedirs("data", exist_ok=True)
    with open("data/stats_lanzadores_hoy.json", 'w', encoding='utf-8') as f:
        json.dump(datos, f, indent=2, ensure_ascii=False)

# Instancia global
motor_lanzadores = obtener_analisis_lanzadores
