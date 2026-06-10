# -*- coding: utf-8 -*-
"""
SCRIPT DE LIMPIEZA DE RAÍZ - BETTING_AI NEON
Mueve archivos a sus carpetas correspondientes según la estructura del proyecto.
"""
import os
import shutil
import sys

# --- PARCHE DE CONSOLA WINDOWS (UTF-8) ---
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

def ensure_dir(path):
    """Asegura que un directorio exista y crea un __init__.py si es necesario."""
    os.makedirs(path, exist_ok=True)
    init_file = os.path.join(path, "__init__.py")
    if not os.path.exists(init_file):
        with open(init_file, 'w', encoding='utf-8') as f:
            f.write("# -*- coding: utf-8 -*-\n")

def move_file(filename, destination_folder):
    """Mueve un archivo a la carpeta de destino si no está ya allí."""
    src_path = os.path.join(PROJECT_ROOT, filename)
    dst_dir = os.path.join(PROJECT_ROOT, destination_folder)
    dst_path = os.path.join(dst_dir, filename)

    if os.path.exists(src_path):
        if not os.path.exists(dst_path):
            ensure_dir(dst_dir)
            shutil.move(src_path, dst_path)
            print(f"✅ Movido: '{filename}' a '{destination_folder}/'")
        else:
            print(f"ℹ️ '{filename}' ya existe en '{destination_folder}/'. Eliminando duplicado en raíz.")
            try:
                os.remove(src_path)
            except Exception as e:
                print(f"⚠️ No se pudo eliminar duplicado {filename}: {e}")

def delete_file(filename):
    """Elimina un archivo de la raíz si existe."""
    file_path = os.path.join(PROJECT_ROOT, filename)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            print(f"🗑️ Eliminado (Temp): '{filename}'")
        except Exception as e:
            print(f"⚠️ Error eliminando {filename}: {e}")

def archive_data_file(filename):
    """Mueve un archivo de data/ a archive/data/ para limpiar el historial activo."""
    src_path = os.path.join(PROJECT_ROOT, "data", filename)
    dst_dir = os.path.join(PROJECT_ROOT, "archive", "data")
    dst_path = os.path.join(dst_dir, filename)

    if os.path.exists(src_path):
        ensure_dir(dst_dir)
        if not os.path.exists(dst_path):
            shutil.move(src_path, dst_path)
            print(f"📦 Archivado (Historial Data): '{filename}'")
        else:
            try: os.remove(src_path)
            except: pass

