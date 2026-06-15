# -*- coding: utf-8 -*-
import os
import sys

def clean_python_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
            content = f.read()
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception:
        return False

def ejecutar_limpieza_automatica(directorio="."):
    count = 0
    for root, _, files in os.walk(directorio):
        if '.venv' in root or '__pycache__' in root:
            continue
        for name in files:
            if name.endswith(".py"):
                path = os.path.join(root, name)
                if clean_python_file(path):
                    count += 1
    return count

if __name__ == "__main__":
    procesados = ejecutar_limpieza_automatica(os.path.dirname(os.path.dirname(__file__)))
    print(f"✅ Limpieza de BOM completada. {procesados} archivos analizados.")