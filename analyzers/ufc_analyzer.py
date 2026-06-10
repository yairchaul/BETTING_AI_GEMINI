# -*- coding: utf-8 -*-
"""
UFC ANALYZER - CORREGIDO (SIEMPRE DA GANADOR)
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.ufc_rankings_scraper import UFCRankingsScraper

class UFCAnalyzer:
    def __init__(self):
        self.rankings = UFCRankingsScraper()
    
    def calculate_score(self, fighter, opponent):
        score = 50
        
        w1 = fighter.get('wins', 0)
        l1 = fighter.get('losses', 0)
        w2 = opponent.get('wins', 0)
        l2 = opponent.get('losses', 0)
        
        name = fighter.get('nombre', '')
        
        # 1. CAMPEÓN
        bonus = self.rankings.get_bonus(name)
        if bonus >= 0.05:
            score += 10
        elif bonus >= 0.04:
            score += 7
        elif bonus >= 0.03:
            score += 5
        
        # 2. RANKING P4P
        p4p_pos = self.rankings.get_p4p_position(name)
        if p4p_pos:
            if p4p_pos <= 3:
                score += 6
            elif p4p_pos <= 5:
                score += 4
            elif p4p_pos <= 10:
                score += 2
        
        # 3. KO Rate
        ko1 = fighter.get('ko_rate', 0)
        if ko1 > 1: ko1 /= 100
        
        if ko1 >= 0.70:
            score += 7
        elif ko1 >= 0.60:
            score += 5
        elif ko1 >= 0.50:
            score += 3
        
        # 4. EXPERIENCIA
        exp1 = w1 + l1
        if exp1 >= 25:
            score += 5
        elif exp1 >= 18:
            score += 3
        elif exp1 >= 12:
            score += 1
        
        # 5. WIN RATE
        if w1 > 0:
            wr1 = w1 / (w1 + l1) if (w1 + l1) > 0 else 0.5
            wr2 = w2 / (w2 + l2) if (w2 + l2) > 0 else 0.5
            if wr1 > wr2 + 0.10:
                score += 3
        
        # 6. EDAD/PEAK
        age = fighter.get('edad', 30)
        if 27 <= age <= 32:
            score += 6
        elif age >= 36:
            score -= 3
        
        # 7. RACHA
        streak = fighter.get('streak', 0)
        if streak >= 3:
            score += 5
        elif streak >= 2:
            score += 3
        
        # 8. STRIKING ACCURACY
        striking = fighter.get('striking_accuracy', 0)
        if striking >= 0.50:
            score += 3
        elif striking >= 0.40:
            score += 1
        
        # 9. TAKEDOWN ACCURACY
        td = fighter.get('takedown_accuracy', 0)
        if td >= 0.50:
            score += 4
        elif td >= 0.35:
            score += 2
        
        return score
    
    def predict_method(self, winner_data, loser_data):
        ko_rate = winner_data.get('ko_rate', 0)
        if ko_rate > 1: ko_rate /= 100
        
        sub_rate = winner_data.get('sub_rate', 0)
        if sub_rate > 1: sub_rate /= 100
        
        exp = winner_data.get('wins', 0) + winner_data.get('losses', 0)
        
        if ko_rate >= 0.70:
            return "KO/TKO", 70
        elif ko_rate >= 0.50:
            return "KO/TKO", 55
        elif sub_rate >= 0.40:
            return "Sumisión", 65
        elif exp >= 25 and ko_rate < 0.40:
            return "Decisión", 60
        else:
            return "Decisión", 50
    
    def calculate_probability(self, p1, p2):
        score1 = self.calculate_score(p1, p2)
        score2 = self.calculate_score(p2, p1)
        total = score1 + score2
        return round((score1 / total) * 100) if total > 0 else 50
    
    def analizar_combate(self, p1_data, p2_data):
        prob = self.calculate_probability(p1_data, p2_data)
        p1_name = p1_data.get('nombre', 'P1')
        p2_name = p2_data.get('nombre', 'P2')
        score1 = self.calculate_score(p1_data, p2_data)
        score2 = self.calculate_score(p2_data, p1_data)
        
        # Determinar ganador (SIEMPRE)
        if prob >= 50:
            winner_data = p1_data
            winner_name = p1_name
            loser_data = p2_data
        else:
            winner_data = p2_data
            winner_name = p2_name
            loser_data = p1_data
        
        # Predecir método
        method, method_conf = self.predict_method(winner_data, loser_data)
        
        # Determinar si es pelea cerrada (para IA)
        is_close = 45 <= prob <= 55
        
        # SIEMPRE dar una recomendación
        if prob >= 65:
            decision = f"🔥 GANA {winner_name.upper()}"
            etiqueta = True
        elif prob >= 55:
            decision = f"📊 GANA {winner_name.upper()}"
            etiqueta = True
        elif prob <= 35:
            decision = f"🔥 GANA {winner_name.upper()}"
            etiqueta = True
        elif prob <= 45:
            decision = f"📊 GANA {winner_name.upper()}"
            etiqueta = True
        else:
            # Pelea cerrada (45-55%) - AÚN ASÍ damos ganador
            decision = f"📈 LIGERA VENTAJA {winner_name}"
            etiqueta = False
        
        return {
            'recomendacion': decision,
            'confianza': prob if prob >= 50 else 100 - prob,
            'metodo': f"{method} ({method_conf}%)",
            'etiqueta_verde': etiqueta,
            'probabilidad_raw': prob / 100,
            'ganador': winner_name,
            'score1': score1,
            'score2': score2,
            'is_close': is_close,
            'method_detail': {'type': method, 'confidence': method_conf}
        }
