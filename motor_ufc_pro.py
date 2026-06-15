# -*- coding: utf-8 -*-
"""
MOTOR UFC PRO - Análisis profesional de peleas UFC
"""

import json
from datetime import datetime
from scrapers.ufc_scraper_unificado import UFCScraperUnificado
from scrapers.ufc_stats_scraper import UFCStatsScraper

class MotorUFCPro:
    def __init__(self):
        self.scraper = UFCScraperUnificado()
        self.stats_scraper = UFCStatsScraper()
        self.current_event = None
        self.analyses = []
        
    def cargar_evento_actual(self):
        """Carga el próximo evento de UFC"""
        try:
            self.current_event = self.scraper.obtener_cartelera_espn()
            
            # Enriquecer con estadísticas detalladas
            if self.current_event and 'fights' in self.current_event:
                for fight in self.current_event['fights']:
                    fighter1 = fight.get('fighter1', '')
                    fighter2 = fight.get('fighter2', '')
                    
                    if fighter1:
                        fight['stats1'] = self.stats_scraper.get_fighter_stats(fighter1)
                    if fighter2:
                        fight['stats2'] = self.stats_scraper.get_fighter_stats(fighter2)
                        
            return self.current_event
        except Exception as e:
            print(f"❌ Error cargando evento UFC: {e}")
            return None
    
    def analizar_pelea(self, fight_data):
        """Análisis completo de una pelea"""
        fighter1 = fight_data.get('fighter1', '')
        fighter2 = fight_data.get('fighter2', '')
        stats1 = fight_data.get('stats1', {})
        stats2 = fight_data.get('stats2', {})
        
        analysis = {
            'fight': f"{fighter1} vs {fighter2}",
            'prediction': self._predict_winner(stats1, stats2, fighter1, fighter2),
            'method': self._predict_method(stats1, stats2),
            'confidence': self._calculate_confidence(stats1, stats2),
            'key_factors': self._identify_key_factors(stats1, stats2)
        }
        
        return analysis
    
    def _predict_winner(self, stats1, stats2, name1, name2):
        """Predice el ganador basado en estadísticas"""
        score1 = self._calculate_fighter_score(stats1)
        score2 = self._calculate_fighter_score(stats2)
        
        if score1 > score2:
            return {'winner': name1, 'score_diff': score1 - score2}
        else:
            return {'winner': name2, 'score_diff': score2 - score1}
    
    def _calculate_fighter_score(self, stats):
        """Calcula puntuación de un peleador"""
        score = 50  # Base
        
        # Factores positivos
        score += stats.get('wins', 0) * 2
        score += stats.get('ko_wins', 0) * 3
        score += stats.get('sub_wins', 0) * 2
        score += stats.get('takedown_accuracy', 0) * 0.5
        score += stats.get('striking_accuracy', 0) * 0.3
        
        # Factores negativos
        score -= stats.get('losses', 0) * 2
        score -= stats.get('ko_losses', 0) * 3
        
        return max(0, min(100, score))
    
    def _predict_method(self, stats1, stats2):
        """Predice el método de victoria más probable"""
        total_kos = stats1.get('ko_wins', 0) + stats2.get('ko_losses', 0)
        total_subs = stats1.get('sub_wins', 0) + stats2.get('sub_losses', 0)
        total_decs = stats1.get('dec_wins', 0) + stats2.get('dec_losses', 0)
        
        if total_kos > total_subs and total_kos > total_decs:
            return 'KO/TKO'
        elif total_subs > total_kos and total_subs > total_decs:
            return 'Submission'
        else:
            return 'Decision'
    
    def _calculate_confidence(self, stats1, stats2):
        """Calcula nivel de confianza en la predicción"""
        diff_wins = abs(stats1.get('wins', 0) - stats2.get('wins', 0))
        diff_experience = abs(stats1.get('fights', 0) - stats2.get('fights', 0))
        
        confidence = 50
        confidence += min(diff_wins * 5, 30)
        confidence += min(diff_experience * 3, 20)
        
        return min(confidence, 100)
    
    def _identify_key_factors(self, stats1, stats2):
        """Identifica factores clave del combate"""
        factors = []
        
        # Ventaja en striking
        if stats1.get('striking_accuracy', 0) > stats2.get('striking_accuracy', 0) + 10:
            factors.append(f"Ventaja en precisión de golpeo para Fighter 1")
        elif stats2.get('striking_accuracy', 0) > stats1.get('striking_accuracy', 0) + 10:
            factors.append(f"Ventaja en precisión de golpeo para Fighter 2")
            
        # Ventaja en grappling
        if stats1.get('takedown_accuracy', 0) > stats2.get('takedown_defense', 0):
            factors.append(f"Ventaja en lucha para Fighter 1")
        elif stats2.get('takedown_accuracy', 0) > stats1.get('takedown_defense', 0):
            factors.append(f"Ventaja en lucha para Fighter 2")
            
        return factors
    
    def generar_reporte(self):
        """Genera reporte completo del evento"""
        if not self.current_event:
            self.cargar_evento_actual()
            
        report = {
            'evento': self.current_event.get('name', 'UFC Event'),
            'fecha': self.current_event.get('date', datetime.now().isoformat()),
            'analisis': []
        }
        
        for fight in self.current_event.get('fights', []):
            analysis = self.analizar_pelea(fight)
            report['analisis'].append(analysis)
            
        return report

# Ejemplo de uso
if __name__ == "__main__":
    motor = MotorUFCPro()
    evento = motor.cargar_evento_actual()
    if evento:
        print(f"🥊 Evento cargado: {evento.get('name', 'UFC')}")
        print(f"Peleas encontradas: {len(evento.get('fights', []))}")
