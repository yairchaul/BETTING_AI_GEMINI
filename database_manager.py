# -*- coding: utf-8 -*-
"""
DATABASE MANAGER - Gestor central de base de datos
Añadido: métodos para obtener top players por estadística
"""

import sqlite3
import pandas as pd
import logging
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path="data/betting_stats.db"):
        self.db_path = db_path
        self._init_tables()
    
    def _init_tables(self):
        """Inicializa tablas necesarias"""
        # Added timeout to prevent hanging on locked databases
        conn = sqlite3.connect(self.db_path, timeout=20)
        cursor = conn.cursor()
        
        # Tabla de estadísticas de jugadores (para NBA y MLB)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS player_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT,
                equipo TEXT,
                deporte TEXT,
                temporada TEXT,
                puntos REAL,
                triples_por_partido REAL,
                intentos_triples REAL,
                porcentaje_triples REAL,
                hr INTEGER,
                avg REAL,
                rbi INTEGER,
                slugging REAL,
                ultima_actualizacion TEXT
            )
        ''')
        
        # Tabla historial equipos fútbol
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS historial_equipos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre_equipo TEXT,
                deporte TEXT,
                puntos_favor INTEGER,
                puntos_contra INTEGER,
                fecha TEXT
            )
        ''')

        # Tabla para aprendizaje de Home Runs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS hr_candidates_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT,
                jugador TEXT,
                probabilidad REAL,
                pitcher_rival TEXT,
                pitcher_mano TEXT,
                resultado TEXT DEFAULT 'PENDIENTE'
            )
        ''')

        # Tabla de equipos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS equipos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT UNIQUE,
                deporte TEXT,
                ciudad TEXT,
                estadio TEXT
            )
        ''')

        # Tabla de backtesting para auditoría de resultados
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS backtesting (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT,
                deporte TEXT,
                evento TEXT,
                pick TEXT,
                cuota REAL,
                estado TEXT DEFAULT 'PENDIENTE',
                creado_en TEXT
            )
        ''')

        # Tabla para caché de lineups de MLB
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lineup_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_pk INTEGER,
                equipo_nombre TEXT,
                lineup_json TEXT,
                timestamp TEXT,
                UNIQUE(game_pk, equipo_nombre)
            )
        ''')

        # Tabla para caché de stats de peleadores UFC
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ufc_fighter_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fighter_name_norm TEXT UNIQUE,
                stats_json TEXT,
                timestamp TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_top_player_stat(self, equipo, stat, limit=1, deporte='nba'):
        """
        Obtiene el/los mejores jugadores de un equipo por una estadística específica.
        
        Args:
            equipo (str): Nombre del equipo
            stat (str): 'three_pm', 'hr', 'points', etc.
            limit (int): Número de jugadores a retornar
            deporte (str): 'nba' o 'mlb'
        
        Returns:
            list: Lista de diccionarios con los mejores jugadores
        """
        try:
            conn = sqlite3.connect(self.db_path, timeout=10)
            
            if deporte == 'nba':
                if stat == 'three_pm':
                    query = '''
                        SELECT nombre, triples_por_partido, porcentaje_triples, puntos
                        FROM player_stats 
                        WHERE equipo LIKE ? AND deporte = 'nba'
                        ORDER BY triples_por_partido DESC, porcentaje_triples DESC
                        LIMIT ?
                    '''
                elif stat == 'points':
                    query = '''
                        SELECT nombre, puntos, triples_por_partido
                        FROM player_stats 
                        WHERE equipo LIKE ? AND deporte = 'nba'
                        ORDER BY puntos DESC
                        LIMIT ?
                    '''
                else:
                    return []
            
            elif deporte == 'mlb':
                if stat == 'hr':
                    query = '''
                        SELECT nombre, hr, avg, rbi, slugging
                        FROM player_stats 
                        WHERE equipo LIKE ? AND deporte = 'mlb'
                        ORDER BY hr DESC, slugging DESC
                        LIMIT ?
                    '''
                elif stat == 'avg':
                    query = '''
                        SELECT nombre, avg, hr, rbi
                        FROM player_stats 
                        WHERE equipo LIKE ? AND deporte = 'mlb'
                        ORDER BY avg DESC
                        LIMIT ?
                    '''
                else:
                    return []
            else:
                return []
            
            # Buscar equipo parcialmente
            equipo_pattern = f'%{equipo}%'
            cursor = conn.cursor()
            cursor.execute(query, (equipo_pattern, limit))
            rows = cursor.fetchall()
            conn.close()
            
            if rows:
                resultados = []
                for row in rows:
                    if deporte == 'nba':
                        resultados.append({
                            'nombre': row[0],
                            'triples_por_partido': row[1],
                            'porcentaje_triples': row[2],
                            'puntos': row[3]
                        })
                    else:
                        resultados.append({
                            'nombre': row[0],
                            'hr': row[1],
                            'avg': row[2],
                            'rbi': row[3],
                            'slugging': row[4]
                        })
                return resultados if limit > 1 else resultados[0]
            return None
            
        except Exception as e:
            logger.error(f"Error obteniendo top player para {equipo} ({stat}): {e}")
            return None
    
    def get_team_stats(self, equipo, deporte, limit=5):
        """Obtiene estadísticas históricas de un equipo"""
        try:
            conn = sqlite3.connect(self.db_path)
            query = '''
                SELECT AVG(puntos_favor) as promedio_favor, 
                       AVG(puntos_contra) as promedio_contra,
                       COUNT(*) as partidos
                FROM historial_equipos 
                WHERE nombre_equipo LIKE ? AND deporte = ?
                ORDER BY fecha DESC
                LIMIT ?
            '''
            cursor = conn.cursor()
            cursor.execute(query, (f'%{equipo}%', deporte, limit))
            row = cursor.fetchone()
            conn.close()
            
            if row and row[0]:
                return {
                    'promedio_favor': row[0],
                    'promedio_contra': row[1],
                    'partidos': row[2]
                }
            return {}
        except Exception as e:
            logger.error(f"Error obteniendo stats de {equipo}: {e}")
            return {}

    def get_lineup_from_cache(self, game_pk, equipo_nombre, max_age_minutes=30):
        """Obtiene un lineup desde el caché de la base de datos si es reciente."""
        try:
            conn = sqlite3.connect(self.db_path, timeout=10)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT lineup_json, timestamp FROM lineup_cache WHERE game_pk = ? AND equipo_nombre = ?",
                (game_pk, equipo_nombre)
            )
            row = cursor.fetchone()
            conn.close()
            if row:
                lineup_json, timestamp_str = row
                timestamp = datetime.fromisoformat(timestamp_str)
                if datetime.now() - timestamp < timedelta(minutes=max_age_minutes):
                    logger.info(f"Cache HIT para lineup: {equipo_nombre} (game_pk: {game_pk})")
                    return json.loads(lineup_json)
                else:
                    logger.info(f"Cache STALE para lineup: {equipo_nombre} (game_pk: {game_pk})")
        except Exception as e:
            logger.error(f"Error obteniendo lineup de caché DB: {e}")
        return None

    def save_lineup_to_cache(self, game_pk, equipo_nombre, lineup):
        """Guarda o actualiza un lineup en el caché de la base de datos."""
        try:
            conn = sqlite3.connect(self.db_path, timeout=10)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO lineup_cache (game_pk, equipo_nombre, lineup_json, timestamp)
                VALUES (?, ?, ?, ?)
                """,
                (game_pk, equipo_nombre, json.dumps(lineup), datetime.now().isoformat())
            )
            conn.commit()
            conn.close()
            logger.info(f"Cache SAVED para lineup: {equipo_nombre} (game_pk: {game_pk})")
        except Exception as e:
            logger.error(f"Error guardando lineup en caché DB: {e}")
    
    def get_ufc_fighter_from_cache(self, fighter_name_norm, max_age_days=3):
        """Obtiene stats de un peleador UFC desde el caché de la DB si es reciente."""
        try:
            conn = sqlite3.connect(self.db_path, timeout=10)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT stats_json, timestamp FROM ufc_fighter_cache WHERE fighter_name_norm = ?",
                (fighter_name_norm,)
            )
            row = cursor.fetchone()
            conn.close()
            if row:
                stats_json, timestamp_str = row
                timestamp = datetime.fromisoformat(timestamp_str)
                if datetime.now() - timestamp < timedelta(days=max_age_days):
                    logger.info(f"Cache HIT para peleador UFC: {fighter_name_norm}")
                    return json.loads(stats_json)
                else:
                    logger.info(f"Cache STALE para peleador UFC: {fighter_name_norm}")
        except Exception as e:
            logger.error(f"Error obteniendo peleador UFC de caché DB: {e}")
        return None

    def save_ufc_fighter_to_cache(self, fighter_name_norm, stats_data):
        """Guarda o actualiza stats de un peleador UFC en el caché de la DB."""
        try:
            conn = sqlite3.connect(self.db_path, timeout=10)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO ufc_fighter_cache (fighter_name_norm, stats_json, timestamp)
                VALUES (?, ?, ?)
                """,
                (fighter_name_norm, json.dumps(stats_data, default=str), datetime.now().isoformat())
            )
            conn.commit()
            conn.close()
            logger.info(f"Cache SAVED para peleador UFC: {fighter_name_norm}")
        except Exception as e:
            logger.error(f"Error guardando peleador UFC en caché DB: {e}")

    def clean_old_cache(self, lineup_days=2, ufc_days=7):
        """Limpia registros antiguos de las tablas de caché."""
        try:
            conn = sqlite3.connect(self.db_path, timeout=10)
            cursor = conn.cursor()
            
            # Limpiar lineup_cache
            cutoff_lineup = (datetime.now() - timedelta(days=lineup_days)).isoformat()
            cursor.execute("DELETE FROM lineup_cache WHERE timestamp < ?", (cutoff_lineup,))
            lineups_deleted = cursor.rowcount
            
            # Limpiar ufc_fighter_cache
            cutoff_ufc = (datetime.now() - timedelta(days=ufc_days)).isoformat()
            cursor.execute("DELETE FROM ufc_fighter_cache WHERE timestamp < ?", (cutoff_ufc,))
            ufc_deleted = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            logger.info(f"Limpieza de caché completada. Lineups eliminados: {lineups_deleted}. Peleadores UFC eliminados: {ufc_deleted}.")
            return lineups_deleted, ufc_deleted
        except Exception as e:
            logger.error(f"Error limpiando caché antiguo: {e}")
            return 0, 0

    def guardar_player_stats(self, stats_list, deporte):
        """Guarda estadísticas de jugadores en BD"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for stat in stats_list:
                if deporte == 'nba':
                    cursor.execute('''
                        INSERT OR REPLACE INTO player_stats 
                        (nombre, equipo, deporte, temporada, puntos, triples_por_partido, 
                         intentos_triples, porcentaje_triples, ultima_actualizacion)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        stat.get('nombre'),
                        stat.get('equipo'),
                        'nba',
                        stat.get('temporada', '2025'),
                        stat.get('puntos', 0),
                        stat.get('triples_por_partido', 0),
                        stat.get('intentos_triples', 0),
                        stat.get('porcentaje_triples', 0),
                        datetime.now().isoformat()
                    ))
                elif deporte == 'mlb':
                    cursor.execute('''
                        INSERT OR REPLACE INTO player_stats 
                        (nombre, equipo, deporte, temporada, hr, avg, rbi, slugging, ultima_actualizacion)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        stat.get('nombre'),
                        stat.get('equipo'),
                        'mlb',
                        stat.get('temporada', '2025'),
                        stat.get('hr', 0),
                        stat.get('avg', 0),
                        stat.get('rbi', 0),
                        stat.get('slugging', 0),
                        datetime.now().isoformat()
                    ))
            
            conn.commit()
            conn.close()
            logger.info(f"✅ {len(stats_list)} jugadores guardados para {deporte}")
        except Exception as e:
            logger.error(f"Error guardando player stats: {e}")

    def guardar_backtesting(self, deporte, evento, pick, cuota=1.90):
        """Guarda un registro para auditoría posterior"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO backtesting (fecha, deporte, evento, pick, cuota, estado, creado_en)
                VALUES (?, ?, ?, ?, ?, 'PENDIENTE', ?)
            ''', (
                datetime.now().strftime("%Y-%m-%d"),
                deporte, evento, pick, cuota,
                datetime.now().isoformat()
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error en guardar_backtesting: {e}")

    def obtener_racha_fallos(self, equipo):
        """
        Retorna el número de veces consecutivas que un equipo ha fallado como pick
        en la tabla de backtesting.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            # Buscamos los últimos 3 picks donde participó este equipo
            cursor.execute('''
                SELECT estado FROM backtesting 
                WHERE evento LIKE ? 
                ORDER BY fecha DESC LIMIT 3
            ''', (f'%{equipo}%',))
            resultados = cursor.fetchall()
            conn.close()
            
            # Contamos cuántas veces el estado es 'PERDIDA'
            return sum(1 for r in resultados if r[0] == 'PERDIDA')
        except Exception as e:
            logger.error(f"Error en obtener_racha_fallos para {equipo}: {e}")
            return 0

# Instancia global
db = DatabaseManager()
