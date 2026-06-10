# -*- coding: utf-8 -*-
"""
NBA Stats Scraper - Versión Corregida
Obtiene estadísticas avanzadas de equipos NBA desde NBA API
"""

import requests
import pandas as pd
import logging
from datetime import datetime
import json
import os

logger = logging.getLogger(__name__)

class NBAStatsScraper:
    def __init__(self):
        self.base_url = "https://stats.nba.com/stats"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Referer': 'https://www.nba.com/',
            'x-nba-stats-origin': 'stats',
            'x-nba-stats-token': 'true'
        }
        self.cache_file = "data/nba_team_stats_cache.json"
        self.cache_expiry_hours = 24
        self.team_stats_df = None
        self._load_or_fetch_stats()

    def _load_or_fetch_stats(self):
        """Carga stats desde caché o las obtiene de la API"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    last_update = datetime.fromisoformat(cache_data.get('last_update', '2020-01-01'))
                    hours_diff = (datetime.now() - last_update).total_seconds() / 3600
                    
                    if hours_diff < self.cache_expiry_hours:
                        logger.info(f"📦 Usando caché de stats NBA ({hours_diff:.1f}h de antigüedad)")
                        self.team_stats_df = pd.DataFrame(cache_data['data'])
                        return
            except Exception as e:
                logger.warning(f"Error cargando caché NBA: {e}")

        # Si no hay caché o está expirado, obtener datos frescos
        self.team_stats_df = self._fetch_fresh_stats()

    def _fetch_fresh_stats(self):
        """Obtiene estadísticas frescas desde la API de NBA"""
        try:
            logger.info("🔄 Obteniendo estadísticas NBA desde API...")
            
            # Endpoint para estadísticas de equipos (temporada actual)
            url = f"{self.base_url}/leaguedashteamstats"
            params = {
                'Conference': '',
                'DateFrom': '',
                'DateTo': '',
                'Division': '',
                'GameScope': '',
                'GameSegment': '',
                'LastNGames': '0',
                'LeagueID': '00',
                'Location': '',
                'MeasureType': 'Advanced',  # Estadísticas avanzadas
                'Month': '0',
                'OpponentTeamID': '0',
                'Outcome': '',
                'PORound': '0',
                'PaceAdjust': 'N',
                'PerMode': 'PerGame',
                'Period': '0',
                'PlayerExperience': '',
                'PlayerPosition': '',
                'PlusMinus': 'N',
                'Rank': 'N',
                'Season': '2024-25',  # Actualizar según temporada
                'SeasonSegment': '',
                'SeasonType': 'Regular Season',
                'ShotClockRange': '',
                'StarterBench': '',
                'TeamID': '0',
                'TwoWay': '0',
                'VsConference': '',
                'VsDivision': ''
            }

            response = requests.get(url, headers=self.headers, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            # Extraer datos de la respuesta
            headers = data['resultSets'][0]['headers']
            rows = data['resultSets'][0]['rowSet']
            
            df = pd.DataFrame(rows, columns=headers)
            
            # Renombrar columnas clave para compatibilidad
            df = df.rename(columns={
                'TEAM_NAME': 'TEAM_NAME',
                'PACE': 'PACE',
                'OFF_RATING': 'OFF_RATING',
                'DEF_RATING': 'DEF_RATING',
                'NET_RATING': 'NET_RATING',
                'W': 'WINS',
                'L': 'LOSSES',
                'W_PCT': 'WIN_PCT'
            })
            
            # Guardar en caché
            cache_data = {
                'last_update': datetime.now().isoformat(),
                'data': df.to_dict('records')
            }
            os.makedirs('data', exist_ok=True)
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ {len(df)} equipos NBA cargados y cacheados")
            return df
            
        except Exception as e:
            logger.error(f"Error obteniendo stats NBA: {e}")
            # Retornar DataFrame vacío con columnas esperadas si falla
            return pd.DataFrame(columns=['TEAM_NAME', 'PACE', 'OFF_RATING', 'DEF_RATING', 'NET_RATING'])

    def get_team_stats(self):
        """Retorna el DataFrame con estadísticas de equipos"""
        if self.team_stats_df is None or self.team_stats_df.empty:
            self._load_or_fetch_stats()
        return self.team_stats_df

    def get_player_stats(self, player_name_or_id):
        """
        Obtiene estadísticas de un jugador específico.
        Para implementar cuando se necesite integración con props.
        """
        # TODO: Implementar cuando se integre Balldontlie o NBA API players
        logger.warning("get_player_stats no implementado aún")
        return None

# Instancia global
nba_stats_scraper = NBAStatsScraper()

if __name__ == "__main__":
    # Test
    logging.basicConfig(level=logging.INFO)
    scraper = NBAStatsScraper()
    df = scraper.get_team_stats()
    print(df.head())
