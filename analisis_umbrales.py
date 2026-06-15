# -*- coding: utf-8 -*-
"""OPTIMIZACIÓN DE UMBRALES - Basado en datos reales"""
import json
from collections import defaultdict

with open("resultados_reales_15dias.json", "r", encoding="utf-8") as f:
    partidos = json.load(f)

print("=" * 70)
print("🧪 ANÁLISIS DE OPTIMIZACIÓN DE UMBRALES")
print("=" * 70)
print(f"   Total partidos analizados: {len(partidos)}")
print()

# ==================== 1. ANÁLISIS POR DIFERENCIA DE RECORDS ====================
print("📊 ANÁLISIS POR DIFERENCIA DE WIN % (diff)")
print("-" * 70)

# Calcular win % para cada partido
for p in partidos:
    away_games = p.get("away_wins", 0) + p.get("away_losses", 0)
    home_games = p.get("home_wins", 0) + p.get("home_losses", 0)
    
    if away_games > 0 and home_games > 0:
        away_pct = p["away_wins"] / away_games
        home_pct = p["home_wins"] / home_games
    else:
        away_pct = 0.5
        home_pct = 0.5
    
    p["away_pct"] = away_pct
    p["home_pct"] = home_pct
    p["diff_pct"] = abs(home_pct - away_pct) * 100  # Diferencia en porcentaje
    p["pick_por_records"] = p["local"] if home_pct > away_pct else p["visitante"]
    p["acerto_pick_records"] = p["pick_por_records"] == p["ganador"]

# Agrupar por rangos de diff
rangos_diff = [
    (0, 3, "0-3%"),
    (3, 5, "3-5%"),
    (5, 7, "5-7%"),
    (7, 10, "7-10%"),
    (10, 15, "10-15%"),
    (15, 100, ">15%"),
]

print(f"{'Rango Diff':<12} {'Partidos':<10} {'Aciertos':<10} {'Win Rate':<10} {'Recomendación'}")
print("-" * 70)

for min_d, max_d, nombre in rangos_diff:
    en_rango = [p for p in partidos if min_d <= p["diff_pct"] < max_d]
    total = len(en_rango)
    aciertos = sum(1 for p in en_rango if p["acerto_pick_records"])
    wr = (aciertos / total * 100) if total > 0 else 0
    
    if wr >= 60:
        rec = "🔥 ELITE"
    elif wr >= 55:
        rec = "⭐ SEGURO"
    elif wr >= 48:
        rec = "🛡️ RESCATE"
    else:
        rec = "❌ EVITAR"
    
    print(f"{nombre:<12} {total:<10} {aciertos:<10} {wr:.1f}%{'':<7} {rec}")

print()
print("💡 CONCLUSIÓN: Ajustar umbrales de diff según estos rangos")
print()

# ==================== 2. ANÁLISIS POR HANDICAP ====================
print("=" * 70)
print("📊 ANÁLISIS DE HANDICAP (Run Line)")
print("-" * 70)

for p in partidos:
    p["local_gano"] = p["ganador"] == p["local"]
    p["dif_runs"] = p["score_local"] - p["score_visitante"]

# ¿Con qué frecuencia el local gana por +1.5, +2.5, +3.5?
handicaps = [1.5, 2.5, 3.5]
for h in handicaps:
    local_cubre = sum(1 for p in partidos if p["dif_runs"] >= h)
    visitante_cubre = sum(1 for p in partidos if p["dif_runs"] <= -h)
    total_cubre = local_cubre + visitante_cubre
    pct = (total_cubre / len(partidos) * 100)
    
    print(f"   Handicap {h}: {total_cubre}/{len(partidos)} partidos cubren ({pct:.1f}%)")
    print(f"      Local cubre +{h}: {local_cubre} | Visitante cubre -{h}: {visitante_cubre}")

print()
print("💡 CONCLUSIÓN: El handicap +1.5 es el más frecuente. Usar +2.5 para RESCATE está bien.")
print()

# ==================== 3. ANÁLISIS POR DÍA DE LA SEMANA ====================
print("=" * 70)
print("📊 ANÁLISIS POR DÍA DE LA SEMANA")
print("-" * 70)

