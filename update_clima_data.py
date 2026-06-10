# -*- coding: utf-8 -*-
"""
SCRIPT PARA ACTUALIZAR DATOS DE CLIMA EN resultados_finales_corregidos.json
Llamado por un Agent Hook
"""
import json
import os
from clima_mlb import ClimaMLB

def update_clima_data():
    print("☁️ Actualizando datos de clima en partidos MLB...")
    
    clima_engine = ClimaMLB()
    
    try:
        with open("resultados_finales_corregidos.json", "r+", encoding="utf-8") as f:
            partidos = json.load(f)
            
            for partido in partidos:
                venue = partido.get("venue", "")
                if venue:
                    clima = clima_engine.obtener_clima(venue)
                    partido["clima"] = clima
                    print(f"   ✅ Clima para {venue}: {clima.get('descripcion')}")
                else:
                    partido["clima"] = clima_engine.obtener_clima("Default Stadium") # Fallback
            
            f.seek(0) # Volver al inicio del archivo
            json.dump(partidos, f, indent=2, ensure_ascii=False)
            f.truncate() # Recortar si el nuevo contenido es más corto
            
        print("✅ Datos de clima actualizados en resultados_finales_corregidos.json")
    except FileNotFoundError:
        print("⚠️ resultados_finales_corregidos.json no encontrado. Ejecuta el scraper MLB primero.")
    except Exception as e:
        print(f"❌ Error al actualizar datos de clima: {e}")

if __name__ == "__main__":
    update_clima_data()