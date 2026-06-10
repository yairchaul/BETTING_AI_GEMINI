# -*- coding: utf-8 -*-
"""
BACKTEST INTEGRAL SEMANAL - Mayo 2026
Prueba: Heurístico + Groq + Gemini en eventos reales recientes.
"""
import os
import sys
import json

BASE_DIR = r"C:\Users\Yair\Desktop\BETTING_AI"
sys.path.insert(0, BASE_DIR) # Priorizar la raíz para evitar conflictos de paquetes

from motors import analizar_nba, analizar_mlb, analizar_futbol_jerarquico, UFCAnalyzer, motor_over_under, predictor_strikes
from utils.analista_total import AnalistaTotal
from utils.cerebro_gemini_pro import CerebroGeminiPro
from groq_ufc_engine import GroqUFCEngine

def run_backtest():
    print("="*80)
    print("🚀 BETTING_AI - BACKTEST INTEGRAL (MAYO 15-21, 2026)")
    print("="*80)

    # Inicializar IA
    gemini = CerebroGeminiPro()
    groq = GroqUFCEngine()
    analista = AnalistaTotal(gemini_client=gemini, groq_client=groq, selected_model="Votación (Todas las IAs)")

    # --- 1. MLB: Yankees vs Mariners (20 Mayo) ---
    print("\n⚾ [MLB] NY Yankees vs Seattle Mariners")
    mlb_match = {
        'local': 'New York Yankees', 'visitante': 'Seattle Mariners',
        'pitchers': {'local': {'nombre': 'Carlos Rodón', 'era': 3.49}, 'visitante': {'nombre': 'Bryan Woo', 'era': 1.93}},
        'odds': {'over_under': 8.0, 'moneyline': {'local': '-150', 'visitante': '+130'}},
        'venue': 'Yankee Stadium', 'clima': {'temp': 68, 'wind_speed': 8, 'wind_dir': 'Out'}
    }
    mlb_h = analizar_mlb(mlb_match)
    k_l = predictor_strikes.predecir_strikes('Carlos Rodón', 'Seattle Mariners')
    mlb_ou = motor_over_under.calcular_total(mlb_match)
    mlb_final = analista.analizar_partido_completo(mlb_match, mlb_h, [], mlb_match['clima'], strike_analysis=k_l, ou_analysis=mlb_ou)
    print(f"   Heurístico: {mlb_h['recomendacion']} | K-Proy: {k_l['k_proyectados']} | O/U: {mlb_ou['recomendacion']}")
    print(f"   IA/Consenso: {mlb_final}")

    # --- 2. NBA: Celtics vs Pacers (21 Mayo) ---
    print("\n🏀 [NBA] Boston Celtics vs Indiana Pacers")
    nba_match = {'local': 'Boston Celtics', 'visitante': 'Indiana Pacers', 'record_local': '64-18', 'record_visit': '47-35', 'odds': {'over_under': 221.5, 'spread': -10.5}}
    nba_h = analizar_nba(nba_match)
    nba_final = analista.analizar_partido_completo(nba_match, nba_h, [], None)
    print(f"   Heurístico: {nba_h['recomendacion']} ({nba_h['confianza']}%)")
    print(f"   IA/Consenso: {nba_final}")

    # --- 3. FUTBOL: Manchester City vs West Ham (Final de Liga) ---
    print("\n⚽ [FUTBOL] Manchester City vs West Ham")
    fut_h = analizar_futbol_jerarquico('Manchester City', 'West Ham United')
    fut_final = analista.analizar_partido_completo({'home': 'Man City', 'away': 'West Ham'}, fut_h, [], None, jerarquia_futbol=fut_h)
    print(f"   Heurístico: {fut_h['pick']} (Regla #{fut_h['regla']})")
    print(f"   IA/Consenso: {fut_final}")

    # --- 4. UFC: Edson Barboza vs Lerone Murphy (Mayo 18) ---
    print("\n🥊 [UFC] Edson Barboza vs Lerone Murphy")
    ufc_analyzer = UFCAnalyzer()
    p1 = {'nombre': 'Edson Barboza', 'ko_rate': 0.65, 'wins': 24, 'losses': 11, 'alcance': 190, 'altura': 180}
    p2 = {'nombre': 'Lerone Murphy', 'ko_rate': 0.50, 'wins': 13, 'losses': 0, 'alcance': 185, 'altura': 175}
    ufc_h = ufc_analyzer.analizar_combate(p1, p2)
    ufc_final = analista.analizar_partido_completo({'peleador1': p1, 'peleador2': p2}, ufc_h, [], None)
    print(f"   Heurístico: {ufc_h['recomendacion']} | Método: {ufc_h['metodo']}")
    print(f"   IA/Consenso: {ufc_final}")

    print("\n" + "="*80)
    print("✅ TEST QUIRÚRGICO COMPLETADO")
    print("="*80)

if __name__ == "__main__":
    run_backtest()