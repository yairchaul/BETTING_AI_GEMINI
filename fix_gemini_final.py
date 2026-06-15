import re

with open('cerebro_gemini_pro.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Reemplazar _build_mlb_json_prompt por el NUEVO prompt
old_build = r'def _build_mlb_json_prompt\(self, partido, resultado\):.*?(?=\n    def |\n    def _|\Z)'

new_build = '''def _build_mlb_json_prompt(self, partido, resultado):
        away = partido.get("visitante", partido.get("away", "TBD"))
        home = partido.get("local", partido.get("home", "TBD"))
        p_away = partido.get("pitcher_v", partido.get("pitchers", {}).get("visitante", {}).get("nombre", "TBD"))
        p_home = partido.get("pitcher_l", partido.get("pitchers", {}).get("local", {}).get("nombre", "TBD"))
        whip_v = partido.get("whip_v", "N/A")
        whip_l = partido.get("whip_l", "N/A")
        k_v = partido.get("k_proy_v", "N/A")
        k_l = partido.get("k_proy_l", "N/A")
        ou = partido.get("odds", {}).get("over_under", partido.get("ou_calculado", "N/A"))
        pick = resultado.get("pick", "N/A")
        conf = resultado.get("confianza", 50)
        
        if p_away in ["TBD", "None", None, ""]: p_away = "Por anunciar"
        if p_home in ["TBD", "None", None, ""]: p_home = "Por anunciar"
        
        return f"""Eres NEON V4, analista MLB. NO digas "None vs None" o "falta información".

PARTIDO: {away} @ {home}
LANZADORES: {p_away} vs {p_home}
WHIP: {whip_v} / {whip_l}
K PROYECTADOS: {k_v} / {k_l}
O/U: {ou}
PICK: {pick} ({conf}%)
Si WHIP > 1.45: ALERTA HR.
Recomienda: ML, Handicap, OVER/UNDER, K Props o HR.

JSON: {{"decision":"APOSTAR|EVITAR","mejor_apuesta":"ML|HANDICAP|OVER|UNDER|K|HR","pick":"...","stake":"1u-5u","confianza":0-100,"razon":"..."}}"""'''

content = re.sub(old_build, new_build, content, flags=re.DOTALL)

with open('cerebro_gemini_pro.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ cerebro_gemini_pro.py actualizado - Gemini ya NO dirá "None vs None"')
