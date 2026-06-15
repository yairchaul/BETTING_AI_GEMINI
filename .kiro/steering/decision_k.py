# -*- coding: utf-8 -*-
import pandas as pd

def decidir_apuesta_k(pitcher_name, proy_k, linea_casa=4.5):
    """
    Decide si la apuesta es Over o Under basada en un margen de confianza.
    """
    margen = proy_k - linea_casa
    
    # Umbral de confianza de 1.2 strikes de diferencia
    if margen >= 1.2:
        return {
            "jugada": "🔥 OVER",
            "confianza": "ALTA",
            "motivo": f"Proyección ({proy_k}) muy superior a la línea ({linea_casa})"
        }
    elif margen <= -1.2:
        return {
            "jugada": "❄️ UNDER",
            "confianza": "ALTA",
            "motivo": f"Proyección ({proy_k}) muy inferior a la línea ({linea_casa})"
        }
    else:
        return {
            "jugada": "⚠️ PASAR",
            "confianza": "BAJA",
            "motivo": "Línea muy ajustada a la proyección"
        }

# Ejemplo de prueba con tus datos de hoy
test_pitchers = [
    {"name": "Ranger Suarez", "proy": 7.5, "linea": 5.5},
    {"name": "Luis Castillo", "proy": 4.2, "linea": 5.5},
    {"name": "Dylan Cease", "proy": 5.0, "linea": 5.5}
]

print("\n" + "📋 RECOMENDACIONES DE PONCHES (K-PROPS)".center(50, "="))
for p in test_pitchers:
    decision = decidir_apuesta_k(p['name'], p['proy'], p['linea'])
    print(f"🧤 {p['name']} | Línea: {p['linea']} | Proy: {p['proy']}")
    print(f"   Resultado: {decision['jugada']} ({decision['motivo']})")
    print("-" * 50)


def generar_recomendaciones_k():
    """Genera recomendaciones de Over/Under de ponches para todos los lanzadores"""
    # Este es un stub, la implementación real necesitaría cargar los pitchers del día
    # y sus líneas de apuestas para generar recomendaciones.
    return []