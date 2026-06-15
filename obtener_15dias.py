# import requests, json
from datetime import datetime, timedelta

resultados = []
for i in range(1, 16):
    fecha = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={fecha}"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if r.status_code == 200:
            data = r.json()
            for date in data.get("dates", []):
                for game in date.get("games", []):
                    if game.get("status", {}).get("detailedState") == "Final":
                        away = game["teams"]["away"]["team"]["name"]
                        home = game["teams"]["home"]["team"]["name"]
                        away_score = game["teams"]["away"].get("score", 0)
                        home_score = game["teams"]["home"].get("score", 0)
                        ganador = home if home_score > away_score else away
                        
                        away_rec = game["teams"]["away"].get("leagueRecord", {})
                        home_rec = game["teams"]["home"].get("leagueRecord", {})
                        
                        resultados.append({
                            "fecha": fecha,
                            "visitante": away, "local": home,
                            "score_visitante": away_score, "score_local": home_score,
                            "ganador": ganador,
                            "away_wins": away_rec.get("wins", 0), "away_losses": away_rec.get("losses", 0),
                            "home_wins": home_rec.get("wins", 0), "home_losses": home_rec.get("losses", 0),
                        })
    except: pass
    print(f"   {fecha}: {len([r for r in resultados if r['fecha']==fecha])} partidos")

with open("resultados_reales_15dias.json", "w", encoding="utf-8") as f:
    json.dump(resultados, f, indent=2, ensure_ascii=False)
print(f"\n✅ {len(resultados)} partidos guardados")
