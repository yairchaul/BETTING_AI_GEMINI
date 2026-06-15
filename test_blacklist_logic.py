# -*- coding: utf-8 -*-
import unittest
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from motors.motor_decision_inteligente import MotorDecisionInteligente

class TestBlacklist(unittest.TestCase):
    def setUp(self):
        self.motor = MotorDecisionInteligente()

    def test_penalty_logic(self):
        # Simular equipo con fallos en el log
        equipo_vulnerable = "New York Yankees"
        partido = {"local": equipo_vulnerable, "visitante": "Boston Red Sox", "odds": {"over_under": 8.5}}
        heuristica = {"pick": equipo_vulnerable, "confianza": 85, "diff": 15}
        
        decision = self.motor.decidir_mejor_apuesta(partido, heuristica, [])
        print(f"Probando penalización para {equipo_vulnerable}...")
        print(f"Resultado: Confianza final {decision['confianza']}% | Razón: {decision['razon']}")
        self.assertTrue(decision['confianza'] < 85 or "fallos previos" in decision['razon'])

if __name__ == "__main__":
    unittest.main()
