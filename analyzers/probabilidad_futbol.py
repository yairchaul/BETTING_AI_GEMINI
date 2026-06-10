"""
CALCULADOR DE PROBABILIDADES PARA FÚTBOL
"""
import numpy as np

class CalculadorProbabilidadesFutbol:
    @staticmethod
    def calcular(stats_local, stats_visit):
        """Calcula probabilidades basadas en estadísticas"""
        
        # Obtener goles de los últimos partidos
        goles_local = stats_local.get('form_goles', [1, 1, 1, 1, 1]) if stats_local else [1, 1, 1, 1, 1]
        goles_visit = stats_visit.get('form_goles', [1, 1, 1, 1, 1]) if stats_visit else [1, 1, 1, 1, 1]
        
        # Promedios
        avg_local = np.mean(goles_local)
        avg_visit = np.mean(goles_visit)
        
        # Probabilidad de Over 2.5
        total_goles = avg_local + avg_visit
        prob_over = min(85, 50 + (total_goles - 2.5) * 15)
        
        # Probabilidad de BTTS (Ambos Anotan)
        btts_local = sum(1 for g in goles_local[-3:] if g > 0) / 3
        btts_visit = sum(1 for g in goles_visit[-3:] if g > 0) / 3
        prob_btts = (btts_local + btts_visit) * 50
        
        # Probabilidad de victoria local
        diff = avg_local - avg_visit
        prob_local_win = min(85, 50 + diff * 20)
        
        return {
            'over_25': round(prob_over, 1),
            'btts': round(prob_btts, 1),
            'local_win': round(prob_local_win, 1),
            'visit_win': round(100 - prob_local_win, 1),
            'avg_local': round(avg_local, 1),
            'avg_visit': round(avg_visit, 1),
            'total_goles': round(total_goles, 1)
        }
