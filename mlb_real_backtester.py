import pandas as pd
import json
import os
import re
from datetime import datetime, timedelta

def run_mlb_real_backtest(days_to_backtest=15):
    """
    Ejecuta un backtesting real para las predicciones de MLB de los últimos N días,
    comparándolas con los resultados reales y calculando métricas de rendimiento.
    """
    print(f"🚀 INICIANDO BACKTEST REAL MLB - ÚLTIMOS {days_to_backtest} DÍAS")
    print("=" * 60)

    bitacora_path = "data/bitacora_maestra.csv"
    resultados_path = "data/resultados_reales_15dias.json"

    if not os.path.exists(bitacora_path):
        print(f"❌ Error: No se encontró la bitácora maestra en {bitacora_path}")
        return
    if not os.path.exists(resultados_path):
        print(f"❌ Error: No se encontraron resultados reales en {resultados_path}")
        print("   Asegúrate de ejecutar 'python -m scrapers.mlb_resultados_scraper' para recolectar los datos.")
        return

    df_bitacora = pd.read_csv(bitacora_path)
    with open(resultados_path, "r", encoding="utf-8") as f:
        resultados_reales = json.load(f)

    # Convertir fechas a datetime objects para facilitar el filtrado y comparación
    df_bitacora['Fecha'] = pd.to_datetime(df_bitacora['Fecha'])
    for res in resultados_reales:
        res['fecha_dt'] = datetime.strptime(res['fecha'], '%Y-%m-%d')

    # Filtrar predicciones de MLB para los últimos 'days_to_backtest'
    cutoff_date = datetime.now() - timedelta(days=days_to_backtest)
    df_mlb_preds = df_bitacora[(df_bitacora['Deporte'] == 'MLB') & (df_bitacora['Fecha'] >= cutoff_date)].copy()

    if df_mlb_preds.empty:
        print(f"⚠️ No se encontraron predicciones de MLB en los últimos {days_to_backtest} días.")
        return

    # Inicializar métricas para cada tipo de apuesta
    metrics = {
        "Moneyline": {"total": 0, "hits": 0, "profit": 0.0},
        "Over/Under": {"total": 0, "hits": 0, "profit": 0.0},
        "Home Run": {"total": 0, "hits": 0, "profit": 0.0},
        "Handicap": {"total": 0, "hits": 0, "profit": 0.0},
        "Total": {"total": 0, "hits": 0, "profit": 0.0}
    }

    # Iterar sobre cada predicción de MLB
    for index, pred_row in df_mlb_preds.iterrows():
        pred_date = pred_row['Fecha'].date()
        pred_evento = pred_row['Evento'] # Ej: "Tampa Bay Rays vs Cleveland Guardians"
        pred_pick = str(pred_row['Apuesta']).strip().lower()
        pred_cuota = pred_row.get('cuota', 1.90) # Usar cuota real si está disponible, sino un valor por defecto

        # Determinar el tipo de apuesta
        pick_type = "Moneyline"
        if "over" in pred_pick or "under" in pred_pick:
            pick_type = "Over/Under"
        elif "hr" in pred_pick or "jonron" in pred_pick:
            pick_type = "Home Run"
        elif "+" in pred_pick or "-" in pred_pick:
            pick_type = "Handicap"
        
        # Buscar el resultado real correspondiente
        real_result = None
        for res in resultados_reales:
            res_date = res['fecha_dt'].date()
            # Coincidencia flexible por fecha y nombres de equipos
            if res_date == pred_date and \
               ((pred_evento.lower().find(res['home'].lower()) != -1 and pred_evento.lower().find(res['away'].lower()) != -1) or \
                (res['home'].lower().find(pred_evento.lower()) != -1 and res['away'].lower().find(pred_evento.lower()) != -1)):
                real_result = res
                break
        
        if real_result:
            is_hit = False
            if pick_type == "Moneyline":
                # Comparar el equipo ganador predicho con el ganador real
                if real_result['ganador'] and pred_pick.find(real_result['ganador'].lower()) != -1:
                    is_hit = True
            elif pick_type == "Over/Under":
                # Comparar el total de carreras real con la línea O/U predicha
                total_runs_real = real_result['total_runs']
                match_ou = re.search(r'(over|under)\s*(\d+\.?\d*)', pred_pick)
                if match_ou:
                    ou_type = match_ou.group(1)
                    ou_line = float(match_ou.group(2))
                    if (ou_type == "over" and total_runs_real > ou_line) or \
                       (ou_type == "under" and total_runs_real < ou_line):
                        is_hit = True
            elif pick_type == "Home Run" or pick_type == "Handicap":
                # Para HR y Handicap, asumimos que la columna 'acierto' en bitacora_maestra.csv
                # ya ha sido actualizada por el 'auditor_bitacora.py' o un proceso similar.
                is_hit = pred_row.get('acierto', False)

            # Actualizar métricas
            metrics[pick_type]["total"] += 1
            metrics["Total"]["total"] += 1
            
            if is_hit:
                metrics[pick_type]["hits"] += 1
                metrics["Total"]["hits"] += 1
                # Calcular ganancia (asumiendo 1 unidad de stake)
                metrics[pick_type]["profit"] += (pred_cuota - 1.0)
                metrics["Total"]["profit"] += (pred_cuota - 1.0)
            else:
                metrics[pick_type]["profit"] -= 1.0
                metrics["Total"]["profit"] -= 1.0
        else:
            print(f"⚠️ No se encontró resultado real para la predicción: {pred_evento} ({pred_date})")

    # Generar y mostrar el reporte final
    print("\n📊 REPORTE DE BACKTESTING MLB")
    print("=" * 60)
    for pick_type, data in metrics.items():
        if data["total"] > 0:
            win_rate = (data["hits"] / data["total"]) * 100
            roi = (data["profit"] / data["total"]) * 100 if data["total"] > 0 else 0
            print(f"--- {pick_type} ---")
            print(f"  Picks: {data['total']}")
            print(f"  Aciertos: {data['hits']}")
            print(f"  Win Rate: {win_rate:.2f}%")
            print(f"  Profit (unidades): {data['profit']:.2f}u")
            print(f"  ROI: {roi:.2f}%")
            print("-" * 20)
    
    print("\n✅ Backtesting completado.")

