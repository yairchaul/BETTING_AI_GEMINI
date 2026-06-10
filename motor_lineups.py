# -*- coding: utf-8 -*-
import requests

def test_motor_lineups():
    print("\n" + "="*50)
    print("📋 MOTOR DE LINEUPS REALES (STARTING LINEUPS)")
    print("="*50)
    
    url = "https://statsapi.mlb.com/api/v1/schedule?sportId=1&hydrate=lineups"
    try:
        data = requests.get(url).json()
        if "dates" not in data or not data["dates"]: return

        for game in data["dates"][0]["games"]:
            home = game["teams"]["home"]["team"]["name"]
            away = game["teams"]["away"]["team"]["name"]
            
            print(f"👉 Partido: {away} @ {home}")
            
            # Verificamos si ya hay alineación confirmada
            lineup_home = game["teams"]["home"].get("lineup", {}).get("lineup", [])
            if not lineup_home:
                print("   ⚠️ Alineación: Aún no confirmada (Esperando reporte manager)")
            else:
                print(f"   ✅ Alineación Confirmada! ({len(lineup_home)} jugadores)")
            print("-" * 30)

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_motor_lineups()
