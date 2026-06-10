import json

print("=" * 70)
print("🎯 MODO PARLAY - SUGERENCIA DE COMBINACIONES")
print("=" * 70)
print()

# Simular picks del día (se llenaría con datos reales)
picks_del_dia = [
    {"jugador": "Aaron Judge", "equipo": "NYY", "prob": 60, "puntuacion": 6, "stake": 2},
    {"jugador": "Shohei Ohtani", "equipo": "LAD", "prob": 53, "puntuacion": 8, "stake": 3},
    {"jugador": "Mike Trout", "equipo": "LAA", "prob": 47, "puntuacion": 7, "stake": 3},
    {"jugador": "Ronald Acuna Jr", "equipo": "ATL", "prob": 40, "puntuacion": 5, "stake": 2},
    {"jugador": "Matt Olson", "equipo": "ATL", "prob": 47, "puntuacion": 6, "stake": 2},
]

# Ordenar por puntuación
picks_del_dia.sort(key=lambda x: x["puntuacion"], reverse=True)

print("📊 TOP PICKS HR DEL DÍA:")
print("-" * 70)
for i, p in enumerate(picks_del_dia, 1):
    emoji = "👑" if i == 1 else "🔥" if p["puntuacion"] >= 6 else "🟡"
    print(f"{i}. {emoji} {p['jugador']} ({p['equipo']}) - {p['puntuacion']}/10 pts - {p['prob']}% HR")

print()
print("🎯 SUGERENCIA DE PARLAY (2 PICKS):")
print("-" * 70)

if len(picks_del_dia) >= 2:
    p1 = picks_del_dia[0]
    p2 = picks_del_dia[1]
    
    prob_combinada = (p1["prob"] / 100) * (p2["prob"] / 100) * 100
    cuota_estimada = round((100 / p1["prob"]) * (100 / p2["prob"]), 1)
    
    print(f"   ⭐ {p1['jugador']} ({p1['equipo']}) HR + {p2['jugador']} ({p2['equipo']}) HR")
    print(f"   📊 Probabilidad combinada: {prob_combinada:.1f}%")
    print(f"   💰 Cuota estimada: +{cuota_estimada}")
    print(f"   💵 Stake sugerido: 1u")

if len(picks_del_dia) >= 3:
    p3 = picks_del_dia[2]
    prob_triple = (p1["prob"] / 100) * (p2["prob"] / 100) * (p3["prob"] / 100) * 100
    cuota_triple = round((100 / p1["prob"]) * (100 / p2["prob"]) * (100 / p3["prob"]), 1)
    
    print()
    print(f"   🔥 PARLAY AGRESIVO (3 picks): {p1['jugador']} + {p2['jugador']} + {p3['jugador']}")
    print(f"   📊 Probabilidad: {prob_triple:.1f}%")
    print(f"   💰 Cuota estimada: +{cuota_triple}")
    print(f"   💵 Stake sugerido: 0.5u (alto riesgo)")

print()
print("💡 El parlay combina los 2 mejores picks del día.")
print("   La cuota se multiplica, pero la probabilidad baja.")
print("   Usar con stake pequeño (1u o 0.5u).")
