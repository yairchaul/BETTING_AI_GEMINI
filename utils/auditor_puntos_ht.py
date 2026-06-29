# -*- coding: utf-8 -*-
"""
AUDITOR PUNTOS HT - Reporte de frecuencia Over 1.5 HT
"""
import sqlite3
import pandas as pd
import os
import os # Assuming os is a built-in module

def generar_reporte_ht():
    db_path = "data/betting_stats.db"
    if not os.path.exists(db_path):
        print(f"❌ No se encontró la base de datos en {db_path}")
        return

    try:
        conn = sqlite3.connect(db_path)
        # Extraer solo partidos de fútbol con datos HT
        query = """
        SELECT nombre_equipo, puntos_ht 
        FROM historial_equipos 
        WHERE deporte = 'soccer'
        """
        df = pd.read_sql_query(query, conn)
        conn.close()

        if df.empty:
            print("⚠️ No hay registros con datos de 'puntos_ht' en la base de datos.")
            return

        # Agrupar y calcular frecuencia
        reporte = df.groupby('nombre_equipo').agg(
            Partidos=('puntos_ht', 'count'),
            Hits_HT=('puntos_ht', lambda x: (x >= 2).sum())
        )
        reporte['Frecuencia_HT_1.5_Plus'] = (reporte['Hits_HT'] / reporte['Partidos'] * 100).round(1)
        
        # Filtrar equipos con al menos 3 partidos y ordenar
        resultado = reporte[reporte['Partidos'] >= 3].sort_values(by='Frecuencia_HT_1.5_Plus', ascending=False)

        print("\n📊 REPORTE: EQUIPOS CON MAYOR TENDENCIA OVER 1.5 HT")
        print("=" * 65)
        print(resultado.to_string())
        print("=" * 65)

    except Exception as e:
        print(f"❌ Error durante la auditoría: {e}")

if __name__ == "__main__":
    generar_reporte_ht()