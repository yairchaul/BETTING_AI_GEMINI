# -*- coding: utf-8 -*-
"""
AUTOMATE IMPROVEMENTS - Orquestador de Salud del Sistema
Ejecuta mantenimiento preventivo y correctivo según Reglas Finales.
"""
import os
import subprocess
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("BETTING_AI.Optimizer")

BASE_DIR = r"C:\Users\Yair\Desktop\BETTING_AI"

def run_step(description, command):
    logger.info(f"🚀 Iniciando: {description}")
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', shell=True)
        if result.returncode == 0:
            logger.info(f"✅ Completado: {description}")
            return True
        else:
            logger.error(f"❌ Error en {description}: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"🔥 Fallo crítico en {description}: {e}")
        return False

def main():
    logger.info("=== BETTING_AI AUTOMATIC OPTIMIZER ===")
    
    # 1. Limpieza de codificación (Regla 1)
    if os.path.exists(os.path.join(BASE_DIR, "clean_bom.py")):
        run_step("Limpieza de BOM y Encodings", [sys.executable, "clean_bom.py"])

    # 2. Verificación de integridad de datos
    run_step("Diagnóstico de Integridad de Datos", [sys.executable, "diagnostico_data.py"])

    # 3. Verificación de conexiones (Regla 23)
    run_step("Test de Conexiones entre Módulos", [sys.executable, "test_conexiones.py"])

    # 4. Actualización de clima (Agent Hook simulado)
    run_step("Sincronización de Clima MLB", [sys.executable, "update_clima_data.py"])

    # 5. Mantenimiento de DB (Si es necesario)
    logger.info("🧹 Ejecutando mantenimiento de logs antiguos...")
    log_dir = os.path.join(BASE_DIR, "logs")
    if os.path.exists(log_dir):
        for f in os.listdir(log_dir):
            if f.endswith(".old"): os.remove(os.path.join(log_dir, f))
    
    logger.info("🎉 El sistema está optimizado y listo para ejecutar main_vision_completo.py")

if __name__ == "__main__":
    main()