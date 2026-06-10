# -*- coding: utf-8 -*-
"""
TEST FUTBOL REGLA 1 - Valida detección de Over 1.5 HT
"""
import sys
import os
import sqlite3
from datetime import datetime

# Configurar rutas para importar módulos del proyecto
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motors.futbol_analyzer_jerarquico import analizar_futbol_jerarquico
from utils.database_manager import db

def setup_mock_data():
    """Inserta datos ficticios para forzar la activación de la Regla 1."""
    db_path = os.path.join("data", "betting_stats.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Limpiar datos previos de los equipos de prueba
    cursor.execute("DELETE FROM historial_equipos WHERE nombre_equipo IN ('Alpha FC', 'Beta United')")
    
    # Insertar 5 partidos para cada uno con >= 2 goles al medio tiempo (HT)
    # Usamos la etiqueta 'soccer' como requiere el motor
    for i in range(5):
        fecha = (datetime.now()).strftime("%Y-%m-%d")
        cursor.execute("""
            INSERT INTO historial_equipos (nombre_equipo, deporte, puntos_favor, puntos_ht, puntos_contra, fecha)
            VALUES (?, 'soccer', 3, 2, 1, ?)
        """, ('Alpha FC', fecha))
        cursor.execute("""
            INSERT INTO historial_equipos (nombre_equipo, deporte, puntos_favor, puntos_ht, puntos_contra, fecha)
            VALUES (?, 'soccer', 2, 2, 0, ?)
        """, ('Beta United', fecha))
        
    conn.commit()
    conn.close()
    print("✅ Datos de prueba (Regla 1 - HT) insertados en la DB con etiqueta 'soccer'.")

if __name__ == "__main__":
    print("🧪 Iniciando validación del Analizador Jerárquico...")
    setup_mock_data()
    
    resultado = analizar_futbol_jerarquico('Alpha FC', 'Beta United')
    
    print(f"\n🎯 RESULTADO DEL ANÁLISIS: {resultado['pick']}")
    print(f"📊 CONFIANZA: {resultado['confianza']}% | REGLA APLICADA: #{resultado['regla']}")
    
    if resultado['regla'] == 1 and resultado['pick'] == "OVER 1.5 HT":
        print("\n⭐ TEST EXITOSO: La Regla 1 fue detectada y priorizada correctamente.")
    else:
        print("\n❌ TEST FALLIDO: No se detectó la Regla 1.")