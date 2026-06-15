# -*- coding: utf-8 -*-
"""ACTUALIZADOR DIARIO - Ejecutar cada día para mantener reglas frescas"""
import json
import os
from datetime import datetime

print("=" * 60)
print("🔄 ACTUALIZADOR DIARIO DE REGLAS")
print("=" * 60)

# 1. Actualizar backtesting
print("\n📊 [1/3] Actualizando backtesting...")
from backtesting_auto_aprendizaje import BacktestingAutoAprendizaje
bt = BacktestingAutoAprendizaje()
reglas = bt.analizar_y_actualizar()

# 2. Actualizar tendencias generales
print("\n📊 [2/3] Actualizando tendencias generales...")
try:
    from actualizar_tendencias import actualizar_tendencias_hoy
    actualizar_tendencias_hoy()
except:
    print("   ⚠️ actualizar_tendencias.py no encontrado")

# 3. Actualizar tendencias Over/Under
print("\n📊 [3/3] Actualizando tendencias Over/Under...")
try:
    from actualizar_tendencias_ou import actualizar_tendencias_ou
except:
    print("   ⚠️ actualizar_tendencias_ou.py no encontrado")

# 4. Mostrar resumen
print("\n" + "=" * 60)
print("✅ REGLAS ACTUALIZADAS:")
print("=" * 60)

reglas_activas = {k: v for k, v in reglas.items() if v and k != "ultima_actualizacion"}
for k, v in reglas_activas.items():
    print(f"   📋 {k}: {v}")

print(f"\n   Última actualización: {reglas.get('ultima_actualizacion', 'N/A')}")
print(f"   Partidos analizados: {reglas.get('total_partidos_analizados', 0)}")
print()
print("🚀 streamlit run main_vision_completo.py")
