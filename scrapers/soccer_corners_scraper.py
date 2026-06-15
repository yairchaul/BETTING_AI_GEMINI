# -*- coding: utf-8 -*-
"""
SOCCER CORNERS SCRAPER - Simulación avanzada de datos de córners
En un entorno real, esto se conectaría a una API o web scraping de un sitio de estadísticas.
"""
import random
import json
import os

class SoccerCornersScraper:
    def __init__(self):
        self.team_corner_tendencies = self._load_tendencies()

    def _load_tendencies(self):
        """
        Carga tendencias de córners por equipo.
        En un escenario real, esto se actualizaría dinámicamente.
        """
        # Datos simulados de tendencias de córners por equipo (promedio por partido)
        return {
            "Manchester City": {"avg_corners_for": 7.5, "avg_corners_against": 3.0},
            "Liverpool": {"avg_corners_for": 6.8, "avg_corners_against": 3.5},
            "Arsenal": {"avg_corners_for": 6.2, "avg_corners_against": 3.8},
            "Chelsea": {"avg_corners_for": 5.9, "avg_corners_against": 4.0},
            "Real Madrid": {"avg_corners_for": 7.0, "avg_corners_against": 3.2},
            "Barcelona": {"avg_corners_for": 6.5, "avg_corners_against": 3.7},
            "Bayern Munich": {"avg_corners_for": 7.2, "avg_corners_against": 2.8},
            "Paris Saint-Germain": {"avg_corners_for": 6.9, "avg_corners_against": 3.1},
            "Juventus": {"avg_corners_for": 5.5, "avg_corners_against": 4.2},
            "Inter Milan": {"avg_corners_for": 5.8, "avg_corners_against": 4.1},
            "Wolverhampton Wanderers": {"avg_corners_for": 4.0, "avg_corners_against": 6.0},
            "Fulham": {"avg_corners_for": 4.5, "avg_corners_against": 5.5},
            "Brighton & Hove Albion": {"avg_corners_for": 5.0, "avg_corners_against": 5.0},
            "Sunderland": {"avg_corners_for": 3.5, "avg_corners_against": 6.5},
            # Añadir más equipos según sea necesario
        }

    def get_corners_data(self, home_team, away_team, league_id=None):
        """
        Genera datos de córners proyectados y línea de apuesta.
        En un escenario real, esto haría una petición HTTP a un sitio de estadísticas.
        """
        home_tendency = self.team_corner_tendencies.get(home_team, {"avg_corners_for": 5.0, "avg_corners_against": 5.0})
        away_tendency = self.team_corner_tendencies.get(away_team, {"avg_corners_for": 5.0, "avg_corners_against": 5.0})

        # Proyección de córners: promedio de los que generan + los que permiten
        projected_corners_home = home_tendency["avg_corners_for"] + away_tendency["avg_corners_against"]
        projected_corners_away = away_tendency["avg_corners_for"] + home_tendency["avg_corners_against"]
        
        total_projected_corners = (projected_corners_home + projected_corners_away) / 2
        
        # Simular una línea de apuesta cercana a la proyección
        line_corners = round(total_projected_corners / 0.5) * 0.5 # Redondear al 0.5 más cercano
        line_corners = max(8.5, line_corners) # Mínimo de línea realista

        return {"corners_proyectados": round(total_projected_corners, 1), "corners_line": line_corners}