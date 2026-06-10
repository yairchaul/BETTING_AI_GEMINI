# -*- coding: utf-8 -*-
"""
BACKTEST RÁPIDO UFC - Valida lógica de método de victoria
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motors.ufc_analyzer import UFCAnalyzer

def run_backtest():
    analyzer = UFCAnalyzer()
    
    # Escenario 1: Perdedor con barbilla de cristal (ko_losses >= 2)
    p1 = {'nombre': 'Fighter Fuerte', 'ko_rate': 0.40, 'wins': 10}
    p2 = {'nombre': 'Fighter Frágil', 'ko_losses': 2, 'wins': 5}
    res1 = analyzer.analizar_combate(p1, p2)
    
    # Escenario 2: Especialista en sumisiones
    p3 = {'nombre': 'Grappler', 'sub_rate': 0.45, 'wins': 15}
    p4 = {'nombre': 'Striker', 'sub_losses': 1, 'wins': 20}
    res2 = analyzer.analizar_combate(p3, p4)

    # Escenario 3: Pelea técnica a decisión
    p5 = {'nombre': 'Técnico 1', 'ko_rate': 0.10, 'sub_rate': 0.10, 'wins': 20}
    p6 = {'nombre': 'Técnico 2', 'ko_losses': 0, 'sub_losses': 0, 'wins': 20}
    res3 = analyzer.analizar_combate(p5, p6)

    print("="*60)
    print("🧪 BACKTESTING DE LÓGICA DE MÉTODO DE VICTORIA")
    print("="*60)
    print(f"TEST 1 (Vulnerabilidad KO): {res1['ganador']} gana por {res1['metodo']}")
    print(f"      Esperado: KO/TKO por ko_losses del oponente.")
    
    print(f"\nTEST 2 (Especialista SUB): {res2['ganador']} gana por {res2['metodo']}")
    print(f"      Esperado: Sumisión por alto sub_rate.")
    
    print(f"\nTEST 3 (Duelo Técnico): {res3['ganador']} gana por {res3['metodo']}")
    print(f"      Esperado: Decisión por falta de poder/vulnerabilidad.")
    
    # Verificación de lógica
    assert "KO/TKO" in res1['metodo']
    assert "Sumisión" in res2['metodo']
    assert "Decisión" in res3['metodo']
    
    print("\n✅ TODOS LOS ESCENARIOS VALIDADOS CORRECTAMENTE.")
    print("="*60)

if __name__ == "__main__":
    run_backtest()