# diagnostico_data.py
import json
import os
import shutil
from datetime import datetime

def diagnosticar_archivos():
    print("\n🔍 DIAGNÓSTICO DE INTEGRIDAD DE DATOS")
    print("="*50)
    
    archivos = [
        "resultados_finales_corregidos.json",
        "pitchers_hoy_selenium.json",
        "data/stats_lanzadores_hoy.json",
        "data/ufc_stats_cache.json",
        "data/betting_stats.db"
    ]
    
    backup_dir = f"data/backups_{datetime.now().strftime('%Y%m%d')}"
    os.makedirs(backup_dir, exist_ok=True)
    
    errores = 0
    for ruta in archivos:
        if not os.path.exists(ruta):
            print(f"❌ FALTA: {ruta}")
            errores += 1
            continue
        
        try:
            if ruta.endswith('.json'):
                with open(ruta, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                backup_path = os.path.join(backup_dir, os.path.basename(ruta))
                shutil.copy(ruta, backup_path)
                print(f"✅ OK+BAK | {ruta} | {len(data)} registros")
            else:
                size = os.path.getsize(ruta) / 1024
                print(f"✅ OK | {ruta} | {size:.1f} KB")
        except json.JSONDecodeError as e:
            print(f"🔥 CORRUPTO: {ruta} - {e}")
            errores += 1
        except Exception as e:
            print(f"❓ ERROR: {ruta} - {e}")
            errores += 1
    
    print("="*50)
    if errores == 0:
        print("✅ SISTEMA DE DATOS INTEGRO")
    else:
        print(f"⚠️ {errores} problemas detectados")
    
    return errores

if __name__ == "__main__":
    diagnosticar_archivos()
