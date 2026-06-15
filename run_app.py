# -*- coding: utf-8 -*-
import os
import subprocess
import shutil # Para mover archivos
import time
import sys

def pre_flight_check():
    print("🔍 Iniciando verificación de sistema...")
    
    # 1. Ejecutar limpieza de archivos (BOM y encodings)
    try:
        # Ejecutar script de limpieza directamente
        subprocess.run([sys.executable, "clean_bom.py"], check=True)
        print("✨ Archivos normalizados (BOM eliminado).")
    except Exception as e:
        print(f"⚠️ Error en limpieza: {e}")

    # 2. Reorganizar archivos (moverlos a sus carpetas correctas)
    project_path = os.path.dirname(os.path.abspath(__file__))
    motors_dir = os.path.join(project_path, "motors")
    visualizers_dir = os.path.join(project_path, "visualizers")
    scrapers_dir = os.path.join(project_path, "scrapers")
    utils_dir = os.path.join(project_path, "utils")
    data_dir = os.path.join(project_path, "data")

    # Crear directorios si no existen
    for d in [motors_dir, visualizers_dir, scrapers_dir, utils_dir, data_dir]:
        os.makedirs(d, exist_ok=True)

    # Crear o limpiar __init__.py en carpetas clave
    for folder in [motors_dir, scrapers_dir, visualizers_dir, utils_dir]:
        init_path = os.path.join(folder, "__init__.py")
        if not os.path.exists(init_path) or os.path.getsize(init_path) == 0:
            with open(init_path, 'w', encoding='utf-8') as f:
                f.write("# -*- coding: utf-8 -*-\n") # Asegurar encoding
            print(f"📄 Creado/Limpiado __init__.py en: {os.path.basename(folder)}")

    # Archivos a mover a motors/
    files_to_move_to_motors = [
        "motor_mlb_pro.py", "motor_nba_pro_v17.py", "motor_fut_pro.py",
        "backtest_engine.py", "motor_lanzadores.py", "predictor_hr.py",
        "predictor_ponches.py", "motor_momentum.py", "motor_decision_inteligente.py",
        "motor_over_under.py", "motor_momentum_profesional.py"
    ]
    for file_name in files_to_move_to_motors:
        src = os.path.join(project_path, file_name)
        dst = os.path.join(motors_dir, file_name)
        if os.path.exists(src) and not os.path.exists(dst):
            shutil.move(src, dst)
            print(f"🚚 Movido: {file_name} -> motors/")
        elif os.path.exists(src) and os.path.exists(dst):
            os.remove(src) # Eliminar duplicado en raíz
            print(f"🚚 Movido: {file_name} -> motors/")

    # Archivos a mover a visualizers/
    files_to_move_to_visualizers = ["visual_mlb.py"]
    for file_name in files_to_move_to_visualizers:
        src = os.path.join(project_path, file_name)
        dst = os.path.join(visualizers_dir, file_name)
        if os.path.exists(src) and not os.path.exists(dst):
            shutil.move(src, dst)
            print(f"🚚 Movido: {file_name} -> visualizers/")

    # 3. Verificar importaciones críticas (ejemplo)
    try:
        import motors.motor_mlb_pro
        import motors.predictor_hr
        import visualizers.visual_mlb
        print("✅ Importaciones críticas verificadas.")
    except Exception as e:
        print(f"❌ Error en importaciones críticas: {e}")
        sys.exit(1) # Salir si hay errores de importación

    print("🚀 Todo listo. Lanzando Streamlit...\n")

if __name__ == "__main__":
    pre_flight_check()
    try:
        # Lanza streamlit automáticamente
        subprocess.run(["streamlit", "run", "main_vision_completo.py"])
    except KeyboardInterrupt:
        print("\n👋 Programa cerrado por el usuario.")
    except Exception as e:
        print(f"❌ Error al lanzar Streamlit: {e}")