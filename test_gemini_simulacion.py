print("=" * 60)
print("🧪 SIMULACIÓN DE PROMPT PARA GEMINI")
print("=" * 60)

# Datos que DEBERÍA recibir Gemini
partido = {
    "visitante": "Tampa Bay Rays",
    "local": "Cleveland Guardians",
    "pitcher_v": "N. Martinez",
    "pitcher_l": "T. Bibee",
    "whip_v": 1.25,
    "whip_l": 1.25,
    "k_proy_v": 5.5,
    "k_proy_l": 5.2,
    "odds": {"over_under": 8.5}
}

resultado = {"pick": "Tampa Bay Rays", "confianza": 54}

# Construir el prompt COMO DEBERÍA SER
prompt = f"""Eres NEON V4, analista MLB. NO digas "None vs None" o "falta información".

PARTIDO: {partido['visitante']} @ {partido['local']}
LANZADORES: {partido['pitcher_v']} vs {partido['pitcher_l']}
WHIP: {partido['whip_v']} / {partido['whip_l']}
K PROYECTADOS: {partido['k_proy_v']} / {partido['k_proy_l']}
O/U: {partido['odds']['over_under']}
PICK: {resultado['pick']} ({resultado['confianza']}%)

Recomienda: ML, Handicap, OVER/UNDER, K Props o HR.
JSON: {{"decision":"APOSTAR|EVITAR","mejor_apuesta":"ML|HANDICAP|OVER|UNDER|K|HR","pick":"...","stake":"1u-5u","confianza":0-100,"razon":"..."}}"""

print("✅ PROMPT CORRECTO:")
print(prompt)
print()
print("=" * 60)
print("⏳ Este es el prompt que Gemini DEBE recibir.")
print("   Si Gemini responde con 'None vs None', el prompt no se está usando.")
