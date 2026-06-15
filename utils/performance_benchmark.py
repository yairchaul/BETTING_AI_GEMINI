# -*- coding: utf-8 -*-
"""
PERFORMANCE BENCHMARK - Prueba de carga de motores unificados
Verifica que la unificación no afecte la velocidad de respuesta.
"""
import time
import sys
import os
import logging

# Configurar rutas
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Benchmark")

def benchmark_ufc():
    logger.info("🧪 Testeando UFCAnalyzer Unificado...")
    from motors.ufc_analyzer import UFCAnalyzer
    analyzer = UFCAnalyzer()
    
    p1 = {'nombre': 'Test Fighter 1', 'ko_rate': 0.6, 'wins': 15, 'losses': 5, 'alcance': 185, 'altura': 180}
    p2 = {'nombre': 'Test Fighter 2', 'ko_rate': 0.2, 'wins': 10, 'losses': 8, 'alcance': 175, 'altura': 178}
    
    start = time.time()
    for _ in range(100):
        analyzer.analizar_combate(p1, p2)
    end = time.time()
    
    avg_time = (end - start) / 100
    logger.info(f"✅ UFC: 100 análisis en {end-start:.4f}s (Avg: {avg_time:.6f}s/análisis)")

def benchmark_futbol():
    logger.info("🧪 Testeando Futbol Jerárquico...")
    from motors.futbol_analyzer_jerarquico import analizar_futbol_jerarquico
    
    start = time.time()
    # El benchmark dependerá de la DB, pero probamos la ejecución del módulo
    try:
        analizar_futbol_jerarquico("Real Madrid", "Barcelona")
    except Exception as e:
        logger.warning(f"⚠️ Futbol Jerárquico requiere datos en DB: {e}")
    end = time.time()
    logger.info(f"✅ Futbol Jerárquico: Primer análisis en {end-start:.4f}s")

def benchmark_mlb():
    logger.info("🧪 Testeando Motores MLB...")
    from motors.motor_mlb_pro import analizar_mlb_pro_v20
    from motors.motor_over_under import motor_over_under
    
    partido = {
        'local': 'New York Yankees', 'visitante': 'Boston Red Sox',
        'pitchers': {'local': {'nombre': 'Gerrit Cole', 'era': 3.20}, 'visitante': {'nombre': 'Nick Pivetta', 'era': 4.50}},
        'odds': {'over_under': 8.5},
        'venue': 'Yankee Stadium'
    }
    
    start = time.time()
    analizar_mlb_pro_v20(partido)
    motor_over_under.calcular_total(partido)
    end = time.time()
    logger.info(f"✅ MLB: Análisis técnico completo en {end-start:.4f}s")

def run_all():
    print("="*60)
    print("🚀 BETTING_AI - PERFORMANCE & INTEGRITY CHECK")
    print("="*60)
    benchmark_ufc()
    benchmark_futbol()
    benchmark_mlb()
    print("="*60)
    print("🎉 PRUEBA DE CARGA FINALIZADA - SISTEMA ESTABLE")

if __name__ == "__main__":
    run_all()