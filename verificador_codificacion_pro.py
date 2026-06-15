# -*- coding: utf-8 -*-
import os
import sys

def verificar_archivos():
    print("🔍 Iniciando auditoría de codificación y caracteres invisibles...")
    print("="*60)
    
    errores = 0
    for root, dirs, files in os.walk("."):
        for file in files:
            if file.endswith((".py", ".json", ".txt", ".md")):
                path = os.path.join(root, file)
                try:
                    with open(path, "rb") as f:
                        raw = f.read()
                    
                    # 1. Detectar BOM
                    if raw.startswith(b'\xef\xbb\xbf'):
                        print(f"🚩 BOM DETECTADO: {path} (Elimínalo con clean_bom.py)")
                        errores += 1
                    
                    # 2. Intentar decodificar como UTF-8 puro
                    raw.decode("utf-8")
                    
                except UnicodeDecodeError as e:
                    print(f"❌ ERROR DE CODIFICACIÓN: {path}")
                    print(f"   Detalle: {e}")
                    errores += 1
                except Exception as e:
                    print(f"⚠️ Error inesperado en {path}: {e}")

    print("="*60)
    if errores == 0:
        print("✅ Todos los archivos están limpios y en UTF-8 puro.")
    else:
        print(f"⚠️ Se encontraron {errores} problemas. Usa automate_improvements.py para sanear.")

if __name__ == "__main__":
    verificar_archivos()