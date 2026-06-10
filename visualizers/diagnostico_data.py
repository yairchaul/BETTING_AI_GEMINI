# -*- coding: utf-8 -*-
import os
import json

print("--- DIAGNÓSTICO DE ARCHIVOS DE DATOS ---")

data_files = [
    "data/aprendizaje_semanal.json",
    "resultados_reales_15dias.json",
    "hr_datasets_completos.json"
]

for file_path in data_files:
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                json.load(f)
            print(f"✅ {file_path}: OK")
        except json.JSONDecodeError:
            print(f"❌ {file_path}: CORRUPTO (Error de JSON)")
    else:
        print(f"⚠️ {file_path}: NO ENCONTRADO")