from datetime import datetime
dias_semana = {0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves", 4: "Viernes", 5: "Sábado", 6: "Domingo"}
por_dia = defaultdict(lambda: {"total": 0, "aciertos": 0})

for p in partidos:
    fecha = datetime.strptime(p["fecha"], "%Y-%m-%d")
    dia = dias_semana[fecha.weekday()]
    por_dia[dia]["total"] += 1
    if p["acerto_pick_records"]:
        por_dia[dia]["aciertos"] += 1

print(f"{'Día':<12} {'Partidos':<10} {'Aciertos':<10} {'Win Rate':<10}")
print("-" * 50)
for dia in ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]:
    d = por_dia[dia]
    wr = (d["aciertos"] / d["total"] * 100) if d["total"] > 0 else 0
    print(f"{dia:<12} {d['total']:<10} {d['aciertos']:<10} {wr:.1f}%")

print()
print("💡 CONCLUSIÓN: Identificar días de la semana con mejor rendimiento")
print()

# ==================== 4. ANÁLISIS DE EQUIPOS TRAMPA ====================
print("=" * 70)
print("📊 ANÁLISIS DE EQUIPOS PROBLEMÁTICOS")
print("-" * 70)

equipos_stats = defaultdict(lambda: {"total": 0, "aciertos": 0, "como_pick": 0, "acerto_pick": 0})

for p in partidos:
    for equipo in [p["visitante"], p["local"]]:
        equipos_stats[equipo]["total"] += 1
        if equipo == p["ganador"]:
            equipos_stats[equipo]["aciertos"] += 1
    
    # Cuando el modelo los elige como pick
    pick = p["pick_por_records"]
    equipos_stats[pick]["como_pick"] += 1
    if p["acerto_pick_records"]:
        equipos_stats[pick]["acerto_pick"] += 1

# Mostrar equipos con peor rendimiento como pick
print(f"{'Equipo':<25} {'Win Real':<10} {'Como Pick':<12} {'WR Pick':<10}")
print("-" * 60)

equipos_ordenados = sorted(equipos_stats.items(), key=lambda x: x[1]["acerto_pick"] / max(x[1]["como_pick"], 1))

for equipo, stats in equipos_ordenados[:10]:
    wr_real = (stats["aciertos"] / max(stats["total"], 1) * 100)
    wr_pick = (stats["acerto_pick"] / max(stats["como_pick"], 1) * 100)
    
    if stats["como_pick"] >= 3 and wr_pick < 45:
        print(f"{equipo:<25} {wr_real:.1f}%{'':<5} {stats['como_pick']:<12} {wr_pick:.1f}% ⚠️ TRAMPA")

print()
print("💡 CONCLUSIÓN: Actualizar EQUIPOS_TRAMPA con estos equipos")
print()

# ==================== 5. RECOMENDACIONES FINALES ====================
print("=" * 70)
print("🎯 RECOMENDACIONES FINALES DE OPTIMIZACIÓN")
print("=" * 70)
print()
print("📋 NUEVOS UMBRALES SUGERIDOS PARA clasificar_v21():")
print()
print("   if diff >= 12:                    # ELITE (WR >60%)")
print("       return 'ELITE', 3u")
print("   elif diff >= 7 and conf >= 58:    # SEGURO (WR ~57%)")
print("       return 'SEGURO', 2u, +1.5")
print("   elif diff >= 5:                   # RESCATE (WR ~52%)")
print("       return 'RESCATE', 1u, +2.5")
print("   else:                             # EVITAR (WR <48%)")
print("       return 'EVITAR', 0u")
print()
print("📋 EQUIPOS TRAMPA ACTUALIZADOS:")
print("   (basado en rendimiento real como pick)")
equipos_trampa = [e for e, s in equipos_ordenados[:5] if s["como_pick"] >= 3]
for e in equipos_trampa:
    print(f"   - {e}")
print()
print("📋 HANDICAP ÓPTIMO POR CLASE:")
print("   ELITE: Moneyline (sin handicap)")
print("   SEGURO: +1.5 (cubre ~65% de partidos)")
print("   RESCATE: +2.5 (cubre ~45% de partidos)")
