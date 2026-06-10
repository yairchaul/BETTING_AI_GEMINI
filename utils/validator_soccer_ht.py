# -*- coding: utf-8 -*-
import sqlite3
import os

def validate_ht_data():
    db_path = "data/betting_stats.db"
    if not os.path.exists(db_path):
        print(f"❌ DB no encontrada en {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Verificar si existen registros soccer con HT > 0
    cursor.execute("""
        SELECT nombre_equipo, puntos_ht, fecha 
        FROM historial_equipos 
        WHERE deporte='soccer' 
        ORDER BY fecha DESC LIMIT 10
    """)
    rows = cursor.fetchall()
    
    if not rows:
        print("⚠️ No hay registros de soccer en la DB. Ejecuta fetch_historical_soccer.py primero.")
        return

    print("🔍 VALIDACIÓN DE PUNTOS HT (Fútbol):")
    valids = 0
    for team, ht, fecha in rows:
        status = "✅" if ht > 0 else "ℹ️"
        if ht > 0: valids += 1
        print(f"   [{fecha}] {team}: HT Score = {ht} {status}")
    
    print(f"\n⭐ RESULTADO: {valids}/10 partidos recientes tienen datos de HT capturados.")
    conn.close()

if __name__ == "__main__":
    validate_ht_data()