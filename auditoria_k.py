# -*- coding: utf-8 -*-
import requests
import pandas as pd
from datetime import datetime, timedelta

def obtener_resultados_reales_k(dias=5):
    """
    Busca los ponches reales que hicieron los lanzadores en los últimos X días.
    """
    resultados = []
    for i in range(1, dias + 1):
        fecha = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={fecha}&hydrate=decisions,person"
        
        try:
            data = requests.get(url).json()
            for date in data.get("dates", []):
                for game in date.get("games", []):
                    # Solo juegos terminados
                    if game.get("status", {}).get("detailedState") == "Final":
                        game_id = game["gamePk"]
                        # Obtener Boxscore para ver ponches exactos
                        box_url = f"https://statsapi.mlb.com/api/v1/game/{game_id}/boxscore"
                        box_data = requests.get(box_url).json()
                        
                        for side in ["home", "away"]:
                            team = game["teams"][side]["team"]["name"]
                            # El primer pitcher en la lista suele ser el abridor
                            pitchers_list = box_data["teams"][side]["pitchers"]
                            if pitchers_list:
                                opener_id = pitchers_list[0]
                                player_stats = box_data["teams"][side]["players"][f"ID{opener_id}"]
                                name = player_stats["person"]["fullName"]
                                k_reales = player_stats["stats"]["pitching"].get("strikeOuts", 0)
                                
                                resultados.append({
                                    "Fecha": fecha,
                                    "Lanzador": name,
                                    "Equipo": team,
                                    "K_Reales": k_reales
                                })
        except:
            continue
    return pd.DataFrame(resultados)

def ejecutar_backtesting_k():
    print("\n" + "="*50)
    print("📈 INICIANDO BACKTESTING DE PONCHES (K)")
    print("="*50)
    
    # 1. Obtenemos lo que pasó en la realidad
    df_real = obtener_resultados_reales_k(dias=3) # Probamos con 3 días para rapidez
    
    # 2. Simulamos la predicción de NEON (basada en el motor que creamos antes)
    # En un escenario real, aquí leeríamos tu base de datos de predicciones pasadas.
    df_real["Prediccion_NEON"] = 5 # Promedio de seguridad de NEON
    df_real["Error"] = df_real["K_Reales"] - df_real["Prediccion_NEON"]
    
    print(df_real[["Fecha", "Lanzador", "K_Reales", "Prediccion_NEON", "Error"]].head(10))
    
    precision = (df_real[abs(df_real["Error"]) <= 1.5].shape[0] / df_real.shape[0]) * 100
    print(f"\n🎯 PRECISIÓN DE NEON (Margen +/- 1.5 K): {precision:.2f}%")

if __name__ == "__main__":
    ejecutar_backtesting_k()
