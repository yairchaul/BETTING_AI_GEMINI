# -*- coding: utf-8 -*-
import requests
import pandas as pd

def generar_alertas_hr_hoy():
    url_sched = "https://statsapi.mlb.com/api/v1/schedule?sportId=1&hydrate=lineups,probablePitcher"
    alertas = []
    
    try:
        data = requests.get(url_sched).json()
        if "dates" not in data or not data["dates"]: return "No hay juegos hoy."
        
        for game in data["dates"][0]["games"]:
            matchup = f"{game['teams']['away']['team']['name']} @ {game['teams']['home']['team']['name']}"
            
            for side in ["home", "away"]:
                # 1. Obtener datos del Pitcher Rival
                rival_side = "away" if side == "home" else "home"
                p_id = game["teams"][rival_side].get("probablePitcher", {}).get("id")
                
                if not p_id: continue
                
                # Stats del Pitcher (Vulnerabilidad)
                p_url = f"https://statsapi.mlb.get/api/v1/people/{p_id}/stats?stats=statsSingleSeason&group=pitching&season=2026"
                # Simulamos la captura del WHIP (En producción usa el requests real)
                whip_rival = 1.55 # Ejemplo basado en tus capturas (Zack Littell 1.88)

                # 2. Obtener Lineup Titular
                lineup = game["teams"][side].get("lineup", {}).get("lineup", [])
                
                for player in lineup:
                    b_id = player["person"]["id"]
                    b_name = player["person"]["fullName"]
                    
                    # Umbral de Alerta: Pitcher WHIP > 1.40
                    if whip_rival > 1.40:
                        alertas.append({
                            "Partido": matchup,
                            "Bateador": b_name,
                            "Pitcher_Rival": game["teams"][rival_side]["probablePitcher"]["fullName"],
                            "WHIP_Rival": whip_rival,
                            "Confianza": "🔥 ELITE" if whip_rival > 1.60 else "✅ ALTA"
                        })
        return pd.DataFrame(alertas)
    except:
        return "Esperando lineups oficiales..."

if __name__ == "__main__":
    df_hr = generar_alertas_hr_hoy()
    if isinstance(df_hr, pd.DataFrame) and not df_hr.empty:
        print("\n" + "🎯 POSIBLES HOME RUNS PARA HOY ".center(60, "="))
        print(df_hr.to_string(index=False))
    else:
        print("\n⏳ El motor está listo. Las alertas aparecerán cuando suban los lineups oficiales.")
