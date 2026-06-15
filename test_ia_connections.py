# -*- coding: utf-8 -*-
import unittest
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cerebro_gemini_pro import CerebroGeminiPro
from groq_ufc_engine import GroqUFCEngine

class TestIA(unittest.TestCase):
    def test_gemini_connection(self):
        print("\n🧪 Probando conexión con Gemini...")
        cerebro = CerebroGeminiPro()
        if not cerebro.client:
            self.fail("❌ Error: API Key de Gemini no configurada o inválida.")
        
        res = cerebro.orquestrar_decision_final("TEST", "Prueba de conexión", "Nada")
        print(f"✅ Gemini respondió: {res[:50]}...")
        self.assertIsNotNone(res)

    def test_groq_connection(self):
        print("\n🧪 Probando conexión con Groq...")
        groq_engine = GroqUFCEngine()
        if not groq_engine.client:
            self.fail("❌ Error: API Key de Groq no configurada.")
            
        # Prueba mínima de inferencia
        res, err = groq_engine.analyze_fight("P1", "0-0", 0, 0, 180, 180, "P2", "0-0", 0, 0, 180, 180)
        if err:
            self.fail(f"❌ Groq falló: {err}")
        print(f"✅ Groq respondió con ganador: {res.get('winner')}")
        self.assertIn('winner', res)

if __name__ == "__main__":
    unittest.main()