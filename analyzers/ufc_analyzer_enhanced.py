# -*- coding: utf-8 -*-
"""
ANALIZADOR UFC MEJORADO - Jerarquía de Decisiones
"""

import logging

logger = logging.getLogger(__name__)

class UFCAnalyzerEnhanced:
    def __init__(self):
        self.umbral_ko = 0.65
        self.umbral_decision = 0.55
        self.umbral_upset = 0.45
    
    def analizar_combate_completo(self, p1_data, p2_data):
        p1_nombre = p1_data.get('nombre', 'Peleador 1')
        p2_nombre = p2_data.get('nombre', 'Peleador 2')
        
        # Extraer datos
        p1_ko = p1_data.get('ko_rate', 0.5)
        p2_ko = p2_data.get('ko_rate', 0.5)
        p1_alcance = p1_data.get('alcance', 170)
        p2_alcance = p2_data.get('alcance', 170)
        p1_altura = p1_data.get('altura', 170)
        p2_altura = p2_data.get('altura', 170)
        
        p1_wins = self._extraer_victorias(p1_data.get('record', '0-0-0'))
        p2_wins = self._extraer_victorias(p2_data.get('record', '0-0-0'))
        
        # Calcular probabilidad base
        prob_victoria_p1 = 0.50
        prob_ko = (p1_ko + p2_ko) / 2
        
        # Ajustar por récord
        if p1_wins > p2_wins:
            prob_victoria_p1 += 0.05 * (p1_wins - p2_wins)
        else:
            prob_victoria_p1 -= 0.05 * (p2_wins - p1_wins)
        
        # Ajustar por alcance
        alcance_diff = p1_alcance - p2_alcance
        prob_victoria_p1 += alcance_diff * 0.005
        
        # Ajustar por altura
        altura_diff = p1_altura - p2_altura
        prob_victoria_p1 += altura_diff * 0.003
        
        # Ajustar por KO rate
        ko_diff = p1_ko - p2_ko
        prob_victoria_p1 += ko_diff * 0.15
        prob_ko += ko_diff * 0.1
        
        # Limitar
        prob_victoria_p1 = max(0.01, min(0.99, prob_victoria_p1))
        prob_ko = max(0.01, min(0.95, prob_ko))
        
        # JERARQUÍA DE DECISIONES
        
        # REGLA 1: Alta probabilidad de KO
        if prob_victoria_p1 > self.umbral_ko and prob_ko > self.umbral_ko:
            return {
                'recomendacion': f"GANA {p1_nombre.upper()} POR KO/TKO",
                'confianza': int(prob_victoria_p1 * 100),
                'metodo': 'KO/TKO',
                'razon': 'Superioridad física y alto % de KO',
                'etiqueta_verde': True
            }
        elif (1 - prob_victoria_p1) > self.umbral_ko and prob_ko > self.umbral_ko:
            return {
                'recomendacion': f"GANA {p2_nombre.upper()} POR KO/TKO",
                'confianza': int((1 - prob_victoria_p1) * 100),
                'metodo': 'KO/TKO',
                'razon': 'Superioridad física y alto % de KO',
                'etiqueta_verde': True
            }
        
        # REGLA 2: Favorito claro (>60%)
        if prob_victoria_p1 > 0.60:
            metodo = "KO/TKO" if prob_ko > 0.5 else "Decisión"
            return {
                'recomendacion': f"GANA {p1_nombre.upper()} POR {metodo}",
                'confianza': int(prob_victoria_p1 * 100),
                'metodo': metodo,
                'razon': 'Favorito claro',
                'etiqueta_verde': prob_victoria_p1 > 0.65
            }
        elif (1 - prob_victoria_p1) > 0.60:
            metodo = "KO/TKO" if prob_ko > 0.5 else "Decisión"
            return {
                'recomendacion': f"GANA {p2_nombre.upper()} POR {metodo}",
                'confianza': int((1 - prob_victoria_p1) * 100),
                'metodo': metodo,
                'razon': 'Favorito claro',
                'etiqueta_verde': (1 - prob_victoria_p1) > 0.65
            }
        
        # REGLA 3: Pelea pareja (45-55%)
        if 0.45 <= prob_victoria_p1 <= 0.55:
            metodo = "KO/TKO" if prob_ko > 0.6 else "Decisión"
            ganador = p1_nombre if prob_victoria_p1 >= 0.50 else p2_nombre
            conf = prob_victoria_p1 if prob_victoria_p1 >= 0.50 else (1 - prob_victoria_p1)
            return {
                'recomendacion': f"GANA {ganador.upper()} POR {metodo}",
                'confianza': int(conf * 100),
                'metodo': metodo,
                'razon': 'Pelea pareja, ligera ventaja',
                'etiqueta_verde': False
            }
        
        # REGLA 4: Default
        return {
            'recomendacion': "EVITAR APUESTA / PELEA A DECISIÓN",
            'confianza': 50,
            'metodo': 'Decisión',
            'razon': 'Sin ventajas claras',
            'etiqueta_verde': False
        }
    
    def _extraer_victorias(self, record):
        try:
            parts = record.split('-')
            return int(parts[0]) if len(parts) >= 1 else 0
        except:
            return 0
