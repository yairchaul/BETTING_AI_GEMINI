# maintenance.py
import logging
import sys
import os

# Asegurarse de que el directorio raíz esté en el path para los imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from scrapers.stats_populator import scrape_and_save_mlb_stats, scrape_and_save_nba_stats
    from database_manager import db
except ImportError as e:
    print(f"Error de importación: {e}. Asegúrate de que los módulos necesarios están en el path.")
    sys.exit(1)

# Configuración del logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_maintenance():
    """
    Ejecuta las tareas de mantenimiento del sistema:
    1. Poblar/actualizar las estadísticas de jugadores en la base de datos.
    2. Limpiar los registros de caché antiguos en la base de datos.
    """
    logger.info("🚀 Iniciando tareas de mantenimiento del sistema BETTING_AI...")

    # --- 1. Poblar/Actualizar Estadísticas ---
    logger.info("--- PASO 1: Actualizando estadísticas de jugadores ---")
    try:
        logger.info("⚾ Actualizando estadísticas de MLB...")
        scrape_and_save_mlb_stats()
        logger.info("✅ Estadísticas de MLB actualizadas.")
    except Exception as e:
        logger.error(f"❌ Error al actualizar estadísticas de MLB: {e}", exc_info=True)

    try:
        logger.info("🏀 Actualizando estadísticas de NBA...")
        scrape_and_save_nba_stats()
        logger.info("✅ Estadísticas de NBA actualizadas.")
    except Exception as e:
        logger.error(f"❌ Error al actualizar estadísticas de NBA: {e}", exc_info=True)
    
    # --- 2. Limpiar Caché Antiguo de la Base de Datos ---
    logger.info("\n--- PASO 2: Limpiando caché antiguo de la base de datos ---")
    try:
        lineups_deleted, ufc_deleted = db.clean_old_cache(lineup_days=2, ufc_days=7)
        logger.info(f"✅ Limpieza de caché completada: {lineups_deleted} lineups y {ufc_deleted} peleadores eliminados.")
    except Exception as e:
        logger.error(f"❌ Error al limpiar el caché de la base de datos: {e}", exc_info=True)
    
    logger.info("\n🎉 Mantenimiento del sistema completado.")

if __name__ == "__main__":
    run_maintenance()