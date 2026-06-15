# -*- coding: utf-8 -*-
from database_manager import db

class NBAMasterEngine:
    """Motor de análisis de Props NBA basado en Master Engine MLB"""
    
    def __init__(self):
        self.defensa_benchmark = 12.5 # Promedio de triples permitidos en la liga

    def calcular_ajuste_defensivo(self, rival_name):
        # Factores de ajuste basados en eficiencia defensiva real
        ranking = {
            "Boston Celtics": 0.85, "Minnesota Timberwolves": 0.88,
            "San Antonio Spurs": 1.25, "Charlotte Hornets": 1.15
        }
        return ranking.get(rival_name, 1.0)

    def proyectar_triples(self, player_stats, rival_name):
        promedio = player_stats.get('triples_por_partido', 0)
        ajuste = self.calcular_ajuste_defensivo(rival_name)
        
        proyeccion = promedio * ajuste
        probabilidad = min(95, (proyeccion / 3.0) * 80)
        
        return round(proyeccion, 1), int(probabilidad)

nba_master = NBAMasterEngine()