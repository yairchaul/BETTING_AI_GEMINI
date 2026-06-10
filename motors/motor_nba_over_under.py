"""
MOTOR NBA OVER/UNDER
Predice el total de puntos de un partido de baloncesto basándose en datos históricos
y la línea de Over/Under proporcionada por los scrapers.
"""
import json
import os
import logging
from datetime import datetime, timedelta

import pandas as pd
import logging

# Importar el nuevo scraper de estadísticas avanzadas
try:
    from scrapers.nba_stats_scraper_fixed import nba_stats_scraper
    STATS_NBA_AVAILABLE = True
except ImportError:
    STATS_NBA_AVAILABLE = False
    logging.warning("NBAStatsScraper no disponible. El motor O/U de la NBA no funcionará correctamente.")

logger = logging.getLogger(__name__)

class MotorNBAOverUnder:
    def __init__(self):
        self.team_stats_df = None
        self.league_avg_pace = 100.0  # Valor por defecto, se recalculará
        self.league_avg_off_rating = 110.0 # Valor por defecto, se recalculará
        self._load_team_stats()

    def _load_team_stats(self):
        """Carga las estadísticas de equipo desde el scraper."""
        if not STATS_NBA_AVAILABLE:
            return
        self.team_stats_df = nba_stats_scraper.get_team_stats()
        if self.team_stats_df is not None:
            # Convertir columnas relevantes a numérico
            for col in ['PACE', 'OFF_RATING', 'DEF_RATING']:
                self.team_stats_df[col] = pd.to_numeric(self.team_stats_df[col], errors='coerce')
            
            # Calcular promedios de la liga
            self.league_avg_pace = self.team_stats_df['PACE'].mean()
            self.league_avg_off_rating = self.team_stats_df['OFF_RATING'].mean()

    def _get_team_advanced_stats(self, team_name):
        """
        Obtiene estadísticas avanzadas de un equipo desde el DataFrame cargado.
        """
        if self.team_stats_df is None:
            return None
        
        # Buscar el equipo por su nombre (puede ser nombre completo o apodo)
        team_row = self.team_stats_df[self.team_stats_df['TEAM_NAME'].str.contains(team_name, case=False, na=False)]
        if not team_row.empty:
            return team_row.iloc[0]
        return None

    def predict_over_under(self, game_data):
        """
        Predice el Over/Under para un partido de la NBA.
        :param game_data: Diccionario con 'local', 'visitante' y 'over_under_line' (de scraper).
        :return: Diccionario con recomendación, confianza y proyección.
        """
        if self.team_stats_df is None:
            self._load_team_stats() # Intentar recargar si no se cargó al inicio
            if self.team_stats_df is None:
                return {"recomendacion": "N/A", "confianza": 0, "proyeccion_total": "N/A", "razon": "No se pudieron cargar las estadísticas de la NBA."}

        home_team = game_data.get('local')
        away_team = game_data.get('visitante')
        over_under_line = game_data.get('over_under_line')

        if not all([home_team, away_team, over_under_line]):
            return {"recomendacion": "N/A", "confianza": 0, "proyeccion_total": "N/A", "razon": "Faltan datos esenciales del partido."}

        # Obtener estadísticas de ambos equipos
        home_stats = self._get_team_advanced_stats(home_team)
        away_stats = self._get_team_advanced_stats(away_team)

        if home_stats is None or away_stats is None:
            return {"recomendacion": "N/A", "confianza": 0, "proyeccion_total": "N/A", "razon": f"No se encontraron estadísticas para {home_team} o {away_team}."}

        # Fórmula de predicción mejorada usando Pace y Ratings
        projected_pace = (home_stats['PACE'] + away_stats['PACE']) / 2
        
        # Puntos proyectados para el equipo local
        home_projected_score = (home_stats['OFF_RATING'] * away_stats['DEF_RATING']) / self.league_avg_off_rating
        
        # Puntos proyectados para el equipo visitante
        away_projected_score = (away_stats['OFF_RATING'] * home_stats['DEF_RATING']) / self.league_avg_off_rating
        
        # Total de puntos proyectado, ajustado por el ritmo del partido
        projected_total = (projected_pace / 100) * (home_projected_score + away_projected_score) / 2

        # Comparar con la línea de Over/Under
        difference = projected_total - over_under_line
        
        if difference > 3.5: # Umbral más alto para mayor seguridad
            recomendacion = "OVER"
            confianza = min(90, 55 + int(difference * 4))
        elif difference < -3.5: # Umbral más alto para mayor seguridad
            recomendacion = "UNDER"
            confianza = min(90, 55 + int(abs(difference) * 4))
        else:
            recomendacion = "NO BET"
            confianza = 40 # Baja confianza si está muy cerca

        return {
            "recomendacion": recomendacion,
            "confianza": confianza,
            "proyeccion_total": round(projected_total, 1),
            "razon": f"Proyección de {round(projected_total, 1)} vs línea de {over_under_line}."
        }