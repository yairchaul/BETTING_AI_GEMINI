# -*- coding: utf-8 -*-
import streamlit as st
import random
import math

class AnalizadorPremiumProfesional:
    def __init__(self):
        print("✅ Analizador Premium Profesional (Vig-Free & RLM) inicializado")

    def _american_to_prob(self, american_odds):
        try:
            if isinstance(american_odds, str):
                american_odds = american_odds.replace('+', '').replace(' ', '')
            odds = int(american_odds)
            if odds > 0:
                return 100 / (odds + 100) * 100
            else:
                return abs(odds) / (abs(odds) + 100) * 100
        except:
            return 50

    def _limpiar_vig(self, prob_local, prob_visit):
        total = prob_local + prob_visit
        if total <= 100: return prob_local, prob_visit
        factor = total / 100
        return round(prob_local / factor, 2), round(prob_visit / factor, 2)

    def analizar(self, partido, resultado_ia, stats_adicionales=None):
        local = partido['local']
        visitante = partido['visitante']
        
        # Extraer probabilidades de la IA (Gemini/Groq)
        prob_modelo = resultado_ia.get('confianza', 50)
        equipo_ia = resultado_ia.get('ganador', local)

        # 1. Obtener Probabilidades Reales de Mercado
        odds_ml = partido.get('odds', {}).get('moneyline', {})
        p_sucia_l = self._american_to_prob(odds_ml.get('local', '-110'))
        p_sucia_v = self._american_to_prob(odds_ml.get('visitante', '-110'))
        
        p_real_l, p_real_v = self._limpiar_vig(p_sucia_l, p_sucia_v)
        overround = round((p_sucia_l + p_sucia_v) - 100, 2)

        # 2. Calcular el EDGE
        p_mercado_equipo = p_real_l if equipo_ia == local else p_real_v
        diff = prob_modelo - p_mercado_equipo
        edge = round(5.0 + (diff * 0.4), 1)

        # 3. Simulación de Movimiento de Línea (RLM)
        rlm_detectado = False
        if stats_adicionales and 'spread_apertura' in stats_adicionales:
            # Lógica de detección de movimiento inverso
            pass

        # 4. Resultado Final Profesional
        intensidad = "⛔ PASAR"
        if edge >= 7.5: intensidad = "🔥🔥 FUERTE"
        elif edge >= 6.5: intensidad = "🔥 MEDIA"

        return {
            'edge_rating': edge,
            'prob_modelo': prob_modelo,
            'prob_mercado': p_mercado_equipo,
            'overround': overround,
            'intensidad': intensidad,
            'valor_detectado': edge >= 6.5
        }

class ScraperTendencias:
    def __init__(self):
        pass
    def obtener_tendencias(self, local, visitante):
        return {'ticket_pct': 60, 'money_pct': 40} # Ejemplo
