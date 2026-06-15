# run_all_scrapers.py
import subprocess
import sys
import os
import logging
import platform

# --- Configuración de logging ---
# Regla 20: Usar logging para eventos y errores.
# Regla 1: Usar UTF-8.
# Parche para consolas de Windows que no manejan bien UTF-8.
if platform.system() == "Windows":
    # Usamos una forma más robusta de reconfigurar stdout/stderr
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout) # Asegura que el log vaya a la consola
    ]
)
logger = logging.getLogger(__name__)

# --- Lista de Scrapers a Ejecutar ---
# (ruta_relativa, nombre_descriptivo, timeout_en_segundos)
# Regla 2: Estructura de carpetas. Asumimos que los scrapers están en /scrapers
# o en la raíz si no se han movido.
SCRAPERS_A_EJECUTAR = [
    ("scrapers/espn_mlb.py", "Partidos MLB (ESPN)", 60),
    ("scrapers/espn_nba.py", "Partidos NBA (ESPN)", 60),
    ("scrapers/espn_ufc.py", "Eventos UFC (ESPN)", 60),
    ("scrapers/espn_futbol.py", "Partidos Fútbol (ESPN)", 120),
    ("scrapers/ufc_stats_scraper.py", "Stats Detalladas UFC (Playwright)", 300), # Mayor timeout para Playwright
    ("scraper_caliente_selenium.py", "Odds y Pitchers (Caliente/Selenium)", 300), # Mayor timeout para Selenium
    ("scraper_lineups_espn.py", "Lineups MLB (ESPN)", 60),
    ("obtener_datos_ponches.py", "Líderes de Ponches (MLB API)", 60),
    ("obtener_resultados_reales.py", "Resultados Reales (MLB API)", 120),
    ("update_clima_data.py", "Actualización de Clima", 60),
]

def main():
    """Función principal que ejecuta todos los scrapers."""
    project_root = os.path.dirname(os.path.abspath(__file__))
    logger.info("="*60)
    logger.info("🚀 INICIANDO ACTUALIZACIÓN MASIVA DE DATOS (TODOS LOS SCRAPERS)")
    logger.info("="*60)

    for scraper_rel_path, nombre, timeout in SCRAPERS_A_EJECUTAR:
        full_path = os.path.join(project_root, scraper_rel_path)

        # Fallback: si no está en /scrapers, buscar en la raíz.
        if not os.path.exists(full_path):
            fallback_path = os.path.join(project_root, os.path.basename(scraper_rel_path))
            if os.path.exists(fallback_path):
                full_path = fallback_path
            else:
                logger.warning(f"⏭️  Omitiendo: No se encontró el scraper '{nombre}' en '{scraper_rel_path}' ni en la raíz.")
                continue

        logger.info(f"📡 Ejecutando scraper de {nombre}...")
        try:
            result = subprocess.run(
                [sys.executable, full_path],
                capture_output=True, text=True, timeout=timeout, encoding='utf-8', errors='replace'
            )
            if result.returncode == 0:
                logger.info(f"✅ {nombre} completado con éxito.")
                if result.stdout: logger.debug(f"   Salida de {nombre}: {result.stdout.strip()[:200]}...")
            else:
                logger.warning(f"⚠️  {nombre} finalizó con errores (código {result.returncode}).")
                logger.warning(f"   Error: {result.stderr.strip()[:500]}")
        except subprocess.TimeoutExpired:
            logger.error(f"❌ TIMEOUT: El scraper de {nombre} excedió el límite de {timeout} segundos.")
        except Exception as e:
            logger.error(f"❌ ERROR CRÍTICO ejecutando {nombre}: {e}")

    logger.info("="*60)
    logger.info("🎉 Todos los scrapers han sido ejecutados.")
    logger.info("="*60)

if __name__ == "__main__":
    main()
