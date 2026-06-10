# -*- coding: utf-8 -*-
import json
import asyncio
import time
import hashlib
import os
import sys
from dotenv import load_dotenv
from cachetools import TTLCache

from cachetools import cached
# --- Add project root to sys.path ---
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from mcp.server.fastmcp import FastMCP
    import google.generativeai as genai
    from utils.llm_client_factory import LLMClientFactory
except ImportError as e:
    print(f"Error: Faltan dependencias críticas para el servidor MCP: {e}")
    print("Por favor, ejecuta: pip install -r requirements.txt")
    sys.exit(1)

# --- Configuration ---
LOG_FILE = os.path.join(PROJECT_ROOT, "logs", "mcp_unified_server.log")
import logging # Move logging import here to be safe
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO, # Changed to INFO for less verbosity in log, DEBUG for more
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)
logging.info("Cargando variables de entorno desde .env")
load_dotenv(override=True) 

# Initialize FastMCP server
mcp = FastMCP("analizador-betting-local")
llm_factory = LLMClientFactory()

start_time = time.time()

_new_ai_instance = None

def get_db():
    """Lazy-load the database manager to prevent import-time side effects."""
    try:
        from utils.database_manager import db
        return db
    except ImportError as e:
        logging.error(f"Fallo al importar database_manager: {e}. Asegúrate que el archivo utils/database_manager.py existe.")
        return None
    except Exception as e:
        logging.error(f"Error inicializando database_manager: {e}")
        return None

def get_new_ai():
    """Lazy-load and initialize CerebroNewAI safely."""
    global _new_ai_instance
    if _new_ai_instance is None:
        try:
            logging.info("Inicializando CerebroNewAI por primera vez.")
            from utils.cerebro_new_ai import CerebroNewAI
            # Defensive initialization
            _new_ai_instance = CerebroNewAI()
        except Exception as e:
            logging.error(f"Fallo al inicializar CerebroNewAI: {e}")
            _new_ai_instance = None
    return _new_ai_instance


# --- Caching for LLM calls ---
# Hacemos los parámetros de la caché configurables a través de variables de entorno.
LLM_CACHE_MAXSIZE = int(os.getenv("LLM_CACHE_MAXSIZE", 500))
LLM_CACHE_TTL_SECONDS = int(os.getenv("LLM_CACHE_TTL_SECONDS", 600)) # 10 minutos por defecto

# Creamos cachés separadas para llamadas a LLM y a la base de datos.
# La caché de LLM ahora es manejada por LLMClientFactory
llm_cache = TTLCache(maxsize=LLM_CACHE_MAXSIZE, ttl=LLM_CACHE_TTL_SECONDS)
DB_CACHE_MAXSIZE = int(os.getenv("DB_CACHE_MAXSIZE", 100))
DB_CACHE_TTL_SECONDS = int(os.getenv("DB_CACHE_TTL_SECONDS", 60)) # 1 minuto por defecto
db_cache = TTLCache(maxsize=DB_CACHE_MAXSIZE, ttl=DB_CACHE_TTL_SECONDS)

def cache_key_generator(func, *args, **kwargs):
    """Genera una clave de caché única para una función y sus argumentos."""
    arg_str = json.dumps(args, sort_keys=True, default=str)
    kwarg_str = json.dumps(kwargs, sort_keys=True, default=str)
    return hashlib.md5(f"{func.__name__}:{arg_str}:{kwarg_str}".encode()).hexdigest()

# --- Domain-Specific Tools (from mcp_server_betting.py) ---

@mcp.tool()
@cached(db_cache, key=lambda equipo, stat, deporte="nba": cache_key_generator(consultar_stats_jugador, equipo, stat, deporte))
def consultar_stats_jugador(equipo: str, stat: str, deporte: str = "nba"):
    """
    Consulta las mejores estadísticas de jugadores en la base de datos local.
    stat puede ser: 'three_pm', 'points', 'hr', 'avg'
    """
    logging.info(f"Tool: consultar_stats_jugador - Equipo: {equipo}, Stat: {stat}, Deporte: {deporte}")
    db_instance = get_db()
    if not db_instance:
        return "Error: La base de datos no está disponible."
    resultado = db_instance.get_top_player_stat(equipo, stat, limit=3, deporte=deporte)
    return json.dumps(resultado, ensure_ascii=False)

@mcp.tool()
@cached(llm_cache, key=lambda deporte, local, visitante: cache_key_generator(analizar_con_new_ai, deporte, local, visitante))
def analizar_con_new_ai(deporte: str, local: str, visitante: str):
    """
    Usa el motor Cerebro New AI para obtener una predicción avanzada.
    """
    logging.info(f"Tool: analizar_con_new_ai - Deporte: {deporte}, Local: {local}, Visitante: {visitante}")
    partido = {"local": local, "visitante": visitante}
    heuristica = {"recomendacion": "Analizar flujo de dinero", "confianza": 50} # Placeholder
    ai = get_new_ai()
    if not ai:
        return "Error: El motor CerebroNewAI no pudo ser inicializado. Revise los logs."
    respuesta = ai.orquestrar_decision_final(deporte, partido, heuristica)
    return respuesta