if __name__ == "__main__":
    # Asegurarse de que el directorio 'data' existe
    os.makedirs("data", exist_ok=True)
    
    # --- EJEMPLO DE DATOS PARA PRUEBA SI NO EXISTEN LOS ARCHIVOS ---
    # Esto es solo para que el script pueda ejecutarse de forma independiente.
    # En un entorno real, estos archivos serían generados por los scrapers y el sistema de picks.
    if not os.path.exists("data/bitacora_maestra.csv"):
        print("Creando bitácora maestra de ejemplo para la prueba...")
        sample_bitacora = pd.DataFrame([
            {"Fecha": (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'), "Deporte": "MLB", "Evento": "New York Yankees vs Boston Red Sox", "Apuesta": "Gana New York Yankees", "cuota": 1.80, "acierto": True, "Resultado_Real": "New York Yankees"},
            {"Fecha": (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d'), "Deporte": "MLB", "Evento": "Los Angeles Dodgers vs San Francisco Giants", "Apuesta": "OVER 8.5", "cuota": 1.95, "acierto": False, "Resultado_Real": "UNDER"},
            {"Fecha": (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d'), "Deporte": "MLB", "Evento": "Houston Astros vs Texas Rangers", "Apuesta": "Yordan Alvarez HR", "cuota": 3.00, "acierto": True, "Resultado_Real": "Yordan Alvarez HR"},
            {"Fecha": (datetime.now() - timedelta(days=4)).strftime('%Y-%m-%d'), "Deporte": "MLB", "Evento": "Atlanta Braves vs Philadelphia Phillies", "Apuesta": "Gana Atlanta Braves -1.5", "cuota": 2.10, "acierto": False, "Resultado_Real": "Atlanta Braves"},
            {"Fecha": (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'), "Deporte": "NBA", "Evento": "Lakers vs Celtics", "Apuesta": "Gana Lakers", "cuota": 2.00, "acierto": True, "Resultado_Real": "Lakers"},
        ])
        sample_bitacora.to_csv("data/bitacora_maestra.csv", index=False)

    if not os.path.exists("data/resultados_reales_15dias.json"):
        print("Creando resultados reales de ejemplo para la prueba...")
        sample_resultados = [
            {"fecha": (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'), "away": "Boston Red Sox", "home": "New York Yankees", "ganador": "New York Yankees", "total_runs": 7},
            {"fecha": (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d'), "away": "San Francisco Giants", "home": "Los Angeles Dodgers", "ganador": "Los Angeles Dodgers", "total_runs": 6},
            {"fecha": (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d'), "away": "Texas Rangers", "home": "Houston Astros", "ganador": "Houston Astros", "total_runs": 9},
            {"fecha": (datetime.now() - timedelta(days=4)).strftime('%Y-%m-%d'), "away": "Philadelphia Phillies", "home": "Atlanta Braves", "ganador": "Atlanta Braves", "total_runs": 8},
        ]
        with open("data/resultados_reales_15dias.json", "w", encoding="utf-8") as f:
            json.dump(sample_resultados, f, indent=2, ensure_ascii=False)

    run_mlb_real_backtest()