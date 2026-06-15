# -*- coding: utf-8 -*-
import json
import os

def run_health_check():
    checks = {
        "MLB Lanzadores": "data/stats_lanzadores_hoy.json",
        "MLB Partidos": "resultados_finales_corregidos.json",
        "UFC Stats": "data/ufc_stats_cache.json"
    }
    
    report = []
    for name, path in checks.items():
        if not os.path.exists(path):
            report.append(f"❌ {name}: Archivo no encontrado.")
            continue
        
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not data or len(data) == 0:
                report.append(f"⚠️ {name}: El archivo está vacío.")
            else:
                report.append(f"✅ {name}: Archivo cargado ({len(data)} entradas).")
                
                # --- VALIDACIÓN DE CALIDAD DE DATOS ---
                if name == "MLB Lanzadores":
                    invalidos = [k for k, v in data.items() if v.get('k9') == 0 or v.get('lanzador') == "TBD"]
                    if invalidos:
                        report.append(f"   🚩 ALERTA: {len(invalidos)} pitchers sin stats reales (K/9 en 0).")
                
                if name == "MLB Partidos":
                    sin_pitcher = [p for p in data if p.get("pitchers", {}).get("visitante", {}).get("nombre") == "TBD"]
                    if sin_pitcher:
                        report.append(f"   🚩 ALERTA: {len(sin_pitcher)} partidos sin abridores confirmados.")

                if name == "UFC Stats":
                    vaciocache = [k for k, v in data.items() if v.get('record') == "N/A"]
                    if vaciocache:
                        report.append(f"   🚩 ALERTA: {len(vaciocache)} peleadores con datos N/A en caché.")
                
    with open("data/health_report.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(report))
    
    print("🩺 Health Check completado.")

if __name__ == "__main__":
    run_health_check()