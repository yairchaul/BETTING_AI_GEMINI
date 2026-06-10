# -*- coding: utf-8 -*-
"""
Cliente de IA unificado para múltiples proveedores.
Soporta: Gemini (google.genai), Groq, DeepSeek, OpenAI-compatible, Anthropic (Claude).
"""

import os
import json
import logging
from openai import OpenAI, APITimeoutError, APIConnectionError, AuthenticationError

try:
    import google.genai as genai
    from google.genai import types as genai_types
except ImportError:
    genai = None
    genai_types = None

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
                if not genai:
                    raise ImportError("Instala 'google-genai': pip install google-genai")
                self.client = genai.Client(api_key=self.api_key)
                self.logger.info(f"✅ Cliente Gemini listo — modelo: {self.model_name}")

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
                self.client.models.generate_content(
                    model=self.model_name,
                    contents="test",
                    config=genai_types.GenerateContentConfig(max_output_tokens=1),
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
                    max_tokens=500,
                    response_format={"type": "json_object"},
                )
                res_text = response.choices[0].message.content

            elif self.client_type == "gemini":
                full_prompt = f"{self._system_persona()}\n\n---\n\nDATOS:\n{prompt_content}"
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=full_prompt,
                    config=genai_types.GenerateContentConfig(
                        temperature=0.0,
                        max_output_tokens=500,
                    ),
                )
                res_text = response.text

            elif self.client_type == "anthropic":
                response = self.client.messages.create(
                    model=self.model_name,
                    system=self._system_persona(),
                    messages=[{"role": "user", "content": prompt_content}],
                    temperature=0.0,
                    max_tokens=500,
                )
                res_text = response.content[0].text

            else:
                return json.dumps({"error": "Proveedor no implementado"})

            # Limpiar markdown si viene envuelto
            if "```json" in res_text:
                res_text = res_text.split("```json")[1].split("```")[0].strip()
            elif "```" in res_text:
                res_text = res_text.split("```")[1].split("```")[0].strip()

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
