# -*- coding: utf-8 -*-
"""
Scraper para obtener estadísticas avanzadas de equipos de la NBA desde stats.nba.com.
Obtiene Offensive Rating, Defensive Rating y Pace.
"""
import requests
import pandas as pd
import logging
import time
import json
import os

logger = logging.getLogger(__name__)

class NBAStatsScraper:
    def __init__(self, cache_file="data/nba_team_stats_cache.json", cache_duration_hours=6):
        self.base_url = "https://stats.nba.com/stats/leaguedashteamstats"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36',
            'Referer': 'https://www.nba.com/',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept': 'application/json, text/plain, */*'
        }
        self.cache_file = cache_file
        self.cache_duration = cache_duration_hours * 3600  # in seconds

    def _load_cache(self):
        if os.path.exists(self.cache_file):
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache = json.load(f)
            # Check if cache is expired
            if time.time() - cache.get('timestamp', 0) < self.cache_duration:
                return cache.get('data')
        return None

    def _save_cache(self, data):
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump({'timestamp': time.time(), 'data': data}, f)

    def get_team_stats(self):
        """
        Obtiene las estadísticas avanzadas (Off/Def Rating, Pace) para todos los equipos.
        Utiliza un sistema de caché para evitar llamadas excesivas.
        """
        cached_data = self._load_cache()
        if cached_data:
            logger.info("Cargando estadísticas de equipos NBA desde caché.")
            return pd.DataFrame(cached_data)

        logger.info("Obteniendo estadísticas de equipos NBA desde stats.nba.com...")
        params = {
            'Conference': '', 'DateFrom': '', 'DateTo': '', 'Division': '',
            'GameScope': '', 'GameSegment': '', 'LastNGames': '0', 'LeagueID': '00',
            'Location': '', 'MeasureType': 'Advanced', 'Month': '0', 'OpponentTeamID': '0',
            'Outcome': '', 'PORound': '0', 'PaceAdjust': 'N', 'PerMode': 'PerGame',
            'Period': '0', 'PlayerExperience': '', 'PlayerPosition': '', 'PlusMinus': 'N',
            'Rank': 'N', 'Season': '2023-24', 'SeasonSegment': '', 'SeasonType': 'Regular Season',
            'ShotClockRange': '', 'StarterBench': '', 'TeamID': '0', 'TwoWay': '0', 'VsConference': '', 'VsDivision': ''
        }
        try:
            response = requests.get(self.base_url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()['resultSets'][0]
            df = pd.DataFrame(data['rowSet'], columns=data['headers'])
            
            # Guardar en caché
            self._save_cache(df.to_dict('records'))
            return df
        except requests.exceptions.RequestException as e:
            logger.error(f"Error obteniendo estadísticas de NBA: {e}")
            return None

# Instancia global para fácil acceso
nba_stats_scraper = NBAStatsScraper()

if __name__ == '__main__':
    df_stats = nba_stats_scraper.get_team_stats()
    if df_stats is not None:
        print("Estadísticas avanzadas de equipos NBA obtenidas:")
        print(df_stats[['TEAM_NAME', 'OFF_RATING', 'DEF_RATING', 'PACE']].head())