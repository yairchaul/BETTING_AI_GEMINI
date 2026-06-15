# -*- coding: utf-8 -*-
"""
Cliente de IA unificado para múltiples proveedores.
Soporta: Gemini (google.genai), Groq, DeepSeek, OpenAI-compatible, Anthropic (Claude).
"""

import os
import json
import logging
import requests
from openai import OpenAI, APITimeoutError, APIConnectionError, AuthenticationError

try:
    import anthropic as anthropic_sdk
except ImportError:
    anthropic_sdk = None


class GenericAIClient:
    """Cliente de IA unificado para múltiples proveedores."""

    def __init__(self, client_type: str, api_key: str, model_name: str, base_url: str = None):
        self.client_type = client_type.lower()
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = base_url
        self.client = None
        self.logger = logging.getLogger(__name__)

        if not self.api_key:
            self.logger.error(f"API Key para {self.client_type} no proporcionada.")
            return

        try:
            if self.client_type in ("groq", "deepseek", "openai", "openrouter"):
                self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
                self.logger.info(f"✅ Cliente {self.client_type} listo — modelo: {self.model_name}")

            elif self.client_type == "gemini":
                self.api_url = f"https://generativelanguage.googleapis.com/v1/models/{self.model_name}:generateContent?key={self.api_key}"
                self.client = True # Marcador de cliente activo
                self.logger.info(f"✅ Cliente Gemini (REST) listo — modelo: {self.model_name}")

            elif self.client_type == "anthropic":
                if not anthropic_sdk:
                    raise ImportError("Instala 'anthropic': pip install anthropic")
                self.client = anthropic_sdk.Anthropic(api_key=self.api_key)
                self.logger.info(f"✅ Cliente Claude listo — modelo: {self.model_name}")

            else:
                self.logger.error(f"Tipo de cliente no soportado: {self.client_type}")

        except Exception as e:
            self.logger.error(f"❌ Error inicializando {self.client_type}: {e}")
            self.client = None

    def test_connection(self) -> bool:
        if not self.client:
            return False
        try:
            if self.client_type in ("groq", "deepseek", "openai", "openrouter"):
                self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": "test"}],
                    max_tokens=1,
                    timeout=10,
                )
            elif self.client_type == "gemini":
                payload = {
                    "contents": [{"parts": [{"text": "test"}]}],
                    "generationConfig": {"maxOutputTokens": 1}
                }
                response = requests.post(self.api_url, json=payload, timeout=15)
                if response.status_code != 200:
                    raise APIConnectionError(
                        f"Gemini test failed with status {response.status_code}: {response.text[:100]}"
                    )
            elif self.client_type == "anthropic":
                self.client.messages.create(
                    model=self.model_name,
                    max_tokens=1,
                    messages=[{"role": "user", "content": "test"}],
                )
            self.logger.info(f"Conexión con {self.client_type} exitosa.")
            return True
        except (APITimeoutError, APIConnectionError) as e:
            self.logger.warning(f"⚠️ Fallo de conexión con {self.client_type}: {e}")
        except AuthenticationError as e:
            self.logger.error(f"❌ Fallo de autenticación con {self.client_type}: {e}")
        except Exception as e:
            self.logger.error(f"⚠️ Fallo técnico en {self.client_type}: {e}")
        return False

    def _system_persona(self) -> str:
        return (
            "Eres el 'Analista Deportivo BETTING_AI', experto senior en apuestas deportivas. "
            "Maximiza el ROI con análisis técnico riguroso. "
            "RESPONDE ÚNICAMENTE con un objeto JSON válido, sin texto extra, sin markdown, sin bloques de código. "
            'Estructura obligatoria: {"pick":"<texto>","confianza":<0-100>,"stake":<1-3>,'
            '"razon":"<texto breve>","mercado":"MONEYLINE|OVER_UNDER|STRIKEOUTS|HOME_RUN|BTTS|HANDICAP"}'
        )

    def orquestrar_decision(self, prompt_content: str) -> str:
        """Envía el prompt al proveedor configurado y retorna la respuesta (string JSON)."""
        if not self.client:
            return json.dumps({"error": f"Cliente {self.client_type} no disponible"})

        try:
            if self.client_type in ("groq", "deepseek", "openai", "openrouter"):
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": self._system_persona()},
                        {"role": "user", "content": prompt_content},
                    ],
                    temperature=0.0,
                    max_tokens=800,
                    response_format={"type": "json_object"},
                )
                res_text = response.choices[0].message.content

            elif self.client_type == "gemini":
                # Usar la API REST directamente, como en CerebroGeminiPro
                full_prompt = f"{self._system_persona()}\n\n---\n\nDATOS:\n{prompt_content}"
                payload = {
                    "contents": [{"parts": [{"text": full_prompt}]}],
                    "generationConfig": {
                        "temperature": 0.0,
                        "maxOutputTokens": 800,
                        "responseMimeType": "application/json", # Forzar salida JSON
                    }
                }
                response = requests.post(self.api_url, json=payload, timeout=30)
                response.raise_for_status() # Lanza error si no es 2xx
                data = response.json()
                # Extraer texto de la respuesta JSON
                res_text = data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
                if not res_text:
                    # Si el texto está vacío, puede que la respuesta entera sea el JSON
                    res_text = json.dumps(data)

            elif self.client_type == "anthropic":
                response = self.client.messages.create(
                    model=self.model_name,
                    system=self._system_persona(),
                    messages=[{"role": "user", "content": prompt_content}],
                    temperature=0.0,
                    max_tokens=800,
                )
                res_text = response.content[0].text

            else:
                return json.dumps({"error": "Proveedor no implementado"})

            # Limpiar markdown si viene envuelto
            if "```json" in res_text:
                res_text = res_text.split("```json")[1].split("```")[0].strip()
            elif "```" in res_text:
                res_text = res_text.split("```")[1].split("```")[0].strip()

            # Extracción robusta: tomar el primer objeto {...} balanceado
            inicio = res_text.find("{")
            if inicio >= 0:
                profundidad = 0
                for i in range(inicio, len(res_text)):
                    if res_text[i] == "{":
                        profundidad += 1
                    elif res_text[i] == "}":
                        profundidad -= 1
                        if profundidad == 0:
                            res_text = res_text[inicio:i + 1]
                            break

            json.loads(res_text)  # Validar JSON
            return res_text.strip()

        except json.JSONDecodeError:
            self.logger.error(f"Respuesta de {self.client_type} no es JSON válido: {res_text[:200]}")
            return json.dumps({"error": "Respuesta no es JSON válido", "raw": res_text[:200]})
        except Exception as e:
            self.logger.error(f"Error en {self.client_type}: {e}")
            if "429" in str(e) or "quota" in str(e).lower():
                self.logger.critical(f"Rate limit / cuota agotada en {self.client_type}")
            return json.dumps({"error": f"Error en {self.client_type}: {str(e)}"})

    def orquestrar_decision_final(self, deporte: str, partido, resultado_heuristico, resumen_contexto=None) -> str:
        """Compatibilidad con CerebroGeminiPro/DeepSeek: construye el prompt y llama a orquestrar_decision."""
        rec  = resultado_heuristico if isinstance(resultado_heuristico, str) else str(resultado_heuristico)[:400]
        part = partido if isinstance(partido, str) else str(partido)[:400]
        ctx  = f"\nContexto adicional: {str(resumen_contexto)[:200]}" if resumen_contexto else ""
        prompt = (
            f"Deporte: {deporte}\n"
            f"Partido: {part}\n"
            f"Análisis heurístico previo: {rec}"
            f"{ctx}\n\n"
            "Confirma o corrige el pick. Responde SOLO en JSON con: pick, confianza, stake, razon, mercado."
        )
        return self.orquestrar_decision(prompt)
