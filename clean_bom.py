# -*- coding: utf-8 -*-
import os
import sys

def clean_python_file(file_path):
    try:
        # utf-8-sig detecta y elimina automáticamente el BOM al leer
        with open(file_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
            content = f.read()
        
        # Guardar como UTF-8 normal (sin firma)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"❌ Error en {file_path}: {e}")
        return False

def ejecutar_limpieza_automatica(directorio="."):
    """Escanea y limpia automáticamente todos los archivos .py del proyecto."""
    print(f"🧹 Iniciando limpieza automática de BOM en: {os.path.abspath(directorio)}")
    count = 0
    for root, dirs, files in os.walk(directorio):
        if '.venv' in root or '__pycache__' in root: continue
        for name in files:
            if name.endswith(".py"):
                path = os.path.join(root, name)
                if clean_python_file(path):
                    count += 1
    return count

if __name__ == "__main__":
    # Si este script se ejecuta manualmente o es llamado por un SyntaxError
    procesados = ejecutar_limpieza_automatica()
    print(f"✅ Limpieza completada. {procesados} archivos analizados y normalizados.")