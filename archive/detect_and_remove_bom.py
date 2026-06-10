# -*- coding: utf-8 -*-
import os

def clean_all_boms(directory):
    """Escanea y elimina el BOM (U+FEFF) de todos los archivos .py"""
    print(f"🔍 Iniciando limpieza de codificación en: {directory}")
    count = 0
    
    for root, dirs, files in os.walk(directory):
        # Omitir carpetas ocultas o virtuales
        if any(x in root for x in ['.git', '__pycache__', '.venv']):
            continue
            
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                with open(file_path, 'rb') as f:
                    content = f.read()
                
                # El BOM de UTF-8 son los bytes: 0xEF, 0xBB, 0xBF
                if content.startswith(b'\xef\xbb\xbf'):
                    with open(file_path, 'wb') as f:
                        f.write(content[3:])
                    print(f"  ✅ BOM eliminado: {file}")
                    count += 1
    print(f"✨ Proceso terminado. Se limpiaron {count} archivos.")

if __name__ == "__main__":
    base_path = os.path.dirname(os.path.abspath(__file__))
    clean_all_boms(base_path)
