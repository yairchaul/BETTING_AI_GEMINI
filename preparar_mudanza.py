# -*- coding: utf-8 -*-
"""
SCRIPT DE PREPARACIÓN PARA MIGRACIÓN - BETTING_AI
Este script automatiza la sincronización con GitHub y crea un paquete de respaldo
con todo lo necesario para continuar en una nueva PC.
"""
import os
import subprocess
import zipfile
from datetime import datetime

def run_cmd(cmd):
    try:
        # Ejecutamos con shell=True para comandos de Git en Windows
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8')
        return res.returncode, res.stdout, res.stderr
    except Exception as e:
        return 1, "", str(e)

def main():
    print("="*60)
    print("🎯 BETTING_AI - ASISTENTE DE MIGRACIÓN A NUEVA PC 🎯")
    print("="*60)

    # 1. Sincronización Git
    print("\n📡 1. Sincronizando cambios con GitHub...")
    
    # Intentar crear rama y cambiar a ella
    run_cmd("git checkout -b version-gemini")
    run_cmd("git checkout version-gemini")
    
    run_cmd("git add .")
    rc, out, err = run_cmd('git commit -m "Sincronización Pre-Migración: Versión Gemini con Lógica Local"')
    
    if "nothing to commit" in out.lower():
        print("  ✅ El repositorio local ya está al día.")
    else:
        print("  ✅ Cambios confirmados localmente.")
    
    print("  📤 Subiendo rama 'version-gemini' al servidor...")
    rc, out, err = run_cmd("git push -u origin version-gemini --force")
    if rc == 0:
        print("  🚀 ¡GitHub actualizado con éxito!")
    else:
        print(f"  ⚠️ No se pudo subir a GitHub (Verifica tu conexión o permisos): {err.strip()}")

    # 2. Creación de Respaldo Local (Zip)
    print("\n📦 2. Creando paquete de respaldo (archivos sensibles y DB)...")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    zip_name = f"RESPALDO_MIGRACION_{datetime.now().strftime('%Y%m%d_%H%M')}.zip"
    
    # Elementos críticos que no van a Git o son vitales
    elementos = [".env", ".kiro", "data", "instrucciones_ia.md"]
    
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for item in elementos:
            full_path = os.path.join(base_dir, item)
            if os.path.exists(full_path):
                if os.path.isfile(full_path):
                    zipf.write(full_path, item)
                    print(f"  ➕ Archivo incluido: {item}")
                else:
                    for root, dirs, files in os.walk(full_path):
                        for file in files:
                            f_path = os.path.join(root, file)
                            zipf.write(f_path, os.path.relpath(f_path, base_dir))
                    print(f"  ➕ Carpeta incluida: {item}/")

    print(f"\n✅ ARCHIVO DE RESPALDO CREADO: {zip_name}")
    print("\n" + "!"*60)
    print("📢 ACCIÓN MANUAL CRÍTICA:")
    print("Debes copiar la carpeta de configuración de Continue de tu usuario:")
    print(f"📂 RUTA: {os.path.join(os.path.expanduser('~'), '.continue')}")
    print("!"*60)
    print("\n¡Todo listo! Lleva ese archivo .zip y la carpeta .continue a tu nueva PC.")

if __name__ == "__main__":
    main()