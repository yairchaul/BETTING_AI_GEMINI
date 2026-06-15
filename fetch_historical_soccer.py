# -*- coding: utf-8 -*-
"""FETCH HISTORICAL SOCCER - Descarga últimos 10 resultados para Premier y La Liga"""
import requests
import sqlite3
import json
from datetime import datetime
import os

DB_PATH = "data/betting_stats.db"

def init_soccer_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historial_equipos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_equipo TEXT,
            deporte TEXT,
            puntos_favor INTEGER,
            puntos_contra INTEGER,
            fecha TEXT,
            UNIQUE(nombre_equipo, fecha, deporte)
        )
    ''')
    conn.commit()
    conn.close()

def fetch_league_history(league_id, sport="soccer"):
    print(f"📡 Descargando historial para liga: {league_id}")
    url_teams = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_id}/teams"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        teams_data = requests.get(url_teams, headers=headers).json()
        teams = teams_data.get('teams', [])
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        for team_entry in teams:
            team = team_entry.get('team', {})
            t_id = team.get('id')
            t_name = team.get('displayName')
            
            print(f"   ⚽ Procesando: {t_name}")
            
            url_schedule = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_id}/teams/{t_id}/schedule"
            schedule = requests.get(url_schedule, headers=headers).json()
            
            events = schedule.get('events', [])
            # Tomar los últimos 10 partidos finalizados
            finalizados = [e for e in events if e.get('status', {}).get('type', {}).get('state') == 'post']
            
            for event in finalizados[-10:]:
                comp = event['competitions'][0]
                fecha = event['date'][:10]
                
                # Encontrar al equipo actual en la competencia
                me = next(c for c in comp['competitors'] if c['team']['id'] == t_id)
                rival = next(c for c in comp['competitors'] if c['team']['id'] != t_id)
                
                p_favor = int(me.get('score', 0))
                p_contra = int(rival.get('score', 0))
                
                cursor.execute('''
                    INSERT OR IGNORE INTO historial_equipos (nombre_equipo, deporte, puntos_favor, puntos_contra, fecha)
                    VALUES (?, ?, ?, ?, ?)
                ''', (t_name, sport, p_favor, p_contra, fecha))
        
        conn.commit()
        conn.close()
        print(f"✅ Historial de {league_id} actualizado.")
        
    except Exception as e:
        print(f"❌ Error en {league_id}: {e}")

if __name__ == "__main__":
    if not os.path.exists("data"): os.makedirs("data")
    init_soccer_db()
    
    # IDs de ESPN: Premier League (eng.1), La Liga (esp.1)
    fetch_league_history("eng.1")
    fetch_league_history("esp.1")
    
    print("\n🚀 Proceso completado. Los visuales de fútbol ahora deberían tener datos.")