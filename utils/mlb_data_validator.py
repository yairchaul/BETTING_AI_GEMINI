# -*- coding: utf-8 -*-
"""
SCRIPT DE VALIDACIÓN DE DATOS MLB
Verifica la integridad y conexión de los datos de MLB desde la extracción hasta el análisis.
"""
import json
import os
import pandas as pd
from utils.mapeo_equipos import normalizar_equipo

def check_file(path, is_json=True):
    """Verifica la existencia y validez de un archivo."""
    print(f"Verificando: {path}... ", end="")
    if not os.path.exists(path):
        print("❌ NO ENCONTRADO")
        return None
    
    try:
        if is_json:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if not data:
                print("⚠️  ADVERTENCIA: Archivo vacío.")
                return None
            print(f"✅ OK ({len(data)} registros)")
            return data
        else: # CSV
            data = pd.read_csv(path)
            if data.empty:
                print("⚠️  ADVERTENCIA: Archivo vacío.")
                return None
            print(f"✅ OK ({len(data)} filas)")
            return data
    except Exception as e:
        print(f"❌ ERROR DE LECTURA: {e}")
        return None

def validate_mlb_data_flow():
    """Función principal para ejecutar todas las validaciones de MLB."""
    print("--- INICIANDO VALIDACIÓN DE DATOS MLB ---")

    # 1. Verificar archivos de datos crudos/procesados por los scrapers
    print("\n[Paso 1: Verificación de Archivos de Scrapers]")
    partidos = check_file("data/resultados_finales_corregidos.json")
    pitchers = check_file("data/pitchers_hoy_selenium.json")
    
    if not partidos or not pitchers:
        print("\n--- 🔴 VALIDACIÓN FALLIDA: Faltan archivos base. Ejecuta los scrapers. ---")
        return

    # 2. Simular la estructura de datos para el motor y visualizadores
    print("\n[Paso 2: Simulación de Estructura de Datos]")
    primer_partido = partidos[0]
    local_norm = normalizar_equipo(primer_partido.get('local', ''))
    visitante_norm = normalizar_equipo(primer_partido.get('visitante', ''))

    print(f"Partido de prueba: {primer_partido.get('visitante')} vs {primer_partido.get('local')}")
    print(f"Nombres normalizados: {visitante_norm} vs {local_norm}")

    # Verificar si los pitchers están en el archivo de pitchers
    pitcher_local_nombre = primer_partido.get('pitchers', {}).get('local', {}).get('nombre')
    pitcher_visitante_nombre = primer_partido.get('pitchers', {}).get('visitante', {}).get('nombre')

    pitcher_local_encontrado = any(p['nombre'].lower() == pitcher_local_nombre.lower() for p in pitchers)
    pitcher_visitante_encontrado = any(p['nombre'].lower() == pitcher_visitante_nombre.lower() for p in pitchers)

    print(f"Pitcher local '{pitcher_local_nombre}': {'✅ Encontrado' if pitcher_local_encontrado else '❌ NO ENCONTRADO en pitchers_hoy_selenium.json'}")
    print(f"Pitcher visitante '{pitcher_visitante_nombre}': {'✅ Encontrado' if pitcher_visitante_encontrado else '❌ NO ENCONTRADO en pitchers_hoy_selenium.json'}")

    # 3. Verificar datos para análisis (HR y K)
    print("\n[Paso 3: Verificación de Datos para Motores de Props]")
    hr_candidates = primer_partido.get('hr_candidates_local', []) + primer_partido.get('hr_candidates_visit', [])
    if hr_candidates:
        print(f"✅ HR-Radar: Se encontraron {len(hr_candidates)} candidatos a HR para el primer partido.")
    else:
        print("⚠️ HR-Radar: No se encontraron candidatos a HR en el primer partido.")

    # La verificación de K-Props es más compleja, pero podemos ver si hay datos de pitchers
    if pitcher_local_nombre and pitcher_visitante_nombre:
        print("✅ K-Props: Nombres de pitchers presentes, listos para el análisis de ponches.")
    else:
        print("❌ K-Props: Faltan nombres de pitchers en los datos del partido.")

    print("\n--- ✅ VALIDACIÓN DE MLB COMPLETADA ---")

if __name__ == "__main__":
    validate_mlb_data_flow()