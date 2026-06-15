# -*- coding: utf-8 -*-
import google.generativeai as genai
from groq import Groq
import json
import re
import streamlit as st

class AnalizadorIANBA:
    def __init__(self, gemini_key=None, groq_key=None):
        self.gemini_key = gemini_key
        self.groq_key = groq_key
        self.model_gemini = None
        self.client_groq = None
        
        # Inicializar Gemini
        if gemini_key:
            try:
                genai.configure(api_key=gemini_key)
                self.model_gemini = genai.GenerativeModel('gemini-1.5-flash')
            except: pass
            
        # Inicializar Groq
        if groq_key:
            try:
                self.client_groq = Groq(api_key=groq_key)
            except: pass

    def _extraer_json(self, texto):
        try:
            match = re.search(r'\{.*\}', texto, re.DOTALL)
            return json.loads(match.group(0)) if match else None
        except: return None

    def analizar(self, partido):
        """
        Analiza usando la mejor IA disponible con lógica de MLB (Cruce de stats)
        """
        local = partido.get('local', 'Equipo Local')
        visitante = partido.get('visitante', 'Equipo Visitante')
        lideres = partido.get('lideres', {})
        
        # Construcción del Prompt "Estilo MLB"
        prompt = f"""
        Eres un experto en arbitraje deportivo y analítica NBA.
        Partido: {local} vs {visitante}
        
        DATOS DE LÍDERES:
        - Local: {lideres.get('local', 'No disponible')}
        - Visitante: {lideres.get('visitante', 'No disponible')}
        - Odds/Spread: {partido.get('odds', 'Sin cuotas')}
        
        INSTRUCCIONES:
        1. Evalúa el cruce de los líderes anotadores contra el equipo rival.
        2. Determina si el spread tiene valor.
        3. Responde estrictamente en este formato JSON:
        {{
            "ganador": "Nombre del equipo",
            "apuesta": "GANA [Equipo] / OVER [Puntos] / HANDICAP [Valor]",
            "confianza": 0-100,
            "razones": ["Razón técnica 1", "Razón técnica 2"],
            "jugador_prop": "Nombre del jugador y su línea probable",
            "color": "green/orange/red"
        }}
        """

        # Intentar primero con Gemini
        if self.model_gemini:
            try:
                response = self.model_gemini.generate_content(prompt)
                res = self._extraer_json(response.text)
                if res: return res
            except: pass

        # Fallback a Groq (Llama 3)
        if self.client_groq:
            try:
                chat_completion = self.client_groq.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model="llama3-70b-8192",
                )
                res = self._extraer_json(chat_completion.choices[0].message.content)
                if res: return res
            except: pass

        # Fallback Heurístico Final (Si las IAs fallan)
        return {
            "ganador": local,
            "apuesta": f"GANA {local} (HEURÍSTICO)",
            "confianza": 50,
            "razones": ["Error de conexión con IAs, usando cálculo base"],
            "jugador_prop": "N/A",
            "color": "gray"
        }

# Clase para mantener compatibilidad con tus imports anteriores
class AnalizadorGeminiNBA(AnalizadorIANBA):
    def __init__(self, api_key):
        super().__init__(gemini_key=api_key)
