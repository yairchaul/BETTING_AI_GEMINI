# -*- coding: utf-8 -*-
import os
import requests
import logging
from dotenv import load_dotenv

# Configuración de log para errores de API
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR): os.makedirs(LOG_DIR)
LOG_FILE = os.path.join(LOG_DIR, "api_errors.log")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def validar_todas_las_apis():
    load_dotenv(override=True)
    reporte = {}
    
    # 1. Test Gemini
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={gemini_key}"
        res = requests.get(url)
        reporte['Gemini'] = "✅ Válida" if res.status_code == 200 else f"❌ Error {res.status_code}"
        if res.status_code != 200:
            logging.error(f"Gemini API Error {res.status_code}: {res.text}")
    
    # 2. Test Groq
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        url = "https://api.groq.com/openai/v1/models"
        res = requests.get(url, headers={"Authorization": f"Bearer {groq_key}"})
        reporte['Groq'] = "✅ Válida" if res.status_code == 200 else f"❌ Error {res.status_code}"
        if res.status_code != 200:
            logging.error(f"Groq API Error {res.status_code}: {res.text}")

    # 3. Test DeepSeek
    ds_key = os.getenv("DEEPSEEK_API_KEY")
    if ds_key:
        url = "https://api.deepseek.com/models"
        res = requests.get(url, headers={"Authorization": f"Bearer {ds_key}"})
        reporte['DeepSeek'] = "✅ Válida" if res.status_code == 200 else f"❌ Error {res.status_code}"
        if res.status_code != 200:
            logging.error(f"DeepSeek API Error {res.status_code}: {res.text}")

    return reporte

if __name__ == "__main__":
    print("🔍 Iniciando escaneo de APIs...")
    resultados = validar_todas_las_apis()
    for api, status in resultados.items():
        print(f"{api}: {status}")