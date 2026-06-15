# -*- coding: utf-8 -*-
"""OBTENER RESULTADOS REALES MLB - ÚLTIMOS 5 DÍAS"""
import requests
import json
from datetime import datetime, timedelta

def obtener_resultados_reales(dias=5):
    """Obtiene resultados reales de MLB de los últimos N días"""
    resultados = []
    
    for i in range(1, dias + 1):
        fecha = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={fecha}"
        
        try:
            response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                for date in data.get("dates", []):
                    for game in date.get("games", []):
                        away = game.get("teams", {}).get("away", {}).get("team", {}).get("name", "")
                        home = game.get("teams", {}).get("home", {}).get("team", {}).get("name", "")
                        
                        away_score = game.get("teams", {}).get("away", {}).get("score", 0)
                        home_score = game.get("teams", {}).get("home", {}).get("score", 0)
                        
                        status = game.get("status", {}).get("detailedState", "")
                        
                        if status == "Final":
                            ganador = home if home_score > away_score else away
                            perdedor = away if home_score > away_score else home
                            diff = abs(home_score - away_score)
                            total_runs = home_score + away_score
                            
                            # Obtener odds si están disponibles
                            odds = game.get("odds", [{}])[0] if game.get("odds") else {}
                            over_under = odds.get("overUnder", "N/A")
                            
                            # Pitchers probables
                            prob_pitchers = game.get("probablePitchers", {})
                            away_pitcher = prob_pitchers.get("away", {}).get("fullName", "TBD")
                            home_pitcher = prob_pitchers.get("home", {}).get("fullName", "TBD")
                            
                            resultados.append({
                                "fecha": fecha,
                                "visitante": away,
                                "local": home,
                                "score_visitante": away_score,
                                "score_local": home_score,
                                "ganador": ganador,
                                "perdedor": perdedor,
                                "diferencia": diff,
                                "total_runs": total_runs,
                                "over_under_line": over_under,
                                "pitcher_visitante": away_pitcher,
                                "pitcher_local": home_pitcher,
                                "status": status
                            })
        except Exception as e:
            print(f"   ⚠️ Error en {fecha}: {str(e)[:50]}")
    
    return resultados

if __name__ == "__main__":
    print("📡 Obteniendo resultados de los últimos 5 días...")
    resultados = obtener_resultados_reales(5)
    
    with open("resultados_reales_5dias.json", "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)
    
    print(f"✅ {len(resultados)} partidos finalizados encontrados")
    
    # Mostrar resumen
    for r in resultados[:3]:
        print(f"   {r['fecha']}: {r['visitante']} {r['score_visitante']} @ {r['local']} {r['score_local']} → {r['ganador']}")
