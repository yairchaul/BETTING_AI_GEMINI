# -*- coding: utf-8 -*-
"""
Scraper de Cuotas (Odds) para MLB desde Caliente.mx
"""
import requests
import re
import logging
from bs4 import BeautifulSoup
from utils.mapeo_equipos import normalizar_equipo

logger = logging.getLogger(__name__)

def get_mlb_odds_caliente():
    """
    Extrae las cuotas de Moneyline para los partidos de MLB de hoy desde Caliente.mx.
    Retorna un diccionario: {'Nombre Equipo Normalizado': '+150', ...}
    """
    odds_map = {}
    try:
        url = "https://sports.caliente.mx/es_MX/MLB"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Selector más robusto para los eventos de partido
        event_containers = soup.select('div.event')

        for event in event_containers:
            team_names = [team.get_text(strip=True) for team in event.select('div.seln-name')]
            odds_values = [odd.get_text(strip=True) for odd in event.select('div.price.dec')]

            if len(team_names) >= 2 and len(odds_values) >= 2:
                # Caliente a veces incluye el pitcher en el nombre, lo limpiamos
                team1_clean = re.sub(r'\s*\([^)]*\)', '', team_names[0])
                team2_clean = re.sub(r'\s*\([^)]*\)', '', team_names[1])

                # Normalizamos el nombre para que coincida con otras fuentes
                norm_team1 = normalizar_equipo(team1_clean)
                norm_team2 = normalizar_equipo(team2_clean)

                odds_map[norm_team1] = odds_values[0]
                odds_map[norm_team2] = odds_values[1]
    except Exception as e:
        logger.error(f"Error al scrapear cuotas de Caliente: {e}")
    
    return odds_map