# -*- coding: utf-8 -*-
import os
import sys
import logging
import sqlite3
import json
from dotenv import load_dotenv

# Configuración de rutas compatibles con Windows
BASE_DIR = r"C:/Users/Yair/Desktop/BETTING_AI"
load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SystemVerifier")

def check_database():
    db_path = os.path.join(BASE_DIR, "data", "betting_stats.db")
    if not os.path.exists(db_path):
        logger.error(f"❌ Base de datos no encontrada en {db_path}")
        return False
    try:
        conn = sqlite3.connect(db_path)
        # Verificar campos críticos (HT en futbol)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(historial_equipos)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'puntos_ht' not in columns:
            logger.warning("⚠️ Falta columna 'puntos_ht'. Ejecutando migración...")
            cursor.execute("ALTER TABLE historial_equipos ADD COLUMN puntos_ht INTEGER")
        conn.close()
        logger.info("✅ Base de datos íntegra.")
        return True
    except Exception as e:
        logger.error(f"❌ Error DB: {e}")
        return False

def check_ias():
    # Test Gemini (Punto 4)
    try:
        from cerebro_gemini_pro import CerebroGeminiPro
        gk = os.getenv("GEMINI_API_KEY")
        gemini = CerebroGeminiPro(gk)
        if gemini.test_connection():
            logger.info("✅ Gemini 2.5 Flash: Conectado.")
        else:
            logger.error("❌ Gemini: Fallo de autenticación.")
    except Exception as e:
        logger.error(f"❌ Error al cargar Gemini: {e}")

    # Test Groq
    try:
        from groq import Groq
        if os.getenv("GROQ_API_KEY"):
            logger.info("✅ Groq API Key: Detectada.")
    except: pass

def check_scrapers():
    # Verificar archivos de salida de scrapers (Punto 8)
    mlb_json = os.path.join(BASE_DIR, "resultados_finales_corregidos.json")
    if os.path.exists(mlb_json):
        with open(mlb_json, 'r', encoding='utf-8', errors='replace') as f:
            data = json.load(f)
            tbd_count = sum(1 for p in data if p.get('pitchers', {}).get('local', {}).get('nombre') == 'TBD')
            if tbd_count > 0:
                logger.warning(f"⚠️ Hay {tbd_count} partidos con pitchers TBD. Se requiere scraper Caliente.mx")
    else:
        logger.error("❌ Archivo de partidos MLB no encontrado.")

if __name__ == "__main__":
    print("="*50)
    print("🎯 BETTING_AI NEON - VERIFICADOR DE CONEXIÓN")
    print("="*50)
    check_database()
    check_ias()
    check_scrapers()
    print("="*50)
    print("🚀 Verificación completada. Si no hay errores críticos, lanza run_app.py")