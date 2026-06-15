import json
from datetime import datetime, timedelta
from collections import defaultdict

# Cargar resultados
with open("resultados_reales_15dias.json", "r", encoding="utf-8") as f:
    partidos = json.load(f)

# Agrupar por día
por_dia = defaultdict(lambda: {"total": 0, "over": 0, "under": 0, "home_wins": 0, "runs": []})

for p in partidos:
    fecha = p["fecha"]
    total_runs = p.get("score_visitante", 0) + p.get("score_local", 0)
    ganador = p.get("ganador", "")
    home = p.get("local", "")
    
    por_dia[fecha]["total"] += 1
    por_dia[fecha]["runs"].append(total_runs)
    if total_runs > 8.5:
        por_dia[fecha]["over"] += 1
    else:
        por_dia[fecha]["under"] += 1
    if ganador == home:
        por_dia[fecha]["home_wins"] += 1

# Calcular tendencias
fechas_ordenadas = sorted(por_dia.keys(), reverse=True)
print("📊 TENDENCIAS DETECTADAS:")
print()

# Últimos 3 días para detectar cambio
if len(fechas_ordenadas) >= 3:
    ayer = fechas_ordenadas[0]
    anteayer = fechas_ordenadas[1]
    
    over_hoy = (por_dia[ayer]["over"] / por_dia[ayer]["total"]) * 100
    over_ayer = (por_dia[anteayer]["over"] / por_dia[anteayer]["total"]) * 100
    
    print(f"   Ayer ({ayer}): {over_hoy:.0f}% OVER")
    print(f"   Anteayer ({anteayer}): {over_ayer:.0f}% OVER")
    
    # Detectar cambio de tendencia
    if over_ayer > 65 and over_hoy < 40:
        print("   🚨 ALERTA: Cambio drástico OVER→UNDER detectado")
        print("   💡 Recomendación: Favorecer UNDER hoy")
        factor_ou = -0.8  # Reducir proyección en 0.8 carreras
    elif over_ayer < 35 and over_hoy > 60:
        print("   🚨 ALERTA: Cambio drástico UNDER→OVER detectado")
        print("   💡 Recomendación: Favorecer OVER hoy")
        factor_ou = +0.8  # Aumentar proyección en 0.8 carreras
    elif over_hoy > 60:
        print("   📈 Tendencia OVER (día caliente)")
        factor_ou = +0.5
    elif over_hoy < 40:
        print("   📉 Tendencia UNDER (día frío)")
        factor_ou = -0.5
    else:
        print("   ➡️ Tendencia NEUTRAL")
        factor_ou = 0
    
    print(f"   Factor O/U ajustado: {factor_ou:+.1f} carreras")

# Guardar factor
import os
os.makedirs("data", exist_ok=True)
with open("data/factor_ou_diario.json", "w", encoding="utf-8") as f:
    json.dump({
        "fecha": datetime.now().strftime("%Y-%m-%d"),
        "factor_ou": factor_ou,
        "over_hoy": over_hoy,
        "over_ayer": over_ayer
    }, f, indent=2)

print()
print("✅ Factor guardado en data/factor_ou_diario.json")
