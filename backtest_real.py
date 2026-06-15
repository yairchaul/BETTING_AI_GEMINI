# -*- coding: utf-8 -*-
import requests
import pandas as pd
from datetime import datetime, timedelta

def obtener_backtesting_dinamico(dias=2):
    resultados = []
    print(f"⏳ Analizando los últimos {dias} días de MLB...")
    
    for i in range(1, dias + 1):
        fecha = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        url_sched = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={fecha}"
        
        try:
            games = requests.get(url_sched).json().get("dates", [])[0].get("games", [])
            for game in games:
                if game.get("status", {}).get("detailedState") == "Final":
                    g_id = game["gamePk"]
                    box = requests.get(f"https://statsapi.mlb.com/api/v1/game/{g_id}/boxscore").json()
                    
                    for side in ["home", "away"]:
                        pitchers = box["teams"][side]["pitchers"]
                        if not pitchers: continue
                        
                        p_id = pitchers[0]
                        p_data = box["teams"][side]["players"][f"ID{p_id}"]
                        name = p_data["person"]["fullName"]
                        k_reales = p_data["stats"]["pitching"].get("strikeOuts", 0)
                        ip_real = float(p_data["stats"]["pitching"].get("inningsPitched", 0))
                        
                        # --- PREDICCIÓN CIENTÍFICA ---
                        # Buscamos su K/9 antes de ese juego (usamos stats de temporada)
                        s_url = f"https://statsapi.mlb.com/api/v1/people/{p_id}/stats?stats=statsSingleSeason&group=pitching&season=2026"
                        s_res = requests.get(s_url).json()
                        
                        try:
                            k9_previo = float(s_res["stats"][0]["splits"][0]["stat"]["strikeOutsPer9Inn"])
                            # Predicción: (K9 / 9) * 5.5 innings promedio
                            prediccion = round((k9_previo / 9) * 5.5, 1)
                        except:
                            prediccion = 4.5 # Default para novatos
                        
                        resultados.append({
                            "Fecha": fecha,
                            "Lanzador": name,
                            "K_Real": k_reales,
                            "Prediccion_K": prediccion,
                            "Diferencia": round(k_reales - prediccion, 1)
                        })
        except: continue

    df = pd.DataFrame(resultados)
    return df

if __name__ == "__main__":
    df_final = obtener_backtesting_dinamico(2)
    if not df_final.empty:
        # Consideramos acierto si el error es menor a 1.5 ponches
        aciertos = df_final[abs(df_final["Diferencia"]) <= 1.5].shape[0]
        precision = (aciertos / len(df_final)) * 100
        
        print("\n" + " COMPARATIVA DE PRECISIÓN ".center(50, "="))
        print(df_final.sort_values(by="Diferencia").to_string(index=False))
        print("="*50)
        print(f"🎯 NUEVA PRECISIÓN DINÁMICA: {precision:.2f}%")
        print(f"📊 Total analizados: {len(df_final)} lanzadores")
    else:
        print("No se encontraron datos suficientes.")
