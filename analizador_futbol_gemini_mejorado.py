# -*- coding: utf-8 -*-
import google.generativeai as genai
import json
import re
import streamlit as st

class AnalizadorFutbolGeminiMejorado:
    def __init__(self, api_key):
        self.api_key = api_key
        self.disponible = False
        try:
            if api_key and api_key != "TU_API_KEY_AQUÍ":
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-1.5-flash')
                self.disponible = True
                print("✅ Gemini Futbol Pro conectado")
        except Exception as e:
            print(f"⚠️ Error Gemini: {e}")

    def analizar(self, partido, stats_local, stats_visitante, probabilidades):
        if not self.disponible:
            return {'apuesta': 'IA OFFLINE', 'confianza': 0, 'razones': ['No API'], 'color': 'red', 'tipo': 'gemini'}

        local = partido.get('local', 'Local')
        visitante = partido.get('visitante', 'Visitante')
        lesionados_l = stats_local.get('lesionados', [])
        lesionados_v = stats_visitante.get('lesionados', [])

        # PROMPT MEJORADO (Sin caracteres de escape conflictivos)
        prompt = f"Analiza: {local} vs {visitante}. Probabilidades: BTTS {probabilidades.get('prob_btts') or 0}%, Over2.5 {probabilidades.get('prob_over25') or 0}%, WinL {probabilidades.get('prob_local') or 0}%. Lesionados Local: {lesionados_l}. Lesionados Visitante: {lesionados_v}. Responde SOLO un JSON con: apuesta, confianza (0-100), razones (lista), color (green/yellow/red)."

        try:
            response = self.model.generate_content(prompt)
            match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if match:
                res = json.loads(match.group(0))
                res['tipo'] = 'gemini_mejorado'
                return res
        except Exception as e:
            return {'apuesta': 'Error IA', 'confianza': 0, 'razones': [str(e)], 'color': 'red', 'tipo': 'gemini'}
        
        return {'apuesta': 'N/A', 'confianza': 0, 'razones': [], 'color': 'red', 'tipo': 'gemini'}
