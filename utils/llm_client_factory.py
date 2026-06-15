# -*- coding: utf-8 -*-
"""
Fábrica de Clientes LLM para centralizar la creación y gestión de API.
"""
import os
import json
import logging
import asyncio
import time
import httpx
from cachetools import TTLCache
import hashlib

# --- Caching ---
LLM_CACHE_MAXSIZE = int(os.getenv("LLM_CACHE_MAXSIZE", 500))
LLM_CACHE_TTL_SECONDS = int(os.getenv("LLM_CACHE_TTL_SECONDS", 600))
llm_cache = TTLCache(maxsize=LLM_CACHE_MAXSIZE, ttl=LLM_CACHE_TTL_SECONDS)

# --- Retry Logic ---
MAX_RETRIES = int(os.getenv("LLM_API_MAX_RETRIES", 3))
INITIAL_DELAY = float(os.getenv("LLM_API_INITIAL_DELAY", 1.0))
BACKOFF_FACTOR = float(os.getenv("LLM_API_BACKOFF_FACTOR", 2.0))

# --- Circuit Breaker Logic ---
CIRCUIT_BREAKER_FAILURE_THRESHOLD = int(os.getenv("CIRCUIT_BREAKER_FAILURE_THRESHOLD", 3))
CIRCUIT_BREAKER_RECOVERY_TIMEOUT = int(os.getenv("CIRCUIT_BREAKER_RECOVERY_TIMEOUT", 60)) # 1 minute

class BaseLLMClient:
    """Cliente base con lógica de reintentos y caché."""
    """Cliente base con lógica de reintentos, caché y circuit breaker."""
    def __init__(self, api_key, model, api_url, headers, timeout=45):
        self.api_key = api_key
        self.model = model
        self.api_url = api_url
        self.headers = headers
        self.timeout = timeout
        self.logger = logging.getLogger(self.__class__.__name__)

        # Circuit Breaker State
        self._circuit_state = "CLOSED"
        self._failure_count = 0
        self._last_failure_time = None

    def _build_payload(self, prompt, model_override=None):
        raise NotImplementedError

    def _parse_response(self, data):
        raise NotImplementedError

    def _trip_breaker(self):
        """Activa el circuit breaker al estado OPEN."""
        if self._circuit_state != "OPEN":
            self._circuit_state = "OPEN"
            self._last_failure_time = time.time()
            self.logger.critical(f"CIRCUIT BREAKER TRIPPED! La API {self.api_url} está ahora en estado OPEN.")

    def _reset_breaker(self):
        """Resetea el circuit breaker al estado CLOSED."""
        if self._circuit_state != "CLOSED":
            self.logger.info("CIRCUIT BREAKER RESET! La API está ahora en estado CLOSED.")
        self._circuit_state = "CLOSED"
        self._failure_count = 0

    async def chat(self, prompt, model_override=None):
        if self._circuit_state == "OPEN":
            if (time.time() - self._last_failure_time) > CIRCUIT_BREAKER_RECOVERY_TIMEOUT:
                self._circuit_state = "HALF-OPEN"
                self.logger.warning("CIRCUIT BREAKER está ahora en HALF-OPEN. Permitiendo una petición de prueba.")
            else:
                self.logger.warning(f"Circuit Breaker está OPEN. Petición a {self.api_url} rechazada.")
                return "Error: La API no está disponible temporalmente (Circuit Breaker abierto)."

        if not self.api_key:
            self.logger.error("API Key no configurada.")
            return "Error: API Key no configurada."

        effective_model = model_override or self.model
        payload = self._build_payload(prompt, effective_model)
        
        cache_key = hashlib.md5(f"{self.__class__.__name__}:{json.dumps(payload, sort_keys=True)}".encode()).hexdigest()
        if cache_key in llm_cache:
            self.logger.info(f"Cache HIT for {self.__class__.__name__}")
            return llm_cache[cache_key]
        
        self.logger.info(f"Cache MISS for {self.__class__.__name__}. Calling API: {self.api_url}")
        
        delay = INITIAL_DELAY
        for attempt in range(MAX_RETRIES):
            try:
                async with httpx.AsyncClient(follow_redirects=True) as client:
                    resp = await client.post(self.api_url, headers=self.headers, json=payload, timeout=self.timeout)
                    resp.raise_for_status()
                    data = resp.json()
                    result = self._parse_response(data)
                    
                    llm_cache[cache_key] = result
                    self._reset_breaker() # Éxito, resetea el circuit breaker
                    return result
            except (httpx.HTTPStatusError, httpx.RequestError) as e:
                self._failure_count += 1
                self.logger.warning(f"Fallo {self._failure_count}/{CIRCUIT_BREAKER_FAILURE_THRESHOLD} registrado para {self.api_url}")

                if self._circuit_state == "HALF-OPEN" or self._failure_count >= CIRCUIT_BREAKER_FAILURE_THRESHOLD:
                    self._trip_breaker()
                    return f"Error: La API de {self.__class__.__name__} no respondió y el circuit breaker se ha activado."

                if isinstance(e, httpx.HTTPStatusError) and e.response.status_code < 500:
                    if e.response.status_code == 402: return f"❌ Error: La cuenta se ha quedado sin saldo."
                    if e.response.status_code != 429:
                        self.logger.error(f"Error HTTP no reintentable ({e.response.status_code}): {e.response.text}")
                        return f"Error HTTP {e.response.status_code}: {e.response.text}"
                
                self.logger.warning(f"Intento {attempt + 1}/{MAX_RETRIES} fallido: {e}. Reintentando en {delay:.1f}s...")
                await asyncio.sleep(delay)
                delay *= BACKOFF_FACTOR
            except Exception as e:
                self.logger.error(f"Excepción inesperada: {str(e)}")
                self._trip_breaker() # Un error inesperado también debería activar el breaker
                return f"Excepción en cliente LLM: {str(e)}"
        
        self.logger.error(f"Todos los {MAX_RETRIES} intentos fallaron.")
        self._trip_breaker() # Si todos los reintentos fallan, activa el breaker
        return f"Error: La API no respondió después de {MAX_RETRIES} intentos."

