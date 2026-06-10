# run_all_scrapers.py
import subprocess
import sys
import os
import logging

# Configuración de logging según Regla 20
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

logger.info("="*50)
logger.info("   EJECUTANDO TODOS LOS SCRAPERS")
logger.info("="*50)

scrapers = [
    (os.path.join("scrapers", "espn_mlb.py"), "MLB"),
    (os.path.join("scrapers", "espn_ufc.py"), "UFC"),
    (os.path.join("scrapers", "espn_nba.py"), "NBA"),
    (os.path.join("scrapers", "espn_futbol.py"), "Fútbol")
]

for scraper, nombre in scrapers:
    logger.info(f"📡 Ejecutando scraper de {nombre} ({scraper_path})...")
    try:
        # Usar sys.executable para asegurar que se usa el intérprete correcto
        # text=True para decodificar stdout/stderr como texto
        # encoding='utf-8' para compatibilidad con Regla 1
        result = subprocess.run([sys.executable, scraper_path], capture_output=True, text=True, timeout=60, encoding='utf-8')
        if result.returncode == 0:
            logger.info(f"✅ {nombre} completado")
        else:
            logger.warning(f"⚠️ {nombre} tuvo errores (código {result.returncode}): {result.stderr.strip()[:500]}")
            logger.debug(f"Salida completa de {nombre}: {result.stdout.strip()}")
    except Exception as e:
        logger.error(f"❌ Error en {nombre}: {e}")

logger.info("✅ Scrapers ejecutados")
