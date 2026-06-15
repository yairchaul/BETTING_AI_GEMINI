import json
from collections import defaultdict

def generar_inteligencia_umpires():
    try:
        with open("resultados_reales_15dias.json", "r", encoding="utf-8") as f:
            partidos = json.load(f)
        
        stats = defaultdict(lambda: {"ganadas": 0, "perdidas": 0, "total_runs": [], "total": 0})

        for p in partidos:
            ump = p.get("umpire", "Desconocido")
            runs = p.get("score_visitante", 0) + p.get("score_local", 0)
            
            # Calcular si el pick del modelo acertó
            aw = p.get("away_wins", 0); al = p.get("away_losses", 0)
            hw = p.get("home_wins", 0); hl = p.get("home_losses", 0)
            away_pct = aw / max(aw + al, 1)
            home_pct = hw / max(hw + hl, 1)
            pick = p["local"] if home_pct > away_pct else p["visitante"]
            ganador = p.get("ganador", "")
            
            if ump and ump != "Desconocido" and ump != "TBD":
                stats[ump]["total"] += 1
                stats[ump]["total_runs"].append(runs)
                if pick == ganador:
                    stats[ump]["ganadas"] += 1
                else:
                    stats[ump]["perdidas"] += 1

        diccionario_final = {}
        for ump, data in stats.items():
            if data["total"] >= 2:  # Mínimo 2 partidos para considerar
                wr = (data["ganadas"] / data["total"]) * 100
                avg_runs = sum(data["total_runs"]) / data["total"]
                tendencia = "OVER" if avg_runs > 9.0 else "UNDER" if avg_runs < 7.5 else "NEUTRAL"
                factor = round(1 + (wr - 50) / 100, 2)

                diccionario_final[ump] = {
                    "tendencia_real": tendencia,
                    "avg_runs_detectado": round(avg_runs, 2),
                    "tu_winrate": f"{wr:.1f}%",
                    "factor_influencia": factor,
                    "total_partidos": data["total"]
                }
                print(f"   ⚖️ {ump}: WR={wr:.1f}%, Avg Runs={avg_runs:.1f}, Tendencia={tendencia}")

        with open("data/inteligencia_umpires.json", "w", encoding="utf-8") as f:
            json.dump(diccionario_final, f, indent=2, ensure_ascii=False)
            
        print(f"\n✅ Inteligencia de {len(diccionario_final)} umpires generada")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    generar_inteligencia_umpires()
