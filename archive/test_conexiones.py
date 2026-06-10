# -*- coding: utf-8 -*-
"""
test_conexiones.py
Verifica la integridad de las conexiones entre módulos y la estructura de archivos.
Mencionado en la Regla 23 de 'instrucciones_ia.md'.
"""
import os
import sys
import importlib.util
from dotenv import load_dotenv
import logging

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Añadir el directorio raíz del proyecto al PYTHONPATH
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

logger.info(f"Iniciando verificación de conexiones en: {PROJECT_ROOT}")

def check_file_exists(path_parts):
    """Verifica si un archivo existe en la ruta especificada."""
    full_path = os.path.join(PROJECT_ROOT, *path_parts)
    if os.path.exists(full_path):
        logger.info(f"✅ Archivo encontrado: {os.path.join(*path_parts)}")
        return True
    else:
        logger.error(f"❌ Archivo NO encontrado: {os.path.join(*path_parts)}")
        return False

def check_module_import(module_name, path_parts=None):
    """Intenta importar un módulo y verifica si es exitoso."""
    try:
        if path_parts:
            # Para módulos que no están directamente en PYTHONPATH
            spec = importlib.util.spec_from_file_location(module_name, os.path.join(PROJECT_ROOT, *path_parts))
            if spec is None:
                raise ImportError(f"No se pudo encontrar la especificación para {module_name}")
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
        else:
            importlib.import_module(module_name)
        logger.info(f"✅ Módulo importado correctamente: {module_name}")
        return True
    except ImportError as e:
        logger.error(f"❌ Error al importar módulo {module_name}: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Error inesperado al cargar módulo {module_name}: {e}")
        return False

def check_api_keys():
    """Verifica la existencia del archivo .env y las API keys (Regla 21)."""
    logger.info("--- VERIFICACIÓN DE API KEYS (.env) ---")
    env_path = os.path.join(PROJECT_ROOT, ".env")
    load_dotenv(dotenv_path=env_path) # Cargar .env para la verificación

    env_ok = True
    if os.path.exists(env_path):
        logger.info(f"✅ Archivo .env encontrado en: {env_path}")
    else:
        logger.error(f"❌ Archivo .env NO encontrado. (Regla 21)")
        env_ok = False

    gemini_key = os.getenv("GEMINI_API_KEY")
    groq_key = os.getenv("GROQ_API_KEY")
    openrouter_key = os.getenv("OPENROUTER_API_KEY")

    if gemini_key and gemini_key.strip():
        logger.info("✅ GEMINI_API_KEY encontrada.")
    else:
        logger.error("❌ GEMINI_API_KEY NO encontrada o vacía. (Regla 21)")
        env_ok = False
    if groq_key and groq_key.strip():
        logger.info("✅ GROQ_API_KEY encontrada.")
    else:
        logger.error("❌ GROQ_API_KEY NO encontrada o vacía. (Regla 21)")
        env_ok = False
    if openrouter_key and openrouter_key.strip():
        logger.info("✅ OPENROUTER_API_KEY encontrada.")
    else:
        logger.warning("⚠️ OPENROUTER_API_KEY no encontrada en .env (Necesaria para MCP fuera de Kiro).")
    
    return env_ok

def run_all_tests():
    """Ejecuta todas las verificaciones."""
    logger.info("--- VERIFICACIÓN DE ESTRUCTURA DE DIRECTORIOS ---")
    directories = ["motors", "scrapers", "visualizers", "utils", "data", ".kiro"]
    all_dirs_ok = True
    for d in directories:
        full_path = os.path.join(PROJECT_ROOT, d)
        if os.path.isdir(full_path):
            logger.info(f"✅ Directorio encontrado: {d}")
        else:
            logger.error(f"❌ Directorio NO encontrado: {d}")
            all_dirs_ok = False
    
    logger.info("\n--- VERIFICACIÓN DE ARCHIVOS CLAVE ---")
    key_files = [
        ("main_vision_completo.py",),
        ("run_all_scrapers.py",),
        ("data", "predicciones_log.json"), # Asumiendo que existe o se creará
        ("data", "aprendizaje_semanal.json"),
        ("data", "config_mlb.json"),
        (".kiro", "specs", "backtest-semanal.md"),
        (".kiro", "hooks", "on-error.md"),
        ("instrucciones_ia.md",)
    ]
    all_files_ok = True
    for f_path in key_files:
        if not check_file_exists(f_path):
            all_files_ok = False

    logger.info("\n--- VERIFICACIÓN DE IMPORTACIONES DE MÓDULOS ---")
    modules_to_check = [
        ("analista_total",),
        ("cerebro_gemini_pro",),
        ("motors", "__init__.py"), # Check motors package init
        ("scrapers", "espn_mlb.py"),
        ("utils", "fuzzy_matching.py"), # Assuming this exists or will exist
    ]
    all_imports_ok = True
    for mod_name_parts in modules_to_check:
        if not check_module_import(mod_name_parts[0], mod_name_parts[1:] if len(mod_name_parts) > 1 else None):
            all_imports_ok = False
            
    # Verificar API Keys
    api_keys_ok = check_api_keys()

    if all_dirs_ok and all_files_ok and all_imports_ok and api_keys_ok:
        logger.info("\n🎉 ¡Todas las conexiones y la estructura del proyecto parecen correctas!")
    else:
        logger.error("\n⚠️ Se detectaron problemas en las conexiones o la estructura del proyecto. Revisa los logs.")

if __name__ == "__main__":
    run_all_tests()