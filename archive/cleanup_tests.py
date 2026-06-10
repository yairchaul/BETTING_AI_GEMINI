# -*- coding: utf-8 -*-
"""
SCRIPT DE LIMPIEZA DE PRUEBAS - BETTING_AI NEON
Elimina archivos .py que son pruebas temporales y ya no son necesarios.
"""
import os
import sys

# --- PARCHE DE CONSOLA WINDOWS (UTF-8) ---
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

def cleanup_test_files():
    print("="*60)
    print("🧹 INICIANDO LIMPIEZA DE ARCHIVOS DE PRUEBA")
    print("="*60)

    test_files_to_remove = [
        "test_hr_candidates.py", "test_gemini.py", "test_gemini_simple.py",
        "test_gemini_new.py", "test_gemini_working.py", "test_gemini_manual.py",
        "test_strikes.py", "test_over_under.py",
    ]

    for filename in test_files_to_remove:
        file_path = os.path.join(PROJECT_ROOT, filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"✅ Eliminado archivo de prueba: '{filename}'")
        else:
            print(f"ℹ️ Archivo de prueba no encontrado (ya eliminado o no existe): '{filename}'")

    print("\n🎉 Limpieza de archivos de prueba completada.")
    print("="*60)

if __name__ == "__main__":
    cleanup_test_files()