def limpiar_raiz():
    print("="*60)
    print("🧹 INICIANDO LIMPIEZA DE RAÍZ DEL PROYECTO")
    print("="*60)

    ensure_dir(os.path.join(PROJECT_ROOT, "archive"))
    print("="*60)

    # Definir archivos y sus destinos
    files_to_motors = [ # Files that are currently in root and should be in motors/
        "hr_analyzer_v24_1.py",
        "analizador_ufc_heurístico.py", # In context, but already in motors/
        "motor_lanzadores.py", # In context
        "predictor_hr_v5.py", # In context, will be moved as predictor_hr.py
        "predictor_ponches.py", # In context
        "motor_over_under.py", # In context
        "motor_momentum_profesional.py",
        "motor_decision_inteligente.py", # In context
        "motor_nba_pro_v17.py",
        "analizador_futbol_heurístico_mejorado.py",
        "mlb_stats_api.py",
        "groq_aprendizaje.py", # In context
        "motor_ufc_pro.py", # In context
    ]

    files_to_visualizers = [
        "visual_nba_mejorado.py", # Not in context
        "visual_ufc_final.py", # Not in context
        "visual_futbol_triple.py", # Not in context
        "radar_triples_nba.py", # In context
        "render_unificado.py", # Not in context
        "panel_inteligencia.py", # In context
        "visual_ufc_ko.py",
        "visual_ufc_mejorado.py",
        "visual_nba_props.py",
        "visual_completo.py",
        "visual_backtest.py",
    ]

    files_to_scrapers = [
        "scraper_caliente_selenium.py",
        "balldontlie_client.py",
        "fetch_historical_soccer.py",
        "update_clima_data.py",
        "nba_com_scraper.py", # Added to scrapers
        "unificar_visuales_ufc.py", # In context
        "espn_futbol.py", # In context
        "mlb_hybrid_scraper.py", # In context
        "mlb_scraper_oficial.py", # In context
        "mlb_resultados_scraper.py", # In context
        "ufc_scraper_unificado.py", # In context
        "ufc_odds_scraper.py", # In context
        "tapology_scraper.py", # In context
        "espn_ufc.py", # In context
        "espn_mlb.py", # In context
        "mlb_scraper_dinamico.py", # In context
        "obtener_datos_ponches.py", # In context
        "obtener_resultados_reales.py", # In context
        "obtener_15dias.py", # In context
        "mlb_scraper.py", # In context
        "ufc_stats_scraper_backup.py", # In context
        "manager.py", # In context
        "fetch_nba_stats.py", # In context
        "mlb_balldontlie_scraper.py", # In context
        "caliente_odds_scraper.py", # In context
        "espn_data_pipeline.py",
    ]

    files_to_utils = [
        "analista_total.py", # Not in context
        "cerebro_gemini_pro.py", # In context
        "cerebro_new_ai.py", # In context
        "deepseek_client.py", # In context
        "database_manager.py", # In context
        "mlb_records_real.py", # Not in context
        "clima_mlb.py", # Not in context
        "groq_ufc_engine.py", # Not in context
        "bet_tracker.py", # Not in context
        "fuzzy_matching.py", # Not in context
        "mapeo_equipos.py", # In context
        "utils.py", # In context
        "error_handler.py", # In context
        "auditor_puntos_ht.py", # In context
        "auditor_resultados.py", # In context
        "generar_inteligencia_umpires.py", # In context
        "notificador_backtest.py", # In context
        "analizador_tendencias.py", # In context
        "analisis_umbrales.py", # In context
        "super_prompt.py", # In context
        "backtest_15_dias.py",
    ]

    files_to_data = [
        "config_mlb.json",
        "odds_ufc.json",
        "resultados_finales_corregidos.json",
        "pitchers_hoy_selenium.json",
        "crear_umpires_db.py", # In context
        "crear_estadios_db.py", # In context
        "contexto_backtesting.py", # In context
    ]

    files_to_archive = [
        "test_conexiones.py",
        "test_connections.py",
        "test_deepseek.py",
        "test_deepseek_api_key.py",
        "test_ias.py",
        "test_simple.py",
        "test_system.py",
        "verificar_sistema.py",
        "verify_all_systems.py",
        "diagnostico_balldontlie.py",
        "fix_gemini.py",
        "fix_and_optimize.py",
        "cleanup_tests.py",
        "clean_bom.py",
        "remove_bom.py",
        "clean_utf8.py",
        "detect_and_remove_bom.py",
        "backtest_auditoria.py",
        "backtest_real.py",
        "auditoria_k.py",
        "mass_backtest_mlb.py",
        "preparar_mudanza.py",
        "inyectar_pitchers_reales.py"
    ]

    # Archivos de la carpeta /data que se pueden archivar (MLB 2025 / aprendizaje viejo)
    data_files_to_archive = [
        "resultados_reales_15dias.json",
        "hr_apuestas.json",
        "aprendizaje_semanal.json"
    ]

    # Archivos temporales o de cache que pueden borrarse
    files_to_delete = [
        "caliente_odds_cache.json",
        "pitchers_espn_api.json",
        "resultados_reales_5dias.json",
        "datos_ponches_reales.json"
    ]

    # Ejecutar movimientos
    for f in files_to_motors: move_file(f, "motors")
    for f in files_to_visualizers: move_file(f, "visualizers")
    for f in files_to_scrapers: move_file(f, "scrapers")
    for f in files_to_utils: move_file(f, "utils")
    for f in files_to_data: move_file(f, "data")
    for f in files_to_archive: move_file(f, "archive")
    for f in data_files_to_archive: archive_data_file(f)
    
    # Limpieza de archivos temporales
    for f in files_to_delete: delete_file(f)

    # Eliminar carpetas __pycache__ redundantes
    for root, dirs, files in os.walk(PROJECT_ROOT):
        if "__pycache__" in dirs:
            shutil.rmtree(os.path.join(root, "__pycache__"))

    print("\n🎉 Limpieza de raíz completada. Por favor, revisa tu estructura de carpetas.")
    print("⚠️ Recuerda que algunos scripts temporales de 'fix' deben ser eliminados manualmente después de usarse.")
    print("="*60)

if __name__ == "__main__":
    limpiar_raiz()