# -*- coding: utf-8 -*-
"""
STATS POPULATOR - Scraper para llenar la base de datos con estadísticas de jugadores.

Este script se encarga de:
1. Scrapear estadísticas de jugadores de MLB usando la API de `statsapi`.
2. Scrapear estadísticas de jugadores de NBA usando la API de `balldontlie`.
3. Guardar los datos recolectados en la base de datos SQLite (`betting_stats.db`)
   a través del `DatabaseManager`.

Puede ser ejecutado manualmente para poblar o actualizar la base de datos.
`python -m scrapers.stats_populator`
"""

import statsapi
import requests
import time
import logging

# Asegurarse de que el gestor de DB y el cliente de balldontlie estén en el path
try:
    from database_manager import db
    from balldontlie_client import balldontlie
except ImportError:
    # Fallback para ejecución como script
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from database_manager import db
    from balldontlie_client import balldontlie

logger = logging.getLogger(__name__)

def scrape_and_save_mlb_stats():
    """Scrapea stats de jugadores de MLB y los guarda en la DB."""
    logger.info("Iniciando scraping de estadísticas de jugadores de MLB...")
    all_stats = []
    try:
        teams = statsapi.get('teams', {'sportId': 1})['teams']
        for team in teams:
            team_id = team['id']
            roster = statsapi.get('team_roster', {'teamId': team_id}).get('roster', [])
            for player_item in roster:
                player_id = player_item['person']['id']
                try:
                    stats = statsapi.player_stat_data(player_id, group="hitting", type="season")['stats'][0]['splits'][0]['stat']
                    player_stats = {
                        'nombre': player_item['person']['fullName'],
                        'equipo': team['name'],
                        'hr': stats.get('homeRuns', 0),
                        'avg': stats.get('avg', 0.0),
                        'rbi': stats.get('rbi', 0),
                        'slugging': stats.get('slg', 0.0),
                    }
                    all_stats.append(player_stats)
                    time.sleep(0.05)  # Ser amable con la API
                except (IndexError, KeyError):
                    continue  # Jugador puede ser pitcher o no tener stats de bateo
    except Exception as e:
        logger.error(f"Error durante el scraping de MLB: {e}")

    if all_stats:
        db.guardar_player_stats(all_stats, 'mlb')
        logger.info(f"Se guardaron {len(all_stats)} estadísticas de jugadores de MLB en la DB.")
    else:
        logger.warning("No se encontraron estadísticas de jugadores de MLB para guardar.")

def scrape_and_save_nba_stats():
    """Scrapea stats de todos los jugadores de NBA y los guarda en la DB."""
    logger.info("Iniciando scraping de estadísticas de jugadores de NBA...")
    try:
        teams_response = balldontlie.get_teams()
        if not teams_response or 'data' not in teams_response:
            logger.error("No se pudieron obtener los equipos de la NBA desde balldontlie.")
            return

        all_players = []
        teams = teams_response['data']
        logger.info(f"Obteniendo jugadores para {len(teams)} equipos de la NBA...")

        for team in teams:
            team_id = team.get('id')
            if not team_id:
                continue
            
            players_data = balldontlie.get_players(team_id=team_id)
            if players_data and 'data' in players_data:
                all_players.extend(players_data['data'])
            time.sleep(1) # Pausa entre equipos para ser amable con la API

        logger.info(f"Total de {len(all_players)} jugadores encontrados. Obteniendo estadísticas...")
        all_stats = []
        for i, player in enumerate(all_players):
            stats = balldontlie.get_player_stats(player.get('id'))
            if stats:
                all_stats.append(stats)
            if (i + 1) % 20 == 0:
                logger.info(f"Procesados {i+1}/{len(all_players)} jugadores...")
            time.sleep(0.5) # Pausa entre jugadores

        if all_stats:
            db.guardar_player_stats(all_stats, 'nba')
            logger.info(f"Se guardaron {len(all_stats)} estadísticas de jugadores de NBA en la DB.")
    except Exception as e:
        logger.error(f"Error durante el scraping de NBA: {e}", exc_info=True)

if __name__ == "__main__":
    scrape_and_save_mlb_stats()
    # scrape_and_save_nba_stats() # Descomentar para ejecutar