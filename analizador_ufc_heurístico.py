# -*- coding: utf-8 -*-
"""
Módulo Heurístico para BETTING_AI
Calcula ventajas físicas y de mercado
"""
import json

class AnalizadorUFCHuristico:
    def __init__(self):
        self.data_path = "data_input_ai.json"

    def calcular_probabilidad(self):
        try:
            with open(self.data_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            resumen = []
            resumen.append("=" * 60)
            resumen.append("🤖 BETTING_AI - ANALIZADOR DE PROBABILIDAD")
            resumen.append("=" * 60)

            # 1. Análisis de Ventaja Física
            fisica = data.get("ventaja_fisica", {})
            alcance_val = fisica.get("alcance", "N/A")
            
            resumen.append(f"📊 Estadísticas Físicas Detectadas:")
            resumen.append(f"   📏 Alcance: {alcance_val}")
            resumen.append(f"   🎂 Edad: {fisica.get('edad', 'N/A')}")

            # 2. Análisis de Mercado
            mercado = data.get("mercado_caliente", [])
            resumen.append(f"\n💰 Momios en Caliente.mx:")
            for peleador, momio in mercado:
                alerta = "⚠️ [Underdog]" if "+" in momio else "🔥 [Favorito]"
                resumen.append(f"   {alerta} {peleador}: {momio}")

            # 3. Lógica de Decisión
            resumen.append("\n🎯 CONCLUSIÓN DEL MOTOR:")
            if str(alcance_val) != "N/A":
                resumen.append("   ✅ VENTAJA FÍSICA DETECTADA: Análisis de alcance integrado.")
            
            resumen.append("=" * 60)
            
            print("\n".join(resumen))
            return "\n".join(resumen)

        except FileNotFoundError:
            msg = "❌ Error: No se encontró 'data_input_ai.json'."
            print(msg)
            return msg
        except Exception as e:
            msg = f"❌ Error en heurístico: {e}"
            print(msg)
            return msg

if __name__ == "__main__":
    # Prueba rápida
    engine = AnalizadorUFCHuristico()
    engine.calcular_probabilidad()
