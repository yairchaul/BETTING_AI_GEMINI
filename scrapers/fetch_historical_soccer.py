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
            puntos_ht INTEGER,
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

    insertados = 0

    try:
        teams_data = requests.get(url_teams, headers=headers).json()
        teams = teams_data.get('teams', [])
        
        # Añadimos timeout=20 para evitar el error de base de datos bloqueada
        conn = sqlite3.connect(DB_PATH, timeout=20)
        cursor = conn.cursor()
        
        for team_entry in teams:
            team = team_entry.get('team', {})
            t_id = team.get('id')
            t_name = team.get('displayName')

            team_inserts = 0
            url_schedule = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_id}/teams/{t_id}/schedule"
            schedule = requests.get(url_schedule, headers=headers).json()
            
            events = schedule.get('events', [])
            if not events:
                continue

            finalizados = [e for e in events if e.get('status', {}).get('type', {}).get('state') == 'post']
            
            for event in finalizados[-10:]:
                comp = event['competitions'][0]
                fecha = event['date'][:10]
                
                # Encontrar al equipo actual en la competencia
                me = next(c for c in comp['competitors'] if c['team']['id'] == t_id)
                rival = next(c for c in comp['competitors'] if c['team']['id'] != t_id)
                
                p_favor = int(me.get('score', 0))
                p_contra = int(rival.get('score', 0))
                
                # Extracción de Puntos HT (Half Time) de linescores si existen
                p_ht = 0
                linescores = me.get('linescores', [])
                if isinstance(linescores, list) and len(linescores) > 0:
                    # El primer periodo en fútbol es el primer tiempo
                    p_ht = int(linescores[0].get('value', 0))
                else:
                    # Intento alternativo buscando en la competencia general
                    c_lines = comp.get('linescores', [])
                    if isinstance(c_lines, list) and len(c_lines) > 0:
                         # Buscar el score del equipo en los periodos de la competencia
                         p_ht = 0 # Mantener en 0 si no se puede mapear con certeza
                
                cursor.execute('''
                    INSERT OR IGNORE INTO historial_equipos (nombre_equipo, deporte, puntos_favor, puntos_ht, puntos_contra, fecha)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (t_name, sport, p_favor, p_ht, p_contra, fecha))
                if cursor.rowcount > 0:
                    team_inserts += 1
                    insertados += 1
            
            if team_inserts > 0:
                print(f"   ✅ {t_name}: {team_inserts} partidos nuevos.")
        
        conn.commit()
        print(f"⭐ Liga {league_id} finalizada. Total inserciones: {insertados}")
        return insertados
        
    except Exception as e:
        print(f"❌ Error en {league_id}: {e}")

if __name__ == "__main__":
    if not os.path.exists("data"): os.makedirs("data")
    init_soccer_db()
    
    # Ligas a sincronizar incluyendo MUNDIAL 2026
    ligas = [
        "eng.1",       # Premier League
        "esp.1",       # La Liga
        "fifa.world",  # Copa del Mundo (Mundial 2026)
        "mex.1",       # Liga MX
        "ita.1"        # Serie A
    ]
    
    for liga in ligas:
        fetch_league_history(liga)
    
    print("\n🚀 Proceso completado. Los visuales de fútbol ahora deberían tener datos.")