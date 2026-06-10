# -*- coding: utf-8 -*-
import os
import sys
import json
from dotenv import load_dotenv

# Parche para permitir importaciones desde la raíz del proyecto
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL_DIR = os.path.dirname(os.path.abspath(__file__))

# Evitar que utils.py en la carpeta local bloquee al paquete utils
if LOCAL_DIR in sys.path:
    sys.path.remove(LOCAL_DIR)
sys.path.insert(0, ROOT_DIR)

from utils.cerebro_gemini_pro import CerebroGeminiPro
from utils.groq_ufc_engine import GroqUFCEngine

def test_ias_all_sports():
    load_dotenv(override=True)
    print("🚀 INICIANDO TEST DE IAs MULTIDEPORTE\n")

    gemini = CerebroGeminiPro()
    groq = GroqUFCEngine()

    prompts = {
        "NBA": "Analiza este matchup de NBA enfocado en el Spread y Total de puntos. Datos: Lakers vs Celtics, Spread +/- 5.5.",
        "MLB": "Analiza este partido de MLB. Enfoque: Pitchers abridores y probabilidad de Home Runs. Datos: Yankees (Gerrit Cole) vs Red Sox.",
        "UFC": "Analiza este combate de UFC. Enfoque: Cardio en altitud y KO Rate. Datos: Moreno vs Royval.",
        "FUTBOL": "Analiza este partido de Futbol. Enfoque: BTTS (Ambos Anotan) y Over 2.5. Datos: Real Madrid vs Barcelona."
    }

    results = {"Gemini": {}, "Groq": {}}

    for sport, prompt in prompts.items():
        print(f"--- Probando {sport} ---")
        
        # Test Gemini
        if gemini.client:
            try:
                res = gemini.orquestrar_decision_final(sport, "Evento Test", prompt)
                results["Gemini"][sport] = "✅ OK"
                print(f"  Gemini {sport}: OK")
            except Exception as e:
                results["Gemini"][sport] = f"❌ Error: {str(e)[:50]}"
        
        # Test Groq
        if groq.client:
            try:
                # Usamos el método genérico de orquestación
                res = groq.orquestrar_decision_final(sport, "Evento Test", prompt)
                results["Groq"][sport] = "✅ OK"
                print(f"  Groq {sport}: OK")
            except Exception as e:
                results["Groq"][sport] = f"❌ Error: {str(e)[:50]}"

    print("\n" + "="*30)
    print("📊 RESUMEN DE CONECTIVIDAD")
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    test_ias_all_sports()