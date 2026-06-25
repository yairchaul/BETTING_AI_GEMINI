# -*- coding: utf-8 -*-
"""
Actualizador de Datos de Fútbol

Este script se encarga de:
1. Obtener la lista de ligas disponibles desde el scraper de ESPN.
2. Iterar sobre cada liga para descargar los partidos más recientes.
3. Poblar/actualizar la base de datos de historial con estos partidos.

Diseñado para ser ejecutado periódicamente (ej. cada 12-24 horas) para
mantener los datos de 'forma reciente' frescos para los modelos de predicción.
"""
import os
import sys
import logging

# Añadir el root del proyecto al path para que los imports funcionen
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scrapers.espn_futbol import ESPN_FUTBOL

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def actualizar_todo_futbol():
    """
    Ejecuta el proceso completo de actualización de datos de fútbol.
    """
    logger.info("🚀 Iniciando actualización de datos de fútbol...")
    scraper = ESPN_FUTBOL()
    
    try:
        ligas = scraper.get_available_leagues()
        logger.info(f"Se encontraron {len(ligas)} ligas y torneos disponibles.")
        for i, liga in enumerate(ligas):
            logger.info(f"[{i+1}/{len(ligas)}] Procesando liga: {liga}")
            partidos = scraper.get_games(liga)
            if partidos:
                scraper.poblar_historial(partidos)
    except Exception as e:
        logger.error(f"❌ Falló la actualización de fútbol: {e}", exc_info=True)

if __name__ == "__main__":
    actualizar_todo_futbol()