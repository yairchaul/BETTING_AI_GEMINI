# -*- coding: utf-8 -*-
import google.generativeai as genai
import json
import re
import streamlit as st
from calculador_probabilidades_futbol import CalculadorProbabilidadesFutbol
from selector_mejor_opcion import SelectorMejorOpcion

class AnalizadorFutbolHeuristicoMejorado:
    """
    SISTEMA MAESTRO NEON - Fusión de Heurística, Premium y Gemini
    """
    def __init__(self, stats_local, stats_visitante, nombre_local, nombre_visitante, api_key=None):
        self.local = stats_local
        self.visitante = stats_visitante
        self.nombre_local = nombre_local
        self.nombre_visitante = nombre_visitante
        self.api_key = api_key
        
        # 1. Ejecutar Cálculos Estadísticos
        self.probabilidades = CalculadorProbabilidadesFutbol.calcular(stats_local, stats_visitante)
        
        # 2. Ejecutar Selector de Reglas (Heurística)
        self.apuesta, self.confianza, self.detalle, self.regla = SelectorMejorOpcion.seleccionar(
            self.probabilidades, 
            self.nombre_local, 
            self.nombre_visitante
        )
        self.color = SelectorMejorOpcion.obtener_color(self.confianza)

    def analizar(self):
        """Devuelve el análisis completo listo para la interfaz"""
        return {
            'apuesta': self.apuesta,
            'confianza': self.confianza,
            'detalle': self.detalle,
            'regla': self.regla,
            'color': self.color,
            'probabilidades': self.probabilidades,
            'tipo': 'heurístico_mejorado'
        }

    def obtener_analisis_premium(self):
        """Lógica Premium: Edge Rating y Sharps Action"""
        prob = self.confianza
        edge = 3.0
        if prob >= 80: edge = 9.5
        elif prob >= 70: edge = 8.5
        elif prob >= 60: edge = 7.0
        
        # Detección de acción de profesionales (Sharps)
        sharps = "Sharps split"
        if prob > 70: sharps = f"Sharps heavy on {self.apuesta}"
        elif prob < 40: sharps = "Sharps avoiding this match"

        return {
            'edge_rating': edge,
            'public_money': 65 if prob > 60 else 50,
            'sharps_action': sharps,
            'value_detected': prob > 65
        }

    def consultar_gemini(self):
        """Consulta a la IA para validación final"""
        if not self.api_key or self.api_key == "TU_API_KEY_AQUÍ":
            return {"apuesta": "IA No Configurada", "confianza": 0, "razones": ["Falta API Key"]}

        try:
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            prompt = f"Analiza: {self.nombre_local} vs {self.nombre_visitante}. Probabilidades: {self.probabilidades}. Lesiones: {self.local.get('lesionados')} y {self.visitante.get('lesionados')}. Responde SOLO JSON con: 'apuesta', 'confianza' (0-100), 'razones' (lista)."
            
            response = model.generate_content(prompt)
            match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if match:
                return json.loads(match.group(0))
        except Exception as e:
            return {"apuesta": "Error Gemini", "confianza": 0, "razones": [str(e)]}
        
        return {"apuesta": "Sin respuesta IA", "confianza": 0, "razones": []}
