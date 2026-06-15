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
                    "temperature": 0.2,
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

    def _system_persona(self) -> str:
        """Define la personalidad y las reglas de formato para Gemini."""
        return """# 🧠 ROL Y OBJETIVO
Eres un analista de datos deportivos de élite, creado para ser un consultor del proyecto BETTING_AI. Tu nombre es "Gemini-Analyst".

Tu misión es analizar los datos heurísticos y de contexto para generar una predicción final con un razonamiento profundo, siguiendo un formato JSON estricto.

# 📜 REGLAS DE INTERACCIÓN
1.  **FORMATO JSON ESTRICTO:** Tu respuesta DEBE ser ÚNICAMENTE un objeto JSON válido, sin texto adicional, explicaciones fuera del JSON ni bloques de código markdown.
2.  **Esquema Obligatorio:** El JSON debe seguir esta estructura: `{"pick":"<texto>", "confianza":<0-100>, "stake":<1-3>, "razon":"<texto>", "mercado":"MONEYLINE|OVER_UNDER|STRIKEOUTS|HOME_RUN|BTTS|HANDICAP"}`
---
"""

    def orquestrar_decision(self, prompt_content: str):
        """
        Genera un análisis usando Gemini, compatible con la interfaz de AnalistaTotal.
        """
        if not self.api_key:
            return json.dumps({"error": "API Key no configurada"})

        full_prompt = (f"{self._system_persona()}\n**TAREA:** Analiza los siguientes datos y devuelve tu decisión "
                       "en el formato JSON especificado. IMPORTANTE: la 'razon' DEBE ser BREVE (máximo 20 palabras) "
                       "para no exceder el límite de respuesta.\n\n**DATOS:**\n" + prompt_content)
        
        try:
            response_text = self.generate_content(full_prompt) or ""

            # Limpiar fences markdown si vienen
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]

            # Extracción robusta: primer objeto {...} balanceado
            inicio = response_text.find("{")
            json_str = ""
            if inicio >= 0:
                prof = 0
                for i in range(inicio, len(response_text)):
                    if response_text[i] == "{":
                        prof += 1
                    elif response_text[i] == "}":
                        prof -= 1
                        if prof == 0:
                            json_str = response_text[inicio:i + 1]
                            break
                # Si quedó sin cerrar (truncado), intentar cerrar el objeto
                if not json_str and prof > 0:
                    json_str = response_text[inicio:] + ('"' if response_text.rstrip().endswith(':') else '') + "}" * prof

            if json_str:
                try:
                    json.loads(json_str)
                    return json_str
                except json.JSONDecodeError:
                    pass

            logger.error(f"Gemini no devolvió un JSON válido: {response_text[:200]}")
            return json.dumps({"error": "Respuesta no es JSON válido", "raw": response_text[:200]})
        except Exception as e:
            logger.error(f"Error en orquestrar_decision (Gemini): {e}")
            return json.dumps({"error": str(e)})
