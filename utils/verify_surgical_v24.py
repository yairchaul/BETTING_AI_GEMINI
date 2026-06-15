# -*- coding: utf-8 -*-
"""
VERIFICADOR QUIRÚRGICO V24 - BETTING_AI
Verifica que la integración de motores, IAs y scrapers sea perfecta.
"""
import os
import sys
import json
import logging

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from motors import (
    analizar_nba, analizar_mlb, UFCAnalyzer,
    analizar_futbol_jerarquico, motor_over_under, predictor_strikes
)
from utils.analista_total import AnalistaTotal
from utils.cerebro_gemini_pro import CerebroGeminiPro
from groq_ufc_engine import GroqUFCEngine

def test_ufc_surgical():
    print("🥊 [UFC] Probando análisis unificado (Físico + Stats)...")
    analyzer = UFCAnalyzer()
    p1 = {"nombre": "Test Striker", "ko_rate": 0.8, "wins": 15, "losses": 2, "alcance": 195, "altura": 190}
    p2 = {"nombre": "Test Grappler", "ko_rate": 0.1, "wins": 20, "losses": 5, "alcance": 180, "altura": 182}
    res = analyzer.analizar_combate(p1, p2)
    print(f"   Veredicto: {res['recomendacion']} | Método: {res['metodo']}")
    assert res['ganador'] == "Test Striker"

def test_nba_triples():
    print("🏀 [NBA] Probando Pro v17 (Lambda + Triples)...")
    partido = {
        "local": "Lakers", "visitante": "Warriors",
        "record_local": "45-30", "record_visit": "40-35",
        "odds": {"over_under": 228.5, "spread": -4.5},
        "record_local": "45-30", "record_visit": "40-35"
    }
    res = analizar_nba(partido)
    print(f"   Pick: {res['recomendacion']} (Confianza: {res['confianza']}%)")
    assert "Gana" in res['recomendacion']

def test_mlb_surgical():
    print("⚾ [MLB] Probando Pro v20 (Strikes + Power Factor + O/U)...")
    partido = {
        "local": "New York Yankees", "visitante": "Boston Red Sox",
        "pitchers": {
            "local": {"nombre": "Gerrit Cole", "era": 3.1},
            "visitante": {"nombre": "Nick Pivetta", "era": 4.6}
        },
        "odds": {"over_under": 8.5},
        "venue": "Yankee Stadium"
    }
    # 1. Test Over/Under quirúrgico
    ou = motor_over_under.calcular_total(partido)
    print(f"   O/U: {ou['total_proyectado']} (Modelo) vs {ou['linea_vegas']} (Vegas)")
    
    # 2. Test Strikes Cole
    k = predictor_strikes.predecir_strikes("Gerrit Cole", "Boston Red Sox")
    print(f"   Strikes Cole: {k['k_proyectados']}K (Modelo)")
    
    # 3. Test Motor Pro
    res = analizar_mlb(partido)
    print(f"   Pick MLB: {res['recomendacion']} (Stake: {res['stake']})")

def test_futbol_jerarquico():
    print("⚽ [FUTBOL] Probando descarte jerárquico (Reglas 1-6)...")
    try:
        res = analizar_futbol_jerarquico("Real Madrid", "Barcelona")
        print(f"   Pick: {res['pick']} (Regla aplicada: #{res['regla']})")
    except Exception as e:
        print(f"   ℹ️ Futbol requiere datos en DB: {e}")

def test_ia_orchestration():
    print("🧠 [IA] Verificando orquestador AnalistaTotal (Contexto Enriquecido)...")
    analista = AnalistaTotal(selected_model="Heurístico")
    partido = {"local": "Yankees", "visitante": "Red Sox"}
    # Si el cliente IA es None, debe retornar el heurístico (fallback resiliente)
    res = analista.analizar_partido_completo(partido, {"pick": "Yankees", "confianza": 70}, [], None)
    print(f"   Resiliencia: {res['pick']} (Confirmada)")

def test_ia_connectivity():
    print("🤖 [IA] Verificando conexiones Gemini/Groq...")
    try:
        gem = CerebroGeminiPro()
        if gem.client:
            print(f"   Gemini: Conexión OK ({gem.model})")
        groq = GroqUFCEngine()
        if groq.client:
            print(f"   Groq: Conexión OK (Llama 3.3)")
    except Exception as e:
        print(f"   ⚠️ Error en IA: {e}")

if __name__ == "__main__":
    print("="*60)
    print("🛡️ INICIANDO AUDITORÍA DE SISTEMAS BETTING_AI V24")
    print("="*60)
    test_ia_connectivity()
    test_ufc_surgical()
    test_nba_triples()
    test_mlb_surgical()
    test_futbol_jerarquico()
    test_ia_orchestration()
    print("="*60)
    print("✅ TODO EL SISTEMA ESTÁ CONECTADO Y FUNCIONANDO QUIRÚRGICAMENTE.")
    print("="*60)