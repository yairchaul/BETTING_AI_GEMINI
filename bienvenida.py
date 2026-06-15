# -*- coding: utf-8 -*-
"""
SCRIPT DE BIENVENIDA Y CONFIGURACIÓN - BETTING_AI
Ejecuta este script al iniciar en una nueva PC para validar el entorno.
"""
import os
import sys
import subprocess
import importlib
from dotenv import load_dotenv

def print_banner():
    print("=" * 70)
    print("🎯 BIENVENIDO A BETTING_AI GEMINI - SISTEMA DE PUESTA EN MARCHA 🎯")
    print("=" * 70)
    print("🔍 Iniciando diagnóstico de entorno en la nueva PC...\n")

def check_folders():
    print("📂 Verificando estructura de directorios...")
    folders = ["data", "logs", "motors", "scrapers", "visualizers", "utils", ".kiro"]
    missing = []
    for f in folders:
        if os.path.isdir(f):
            print(f"  ✅ {f}/")
        else:
            print(f"  ❌ {f}/ (No encontrada)")
            missing.append(f)
    return missing

def check_dependencies():
    print("\n📦 Verificando dependencias de Python...")
    libs = ["streamlit", "pandas", "requests", "openai", "google.generativeai", "python-dotenv"]
    for lib in libs:
        try:
            # Caso especial para python-dotenv
            if lib == "python-dotenv":
                importlib.import_module("dotenv")
            else:
                importlib.import_module(lib.replace("-", "_"))
            print(f"  ✅ {lib}")
        except ImportError:
            print(f"  ❌ {lib} (No instalada - Ejecuta: pip install {lib})")

def check_env():
    print("\n🔑 Verificando credenciales (.env)...")
    if not os.path.exists(".env"):
        print("  ❌ ARCHIVO .env NO ENCONTRADO.")
        print("     Recuerda copiar tu archivo .env manualmente desde tu respaldo.")
        return False
    
    load_dotenv()
    keys = ["GEMINI_API_KEY", "GROQ_API_KEY", "DEEPSEEK_API_KEY"]
    for k in keys:
        val = os.getenv(k)
        if val:
            print(f"  ✅ {k}: Detectada (****{val[-4:]})")
        else:
            print(f"  ⚠️ {k}: NO DETECTADA")
    return True

def run_initial_maintenance():
    print("\n🛠️ Ejecutando mantenimiento inicial...")
    # Limpieza de BOM para evitar SyntaxError
    if os.path.exists("clean_bom.py"):
        print("  🧹 Limpiando archivos (Eliminando BOM)...")
        subprocess.run([sys.executable, "clean_bom.py"])
    
    # Test de conexiones
    if os.path.exists("test_conexiones.py"):
        print("  🔗 Verificando integridad de módulos...")
        subprocess.run([sys.executable, "test_conexiones.py"])

def migration_reminders():
    print("\n" + "!" * 70)
    print("📢 RECORDATORIOS DE MIGRACIÓN PARA LA NUEVA PC:")
    print("-" * 70)
    print("1. 🧠 CONTINUE: ¿Copiaste la carpeta %USERPROFILE%\\.continue?")
    print("   (Es vital para mantener mi configuración y el servidor MCP)")
    print("2. 🏗️ GIT: Estás usando el repo 'BETTING_AI_GEMINI'")
    print("   Ejecuta: git checkout version-gemini")
    print("3. 🗄️ DB: Verifica que 'data/betting_stats.db' tenga tus datos históricos.")
    print("4. 🌐 CHROME: Instala Google Chrome para los scrapers de Selenium.")
    print("!" * 70)

def check_git_branch():
    print("\n🔱 Verificando rama de Git...")
    try:
        branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"]).decode().strip()
        if branch == "version-gemini":
            print(f"  ✅ Estás en la rama correcta: {branch}")
        else:
            print(f"  ⚠️ Estás en la rama '{branch}'. Se recomienda cambiar a 'version-gemini'.")
    except:
        print("  ⚠️ No se pudo determinar la rama de Git.")

def main():
    print_banner()
    
    missing_folders = check_folders()
    check_dependencies()
    env_ok = check_env()
    check_git_branch()
    
    run_initial_maintenance()
    migration_reminders()
    
    print("\n" + "=" * 70)
    if not missing_folders and env_ok:
        print("💎 ¡SISTEMA LISTO PARA OPERAR!")
        print("Ejecuta: python run_app.py")
    else:
        print("⚠️ EL SISTEMA REQUIERE ATENCIÓN ANTES DE INICIAR.")
    print("=" * 70)

if __name__ == "__main__":
    main()