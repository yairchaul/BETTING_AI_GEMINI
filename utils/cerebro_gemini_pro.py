# -*- coding: utf-8 -*-
"""
CEREBRO GEMINI PRO - Versión estable con modelos verificados
"""

import logging
import json
import os
import requests

logger = logging.getLogger(__name__)

class CerebroGeminiPro:
    # Modelos que funcionan actualmente (Junio 2026)
    MODELOS_VALIDOS = [
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-pro"
    ]
    
    def __init__(self, api_key, model_name="gemini-1.5-pro"):
        self.api_key = api_key
        self.model_name = model_name if model_name in self.MODELOS_VALIDOS else "gemini-1.5-pro"
        self.api_url = f"https://generativelanguage.googleapis.com/v1/models/{self.model_name}:generateContent?key={self.api_key}"
        self.client = None
        self.model = None

        if not self.api_key:
            logger.error("CerebroGeminiPro: API Key de Gemini no proporcionada.")
            return
        
        try:
            # Verificar disponibilidad del modelo
            list_url = f"https://generativelanguage.googleapis.com/v1/models?key={self.api_key}"
            response = requests.get(list_url, timeout=10)
            if response.status_code == 200:
                models = response.json().get('models', [])
                available_models = [m['name'].replace('models/', '') for m in models]
                logger.info(f"Modelos disponibles: {available_models}")
                
                # Si el modelo solicitado no está disponible, usar el primero disponible
                if self.model_name not in available_models and available_models:
                    self.model_name = available_models[0]
                    self.api_url = f"https://generativelanguage.googleapis.com/v1/models/{self.model_name}:generateContent?key={self.api_key}"
                    logger.info(f"Usando modelo alternativo: {self.model_name}")
            
            self.client = True  # Marcador de cliente activo
            logger.info(f"CerebroGeminiPro inicializado con modelo {self.model_name}")
        except Exception as e:
            logger.error(f"Error configurando Gemini: {e}")

    def test_connection(self):
        """Verifica si la API de Gemini responde correctamente."""
        if not self.api_key:
            return False
            
        try:
            payload = {
                "contents": [{
                    "parts": [{"text": "test"}]
                }],
                "generationConfig": {
                    "maxOutputTokens": 1
                }
            }
            response = requests.post(self.api_url, json=payload, timeout=15)
            
            if response.status_code == 200:
                logger.info("Conexión con Gemini verificada exitosamente.")
                return True
            else:
                logger.error(f"Error en conexión Gemini: {response.status_code} - {response.text[:200]}")
                return False
        except Exception as e:
            logger.error(f"Fallo en prueba de conexión Gemini: {e}")
            return False

    def generate_content(self, prompt):
        """Genera contenido usando la API REST de Gemini."""
        if not self.api_key:
            return {"error": "API Key no configurada"}
        
        try:
            payload = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 1024
                }
            }
            
            response = requests.post(self.api_url, json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                text = data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
                return text
            else:
                error_msg = f"Error {response.status_code}: {response.text[:200]}"
                logger.error(error_msg)
                return error_msg
        except Exception as e:
            logger.error(f"Error en generate_content: {e}")
            return f"Error: {e}"

    def orquestrar_decision_final(self, deporte, datos_partido, resultado_heuristico):
        """Genera un análisis usando Gemini."""
        if not self.api_key:
            return {"error": "API Key no configurada", "pick": "Error", "confianza": 0}

        prompt = f"""Eres un analista deportivo experto. Analiza el siguiente partido de {deporte}:

Datos del partido: {json.dumps(datos_partido, indent=2)[:2000]}
Análisis Heurístico: {json.dumps(resultado_heuristico, indent=2)[:500]}

Responde SOLO en formato JSON con estas claves:
- "pick": El equipo o apuesta recomendada
- "confianza": Número del 0 al 100
- "metodo": El método o tipo de apuesta
- "razon": Breve explicación

JSON:"""
        
        try:
            response_text = self.generate_content(prompt)
            
            # Extraer JSON de la respuesta
            import re
            json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(0))
                return result
            else:
                return {"pick": "No se pudo analizar", "confianza": 50, "metodo": "N/A", "razon": response_text[:200]}
        except Exception as e:
            logger.error(f"Error en orquestrar_decision_final: {e}")
            return {"error": str(e), "pick": "Error", "confianza": 0}
