# -*- coding: utf-8 -*-
import json
import os
import pandas as pd

def auto_ajustar_pesos_mlb(win_rate):
    """Ajusta quirúrgicamente los pesos si el rendimiento es bajo"""
    pesos_path = "data/pesos_motores.json"
    try:
        if os.path.exists(pesos_path):
            with open(pesos_path, 'r') as f: pesos = json.load(f)
        else:
            pesos = {"power_factor_ml": 5, "ml_pitcher_vulnerable_penalty": 0.85, "hr_ou_impact": 0.015}

        print(f"⚙️ Auto-ajustando pesos (WR Actual: {win_rate:.1f}%)...")
        
        if win_rate < 55:
            # Si perdemos mucho, bajamos el impacto de HR y subimos penalización a pitchers malos
            pesos["power_factor_ml"] = max(2, pesos.get("power_factor_ml", 5) - 1)
            pesos["ml_pitcher_vulnerable_penalty"] = max(0.70, pesos.get("ml_pitcher_vulnerable_penalty", 0.85) - 0.05)
            print("   ⚠️ Pesos ajustados por bajo rendimiento (Enfoque Conservador).")
        elif win_rate > 70:
            # Si el sistema es muy preciso, podemos ser más agresivos con el Power Factor
            pesos["power_factor_ml"] += 0.5
            print("   🚀 Rendimiento excelente. Incrementando peso de Power Factor.")

        with open(pesos_path, 'w') as f:
            json.dump(pesos, f, indent=2)
        return True
    except Exception as e:
        print(f"❌ Fallo al actualizar pesos: {e}")

def ejecutar_backtest_maestro_mlb():
    print("🧪 INICIANDO BACKTEST MAESTRO MLB (V24.8)")
    print("="*50)
    
    path_res = "data/resultados_reales_15dias.json"
    if not os.path.exists(path_res):
        print("❌ Error: No se encontró data/resultados_reales_15dias.json")
        return

    with open(path_res, "r", encoding="utf-8") as f:
        datos = json.load(f)

    stats = {
        "winners": {"total": 0, "hits": 0},
        "over_under": {"total": 0, "hits": 0, "diff_avg": []},
        "home_runs": {"total_detectados": 0, "cumplidos": 0},
        "pitchers_k": {"total": 0, "k_promedio": 0}
    }
    
    # Cargar bitácora para cruzar picks
    try:
        bitacora = pd.read_csv("data/bitacora_maestra.csv")
    except: bitacora = pd.DataFrame()

    for juego in datos:
        # 1. Auditoría Ganadores
        stats["winners"]["total"] += 1
        if not bitacora.empty:
            evento_str = f"{juego['away']} vs {juego['home']}"
            pick_row = bitacora[bitacora['Evento'].str.contains(juego['home'], na=False)]
            if not pick_row.empty:
                pick_final = str(pick_row.iloc[0]['Apuesta']).lower()
                if juego['ganador'].lower() in pick_final:
                    stats["winners"]["hits"] += 1
        
        # 2. Auditoría Home Runs Reales
        stats["home_runs"]["total_detectados"] += len(juego.get("home_runs", []))
        
        # 3. Auditoría Ponches
        for side in ["home", "away"]:
            if side in juego.get("pitchers_k", {}):
                stats["pitchers_k"]["total"] += 1
                stats["pitchers_k"]["k_promedio"] += juego["pitchers_k"][side]["k"]

    # Resumen de aprendizaje
    print(f"📊 RESULTADOS DEL BACKTEST ({len(datos)} partidos):")
    print(f"---")
    
    # Win Rate ML
    wr = (stats["winners"]["hits"] / stats["winners"]["total"] * 100) if stats["winners"]["total"] > 0 else 0
    print(f"🏆 Win Rate ML: {wr:.1f}%")
    
    # Disparar Auto-Ajuste
    auto_ajustar_pesos_mlb(wr)

    # Cálculo de HR Ratio (HR por partido detectado)
    hr_ratio = stats["home_runs"]["total_detectados"] / len(datos)
    print(f"💣 Home Runs: Se detectaron {stats['home_runs']['total_detectados']} HR totales.")
    print(f"   Promedio: {hr_ratio:.2f} HR por partido.")
    
    # Cálculo de K Promedio
    if stats["pitchers_k"]["total"] > 0:
        avg_k = stats["pitchers_k"]["k_promedio"] / stats["pitchers_k"]["total"]
        print(f"🧤 Ponches: Los abridores promediaron {avg_k:.1f} K por salida.")
    
    print(f"\n💡 CONCLUSIÓN PARA MOTORES:")
    if hr_ratio > 1.8:
        print("⚠️ Tendencia de bateo ALTA. Considerar subir umbrales de O/U.")
    elif hr_ratio < 1.0:
        print("⚠️ Tendencia de pitcheo ALTA. Los candidatos de HR deben ser más estrictos.")
    
    # Guardar reporte de aprendizaje
    reporte = {
        "timestamp": pd.Timestamp.now().isoformat(),
        "partidos_analizados": len(datos),
        "hr_per_game": hr_ratio,
        "k_per_pitcher": avg_k if stats["pitchers_k"]["total"] > 0 else 0,
        "win_rate_ml": wr
    }
    
    with open("data/aprendizaje_backtest.json", "w", encoding="utf-8") as f:
        json.dump(reporte, f, indent=2)
    print(f"\n✅ Reporte de aprendizaje guardado en data/aprendizaje_backtest.json")

if __name__ == "__main__":
    ejecutar_backtest_maestro_mlb()