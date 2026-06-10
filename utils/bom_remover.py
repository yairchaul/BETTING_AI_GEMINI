# -*- coding: utf-8 -*-
"""
SCRIPT DE LIMPIEZA DE BOM (Byte Order Mark)

Este script recorre todos los directorios y subdirectorios del proyecto en busca de
archivos .py y elimina el carácter BOM (U+FEFF) si lo encuentra al inicio del archivo.

El BOM es un carácter invisible que algunos editores añaden y que causa un
SyntaxError en Python.

Uso:
    python -m utils.bom_remover
"""
import os
import sys

# La secuencia de bytes que representa el BOM en UTF-8
UTF8_BOM = b'\xef\xbb\xbf'

def scan_and_fix_bom(directory='.'):
    """
    Escanea recursivamente un directorio en busca de archivos .py y elimina el BOM.
    """
    fixed_files_count = 0
    print("--- 🧹 Iniciando limpieza de caracteres BOM en archivos .py ---")

    for root, _, files in os.walk(directory):
        # Ignorar directorios de virtual environment
        if 'venv' in root or 'env' in root or '.git' in root:
            continue

        for filename in files:
            if filename.endswith('.py'):
                filepath = os.path.join(root, filename)
                try:
                    with open(filepath, 'rb') as f:
                        content = f.read()
                    if content.startswith(UTF8_BOM):
                        print(f"🛠️  Corrigiendo archivo: {filepath}")
                        content = content[len(UTF8_BOM):]
                        with open(filepath, 'wb') as f:
                            f.write(content)
                        fixed_files_count += 1
                except Exception as e:
                    print(f"❌ Error procesando {filepath}: {e}", file=sys.stderr)
    
    print(f"\n--- ✅ Limpieza completada. Se corrigieron {fixed_files_count} archivos. ---")

if __name__ == "__main__":
    # Ejecutar desde la raíz del proyecto
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    scan_and_fix_bom(project_root)
