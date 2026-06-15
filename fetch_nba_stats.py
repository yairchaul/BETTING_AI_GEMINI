# -*- coding: utf-8 -*-
import requests
import sqlite3
from datetime import datetime
import os

def fetch_nba_player_stats():
    print("📡 Descargando estadísticas dinámicas de jugadores NBA...")
    # Endpoint de líderes de la NBA en ESPN
    url = "https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/statistics/byplayer?sort=avgThreePointFieldGoalsMade%3Adesc&limit=100"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        response = requests.get(url, headers=headers).json()
        players = response.get('categories', [{}])[0].get('statistics', [])
        
        conn = sqlite3.connect("data/betting_stats.db")
        cursor = conn.cursor()
        
        count = 0
        for p in players:
            athlete = p.get('athlete', {})
            name = athlete.get('displayName')
            team = athlete.get('teamShortName', 'N/A')
            
            # Extraer 3PM y Porcentaje (ajustar según índices de la API)
            stats_list = p.get('stats', [])
            # Buscamos por el nombre de la estadística en la respuesta
            three_pm = next((float(s) for i, s in enumerate(stats_list) if i == 11), 0.0) # Ajuste manual de índice
            points = next((float(s) for i, s in enumerate(stats_list) if i == 3), 0.0)
            
            cursor.execute('''
                INSERT OR REPLACE INTO player_stats 
                (nombre, equipo, deporte, temporada, puntos, triples_por_partido, ultima_actualizacion)
                VALUES (?, ?, 'nba', '2025-26', ?, ?, ?)
            ''', (name, team, points, three_pm, datetime.now().isoformat()))
            count += 1
            
        conn.commit()
        conn.close()
        print(f"✅ {count} jugadores NBA actualizados en la base de datos.")
        
    except Exception as e:
        print(f"❌ Error descargando NBA stats: {e}")

if __name__ == "__main__":
    if not os.path.exists("data"): os.makedirs("data")
    fetch_nba_player_stats()