# -*- coding: utf-8 -*-
"""ANÁLISIS DE TENDENCIAS DE HOME RUNS - 15 días"""
import json
from collections import defaultdict
from datetime import datetime

# Cargar datos de HR
try:
    with open("hr_datasets_completos.json", "r", encoding="utf-8") as f:
        hr_data = json.load(f)
    bateadores = hr_data.get("bateadores", {})
    pitchers = hr_data.get("pitchers", {})
    print(f"✅ {len(bateadores)} bateadores cargados")
except:
    bateadores = {}
    pitchers = {}
    print("⚠️ No se encontró hr_datasets_completos.json")

# Cargar resultados reales para cruzar
try:
    with open("resultados_reales_15dias.json", "r", encoding="utf-8") as f:
        partidos = json.load(f)
    print(f"✅ {len(partidos)} partidos cargados")
except:
    partidos = []
    print("⚠️ No se encontraron resultados")

print()
print("=" * 70)
print("💣 ANÁLISIS DE TENDENCIAS DE HOME RUNS")
print("=" * 70)
print()

# ==================== 1. TOP BATEADORES HR ====================
print("📊 1. TOP 10 BATEADORES CON MÁS HR")
print("-" * 70)
print(f"{'#':<4} {'Bateador':<25} {'Equipo':<6} {'HR':<6} {'HR/Juego':<10} {'Prob HR':<10}")
print("-" * 70)

top_bateadores = sorted(bateadores.items(), key=lambda x: x[1].get("hr", 0), reverse=True)[:10]

for i, (nombre, stats) in enumerate(top_bateadores, 1):
    hr = stats.get("hr", 0)
    hr_juego = stats.get("hr_por_juego", 0)
    equipo = stats.get("equipo", "N/A")
    prob = min(85, hr_juego * 100) if hr_juego > 0 else 5
    emoji = "🔥🔥🔥" if hr >= 8 else "🔥🔥" if hr >= 5 else "🔥" if hr >= 3 else "💣"
    print(f"{i:<4} {emoji} {nombre:<22} {equipo:<6} {hr:<6} {hr_juego:<10.2f} {prob:.1f}%")

print()

# ==================== 2. EQUIPOS CON MÁS HR ====================
print("📊 2. EQUIPOS QUE MÁS BATEAN HR")
print("-" * 70)

hr_por_equipo = defaultdict(lambda: {"total_hr": 0, "bateadores": 0, "top_bateador": "", "top_hr": 0})

for nombre, stats in bateadores.items():
    equipo = stats.get("equipo", "UNK")
    hr = stats.get("hr", 0)
    hr_por_equipo[equipo]["total_hr"] += hr
    hr_por_equipo[equipo]["bateadores"] += 1
    if hr > hr_por_equipo[equipo]["top_hr"]:
        hr_por_equipo[equipo]["top_hr"] = hr
        hr_por_equipo[equipo]["top_bateador"] = nombre

equipos_ordenados = sorted(hr_por_equipo.items(), key=lambda x: x[1]["total_hr"], reverse=True)

print(f"{'Equipo':<8} {'Total HR':<10} {'Bateadores':<12} {'Top Bateador':<22} {'HR':<5}")
print("-" * 70)
for equipo, stats in equipos_ordenados[:10]:
    print(f"{equipo:<8} {stats['total_hr']:<10} {stats['bateadores']:<12} {stats['top_bateador']:<22} {stats['top_hr']:<5}")

print()

# ==================== 3. PITCHERS QUE MÁS PERMITEN HR ====================
print("📊 3. PITCHERS MÁS VULNERABLES A HR")
print("-" * 70)

pitchers_ordenados = sorted(pitchers.items(), key=lambda x: x[1].get("hr_por_juego", 0), reverse=True)

print(f"{'Pitcher':<25} {'Equipo':<6} {'HR/9':<8} {'Riesgo'}")
print("-" * 55)
for nombre, stats in pitchers_ordenados[:8]:
    hr9 = stats.get("hr_por_juego", 1.0)
    equipo = stats.get("equipo", "N/A")
    riesgo = "🔴 ALTO" if hr9 > 1.5 else "🟠 MEDIO" if hr9 > 1.0 else "🟢 BAJO"
    print(f"{nombre:<25} {equipo:<6} {hr9:<8.2f} {riesgo}")

print()

# ==================== 4. MOMENTOS DE HR (POR DÍA) ====================
print("📊 4. ¿CUÁNDO HAY MÁS HOME RUNS? (POR DÍA)")
print("-" * 70)

# Simular HR por día basado en tendencias
hr_por_dia = defaultdict(lambda: {"juegos": 0, "hr_estimados": 0})
dias_nombre = {0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves", 4: "Viernes", 5: "Sábado", 6: "Domingo"}

for p in partidos:
    fecha = datetime.strptime(p["fecha"], "%Y-%m-%d")
    dia = fecha.weekday()
    hr_por_dia[dia]["juegos"] += 1
    # Estimar HR por partido (promedio MLB ~1.2 HR/equipo/partido)
    hr_por_dia[dia]["hr_estimados"] += 2.4

print(f"{'Día':<12} {'Partidos':<10} {'HR Estimados':<15} {'HR/Partido':<12}")
print("-" * 50)
for dia in range(7):
    d = hr_por_dia[dia]
    if d["juegos"] > 0:
        hr_por_partido = d["hr_estimados"] / d["juegos"]
        emoji = "🔥" if hr_por_partido > 2.5 else "📈" if hr_por_partido > 2.2 else "➡️"
        print(f"{emoji} {dias_nombre[dia]:<9} {d['juegos']:<10} {d['hr_estimados']:<15.0f} {hr_por_partido:.1f}")

print()

# ==================== 5. RECOMENDACIONES ====================
print("=" * 70)
print("🎯 RECOMENDACIONES PARA APOSTAR HR")
print("=" * 70)
print()
print("💡 CUÁNDO APOSTAR HOME RUNS:")
print("   1. Cuando el pitcher rival tiene HR/9 > 1.5 (muy vulnerable)")
print("   2. Cuando el bateador tiene >5 HR en 15 días")
print("   3. En estadios con factor HR > 1.15 (Coors, Great American)")
print("   4. Con viento saliendo a >10mph")
print("   5. Con umpires de zona estrecha (favorecen contacto)")
print()
print("⚠️ CUÁNDO EVITAR HOME RUNS:")
print("   1. Pitcher elite (HR/9 < 0.6: Cole, deGrom, Burnes)")
print("   2. Estadios grandes (Petco, Oracle, Target Field)")
print("   3. Temperatura <50°F (bola no viaja)")
print("   4. Viento en contra >10mph")