@mcp.tool()
@cached(db_cache, key=cache_key_generator)
def obtener_racha_equipo(equipo: str):
    """
    Obtiene la racha de fallos reciente de un equipo para detectar 'equipos trampa'.
    """
    logging.info(f"Tool: obtener_racha_equipo - Equipo: {equipo}")
    db_instance = get_db()
    if not db_instance:
        return "Error: La base de datos no está disponible."
    fallos = db_instance.obtener_racha_fallos(equipo)
    return f"El equipo {equipo} ha fallado {fallos} veces en los últimos picks."

@mcp.tool()
@cached(db_cache, key=cache_key_generator)
def analizar_nba_jerarquico(local: str, visitante: str):
    """
    Aplica el análisis Lambda (Expectativa de puntos) y reglas de NBA.
    """
    db = get_db()
    if not db:
        return "Error: La base de datos no está disponible."
        
    # Obtenemos promedios reales (simulado si no hay en DB según Regla 9)
    s_l = db.get_team_stats_detailed(local, 'nba')
    s_v = db.get_team_stats_detailed(visitante, 'nba')
    
    off_l, def_l = s_l.get('promedio_favor', 110), s_l.get('promedio_contra', 110)
    off_v, def_v = s_v.get('promedio_favor', 110), s_v.get('promedio_contra', 110)
    
    # Proyección Lambda
    proy_l = (off_l + def_v) / 2
    proy_v = (off_v + def_l) / 2
    diff_puntos = proy_l - proy_v
    
    # 1. Handicap >= 60% (Basado en la diferencia Lambda vs Spread)
    # Si nuestra proyección difiere del spread en > 4 puntos, alta confianza
    return json.dumps({
        "proyeccion": f"{local} {proy_l:.1f} - {visitante} {proy_v:.1f}",
        "pick_sugerido": local if diff_puntos > 0 else visitante,
        "confianza": min(92, 50 + abs(diff_puntos)*3),
        "lambda_diff": round(diff_puntos, 2)
    })

# --- LLM Chat Tools (adapted from servidor_mcp_propio.py) ---

@mcp.tool()
async def chat_groq(prompt: str, model: str = "llama-3.3-70b-versatile"):
    """
    Sends a chat prompt to the Groq API.
    """
    client = llm_factory.get_client("groq")
    if not client:
        return "Error: Cliente Groq no disponible. Verifica la API Key."
    return await client.chat(prompt, model_override=model)

@mcp.tool()
async def chat_deepseek(prompt: str, model: str = "deepseek-reasoner"):
    """
    Sends a chat prompt to the DeepSeek API.
    """
    client = llm_factory.get_client("deepseek")
    if not client:
        return "Error: Cliente DeepSeek no disponible. Verifica la API Key."
    return await client.chat(prompt, model_override=model)

@mcp.tool()
async def chat_gemini(prompt: str, model: str = "gemini-1.5-flash"):
    """
    Sends a chat prompt to Google Gemini API (Altamente recomendado por su nivel gratuito).
    """
    genai_module = llm_factory.get_client("gemini")
    if not genai_module:
        return "Error: Cliente Gemini no disponible. Verifica la API Key."
    try:
        logging.info(f"Configurando y llamando a Gemini con el modelo {model}")
        model_instance = genai_module.GenerativeModel(model)
        response = await model_instance.generate_content_async(prompt)
        return response.text
    except Exception as e:
        logging.error(f"Error en Gemini: {str(e)}")
        return f"Error en Gemini: {str(e)}"

@mcp.tool()
async def chat_openai(prompt: str, model: str = "gpt-4o"):
    """
    Sends a chat prompt to the OpenAI API (or OpenRouter compatible).
    """
    client = llm_factory.get_client("openai")
    if not client:
        return "Error: Cliente OpenAI/OpenRouter no disponible. Verifica la API Key."
    return await client.chat(prompt, model_override=model)

@mcp.tool()
async def chat_claude(prompt: str, model: str = "claude-3-5-sonnet-20240620"):
    """
    Sends a chat prompt to the Anthropic Claude API.
    """
    client = llm_factory.get_client("claude")
    if not client:
        return "Error: Cliente Claude no disponible. Verifica la API Key."
    return await client.chat(prompt, model_override=model)

# --- Server Management Tools ---

@mcp.tool()
def limpiar_cache_llm():
    """
    Limpia manualmente el caché en memoria de las respuestas de los LLM.
    Útil para forzar una nueva respuesta de las APIs de IA.
    """
    cache_size_before = len(llm_cache)
    llm_cache.clear()
    logging.info(f"Tool: limpiar_cache_llm - Caché de LLM limpiado. Se eliminaron {cache_size_before} entradas.")
    return f"✅ Caché de LLM limpiado. Se eliminaron {cache_size_before} entradas."

@mcp.tool()
def get_server_status():
    """
    Devuelve el estado y tiempo de actividad del servidor MCP unificado.
    Útil para verificar que el servidor correcto está en ejecución.
    """
    uptime_seconds = time.time() - start_time
    status = {
        "status": "OK",
        "server_name": "betting-ai-unified",
        "uptime_seconds": round(uptime_seconds),
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}"
    }
    logging.info(f"Tool: get_server_status - Estado: {status}")
    return json.dumps(status, indent=2)

if __name__ == "__main__":
    logging.info("Iniciando Servidor MCP Unificado de BETTING_AI...")
    mcp.run()