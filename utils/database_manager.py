# -*- coding: utf-8 -*-
"""
DATABASE MANAGER - Gestor central de base de datos
Añadido: métodos para obtener top players por estadística
"""

import sqlite3
import pandas as pd
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path="data/betting_stats.db"):
        self.db_path = db_path
        self._init_tables()

    def _connect(self):
        conn = sqlite3.connect(self.db_path, timeout=20)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_tables(self):
        conn = self._connect()
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
                puntos_ht INTEGER,
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

        # Tabla de trazabilidad de auditoría (Task 9.1 — backtesting-real-mlb)
        # No rompe el esquema existente: tabla nueva, todos los campos nullable
        # excepto pick_id (PK). Permite trazar qué game_pk se cruzó con qué pick,
        # qué personId (HR/K) intervino, y la cuota usada en el momento de auditar.
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS backtesting_audit (
                pick_id      INTEGER PRIMARY KEY,
                game_pk      INTEGER,
                pick_type    TEXT,
                person_id    INTEGER,
                resultado    TEXT,
                cuota_usada  REAL,
                auditado_en  TEXT
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
            conn = self._connect()
            
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
            
            # Usar el nombre completo del equipo para la búsqueda, ya que así se guarda en la DB.
            equipo_busqueda = equipo
            equipo_pattern = f'%{equipo_busqueda}%'
            
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
    
    def get_team_stats_detailed(self, equipo, deporte, limit=5):
        """Obtiene estadísticas históricas de un equipo"""
        try:
            conn = self._connect()
            # Extraemos los datos individuales para calcular probabilidades manuales
            query = "SELECT puntos_favor, puntos_ht, puntos_contra FROM historial_equipos WHERE nombre_equipo LIKE ? AND deporte = ? ORDER BY fecha DESC LIMIT ?"
            df = pd.read_sql_query(query, conn, params=(f'%{equipo}%', deporte, limit))
            conn.close()
            
            if not df.empty:
                return {
                    'goles_favor': df['puntos_favor'].tolist(),
                    'goles_ht': df['puntos_ht'].fillna(0).tolist(),
                    'goles_contra': df['puntos_contra'].tolist(),
                    'promedio_favor': df['puntos_favor'].mean(),
                    'promedio_contra': df['puntos_contra'].mean(),
                    'victorias': len(df[df['puntos_favor'] > df['puntos_contra']]),
                    'partidos': len(df)
                }
            return {}
        except Exception as e:
            logger.error(f"Error detallado en stats de {equipo}: {e}")
            return {}

    def get_last_game_date(self, equipo, deporte):
        """Retorna la fecha del último partido jugado para detectar B2B"""
        try:
            conn = self._connect()
            query = "SELECT MAX(fecha) FROM historial_equipos WHERE nombre_equipo LIKE ? AND deporte = ?"
            cursor = conn.cursor()
            cursor.execute(query, (f'%{equipo}%', deporte))
            res = cursor.fetchone()
            conn.close()
            if res and res[0]:
                # Convertir a objeto datetime para cálculos
                return datetime.strptime(res[0], "%Y-%m-%d")
            return None
        except Exception as e:
            logger.error(f"Error obteniendo fecha de último juego para {equipo}: {e}")
            return None

    def get_team_stats(self, equipo, deporte, limit=5):
        """Obtiene estadísticas históricas de un equipo (Legacy support)"""
        try:
            conn = self._connect()
            query = "SELECT AVG(puntos_favor), AVG(puntos_contra), COUNT(*) FROM historial_equipos WHERE nombre_equipo LIKE ? AND deporte = ? ORDER BY fecha DESC LIMIT ?"
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
    
    def guardar_player_stats(self, stats_list, deporte):
        """Guarda estadísticas de jugadores en BD"""
        try:
            conn = self._connect()
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
            conn = self._connect()
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
            conn = self._connect()
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
