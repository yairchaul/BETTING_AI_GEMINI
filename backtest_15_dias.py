# -*- coding: utf-8 -*-
import requests
import pandas as pd
from datetime import datetime, timedelta
import time

def ejecutar_backtesting_15_dias():
    resultados = []
    hoy = datetime.now()
    
    print(f"📡 Conectando con API MLB para recolección de datos...")
    
    for i in range(1, 16):
        fecha = (hoy - timedelta(days=i)).strftime("%Y-%m-%d")
        print(f"📅 Procesando: {fecha}...", end="\r")
        
        url_sched = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={fecha}"
        try:
            response = requests.get(url_sched).json()
            if "dates" not in response or not response["dates"]: continue
            
            games = response["dates"][0]["games"]
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
                        k_real = p_data["stats"]["pitching"].get("strikeOuts", 0)
                        
                        # Simulación de Línea de Casa (Suelen ponerla cerca de su promedio real)
                        # Para el backtest, usaremos un valor base de 4.5 o 5.5
                        linea_imaginaria = 5.5 if k_real > 4 else 4.5
                        
                        # Predicción NEON (Simulada con K/9 real de la temporada)
                        # Nota: En un entorno real, NEON usaría el K/9 que el jugador tenía EN ESE MOMENTO.
                        s_url = f"https://statsapi.mlb.com/api/v1/people/{p_id}/stats?stats=statsSingleSeason&group=pitching&season=2026"
                        s_res = requests.get(s_url).json()
                        
                        try:
                            k9 = float(s_res["stats"][0]["splits"][0]["stat"]["strikeOutsPer9Inn"])
                            prediccion = round((k9 / 9) * 5.5, 1)
                        except:
                            continue

                        # Lógica de Decisión
                        if prediccion - linea_imaginaria >= 1.2:
                            decision = "OVER"
                        elif linea_imaginaria - prediccion >= 1.2:
                            decision = "UNDER"
                        else:
                            decision = "PASAR"

                        # Verificación de Acierto
                        acierto = False
                        if decision == "OVER" and k_real > linea_imaginaria: acierto = True
                        if decision == "UNDER" and k_real < linea_imaginaria: acierto = True

                        if decision != "PASAR":
                            resultados.append({
                                "Fecha": fecha,
                                "Lanzador": name,
                                "Línea": linea_imaginaria,
                                "Prediccion": prediccion,
                                "Decisión": decision,
                                "Real": k_real,
                                "Resultado": "✅" if acierto else "❌"
                            })
        except: continue
        time.sleep(0.1) # Evitar baneo de API

    df = pd.DataFrame(resultados)
    return df

if __name__ == "__main__":
    df_res = ejecutar_backtesting_15_dias()
    if not df_res.empty:
        total = len(df_res)
        ganados = len(df_res[df_res["Resultado"] == "✅"])
        precision = (ganados / total) * 100
        
        print("\n\n" + "📊 REPORTE DE 15 DÍAS (K-PROPS) ".center(60, "="))
        print(df_res.tail(20).to_string(index=False))
        print("=" * 60)
        print(f"📈 TOTAL APUESTAS SUGERIDAS: {total}")
        print(f"✅ GANADAS: {ganados} | ❌ PERDIDAS: {total - ganados}")
        print(f"🎯 EFECTIVIDAD FINAL: {precision:.2f}%")
        
        # Simulación de Ganancia (Suponiendo momios de -110 / 1.90)
        unidades = (ganados * 0.90) - (total - ganados)
        color = "🟢" if unidades > 0 else "🔴"
        print(f"💰 BALANCE ESTIMADO: {unidades:.2f} Unidades {color}")
    else:
        print("\nNo se pudieron recolectar datos suficientes para el reporte.")