class OpenAICompatibleClient(BaseLLMClient):
    def _build_payload(self, prompt, model):
        return {"model": model, "messages": [{"role": "user", "content": prompt}]}
    
    def _parse_response(self, data):
        return data["choices"][0]["message"]["content"]

class ClaudeClient(BaseLLMClient):
    def _build_payload(self, prompt, model):
        return {"model": model, "max_tokens": 1024, "messages": [{"role": "user", "content": prompt}]}

    def _parse_response(self, data):
        return data["content"][0]["text"]

class LLMClientFactory:
    def __init__(self):
        self.api_keys = {
            "GROQ": os.getenv("GROQ_API_KEY"),
            "DEEPSEEK": os.getenv("DEEPSEEK_API_KEY"),
            "OPENAI": os.getenv("OPENAI_API_KEY"),
            "ANTHROPIC": os.getenv("ANTHROPIC_API_KEY"),
            "GEMINI": os.getenv("GEMINI_API_KEY"),
        }
        self.clients = {}
        self.logger = logging.getLogger(self.__class__.__name__)
        self._initialize_clients()

    def _initialize_clients(self):
        if self.api_keys["GROQ"]:
            self.clients["groq"] = OpenAICompatibleClient(self.api_keys["GROQ"], "llama-3.3-70b-versatile", "https://api.groq.com/openai/v1/chat/completions", {"Authorization": f"Bearer {self.api_keys['GROQ']}"})
        if self.api_keys["DEEPSEEK"]:
            self.clients["deepseek"] = OpenAICompatibleClient(self.api_keys["DEEPSEEK"], "deepseek-reasoner", "https://api.deepseek.com/v1/chat/completions", {"Authorization": f"Bearer {self.api_keys['DEEPSEEK']}"})
        if self.api_keys["OPENAI"]:
            api_base = os.getenv("OPENAI_API_BASE", "https://openrouter.ai/api/v1/chat/completions")
            self.clients["openai"] = OpenAICompatibleClient(self.api_keys["OPENAI"], "gpt-4o", api_base, {"Authorization": f"Bearer {self.api_keys['OPENAI']}"})
        if self.api_keys["ANTHROPIC"]:
            self.clients["claude"] = ClaudeClient(self.api_keys["ANTHROPIC"], "claude-3-5-sonnet-20240620", "https://api.anthropic.com/v1/messages", {"x-api-key": self.api_keys["ANTHROPIC"], "anthropic-version": "2023-06-01", "Content-Type": "application/json"})
        if self.api_keys["GEMINI"]:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_keys["GEMINI"])
                self.clients["gemini"] = genai
                self.logger.info("Cliente Gemini configurado.")
            except ImportError:
                self.logger.warning("Paquete 'google-generativeai' no instalado. El cliente Gemini no estará disponible.")
            except Exception as e:
                self.logger.error(f"Error inicializando Gemini: {e}")

    def get_client(self, provider):
        client = self.clients.get(provider.lower())
        if not client:
            self.logger.error(f"Cliente para '{provider}' no disponible o no configurado (falta API Key?).")
        return client