# -*- coding: utf-8 -*-
import pandas as pd
import os
import sys

# Parche para permitir importaciones desde la raíz del proyecto
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL_DIR = os.path.dirname(os.path.abspath(__file__))

# Evitar que utils.py local bloquee la visibilidad del paquete utils
if LOCAL_DIR in sys.path:
    sys.path.remove(LOCAL_DIR)
sys.path.insert(0, ROOT_DIR)

from motors.motor_mlb_pro import analizar_mlb_pro_v20
from utils.cerebro_gemini_pro import CerebroGeminiPro
import json

def comparar_analisis_mlb(partido_sample):
    print("🔬 COMPARADOR QUIRÚRGICO DE MOTORES\n")
    
    # 1. Resultado Heurístico (Matemático)
    res_heur = analizar_mlb_pro_v20(partido_sample)
    
    # 2. Resultado IA (Razonamiento)
    gemini = CerebroGeminiPro()
    res_ia = {"pick": "N/A", "confianza": 0}
    if gemini.client:
        raw = gemini.orquestrar_decision_final("MLB", str(partido_sample), str(res_heur))
        try: res_ia = json.loads(raw)
        except: pass

    # 3. Tabla Comparativa
    data = {
        "Métrica": ["Pick Sugerido", "Confianza %", "Stake", "Power Factor"],
        "Heurístico (Matemático)": [res_heur['pick'], res_heur['confianza'], res_heur['stake'], res_heur['poder_home']],
        "IA (Razonamiento)": [res_ia.get('pick'), res_ia.get('confianza'), res_ia.get('stake', 'N/A'), "N/A"]
    }
    
    df = pd.DataFrame(data)
    print(df.to_string(index=False))
    
    diff = abs(res_heur['confianza'] - res_ia.get('confianza', 0))
    if diff > 15:
        print(f"\n⚠️ DISCREPANCIA ALTA ({diff}%): Revisar si la IA detectó un factor (clima/lesión) que el motor ignoró.")
    else:
        print("\n✅ CONCORDANCIA ALTA: Los motores están alineados.")

if __name__ == "__main__":
    # Ejemplo de partido para comparar
    sample = {
        "local": "New York Yankees",
        "visitante": "Boston Red Sox",
        "pitchers": {
            "local": {"nombre": "Gerrit Cole"},
            "visitante": {"nombre": "Brayan Bello"}
        }
    }
    comparar_analisis_mlb(sample)