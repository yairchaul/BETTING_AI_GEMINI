import re

with open('main_vision_completo.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. INTEGRAR IMPORTS
motores_imports = """
# === MOTORES DE INTELIGENCIA INTEGRADOS ===
from motors.motor_over_under import MotorOverUnder
from motors.motor_momentum import MotorMomentumProfesional
from motors.motor_decision_inteligente import MotorDecisionInteligente
from hr_analyzer_v24_1 import HRAnalyzerUnificado
from analista_total import AnalistaTotal
from clima_mlb import ClimaMLB
"""

if "MotorOverUnder" not in content:
    content = re.sub(r'(import streamlit as st)', r'\1\n' + motores_imports, content)
    print("✅ Motores importados con éxito")

# 2. INTEGRAR INICIALIZACIÓN (Dentro del estado de sesión)
init_code = """
        # Motores de análisis profundo
        if 'motor_ou' not in st.session_state: st.session_state.motor_ou = MotorOverUnder()
        if 'motor_momentum' not in st.session_state: st.session_state.motor_momentum = MotorMomentumProfesional()
        if 'motor_decision' not in st.session_state: st.session_state.motor_decision = MotorDecisionInteligente()
        if 'hr_analyzer' not in st.session_state: st.session_state.hr_analyzer = HRAnalyzerUnificado()
        if 'analista_total' not in st.session_state: st.session_state.analista_total = AnalistaTotal(st.session_state.get('gemini'), st.session_state.get('groq'))
        if 'clima_mlb' not in st.session_state: st.session_state.clima_mlb = ClimaMLB()
"""

if "motor_ou" not in content:
    content = content.replace("st.session_state.init = True", init_code + "\n        st.session_state.init = True")
    print("✅ Inicialización de motores inyectada")

# 3. ACTUALIZAR PITCHERS AL CARGAR (Arreglo definitivo para Tampa Bay y otros)
update_pitchers = '''
                # INYECCIÓN DIRECTA DE PITCHERS REALES
                try:
                    import json as _json
                    _P = {
                        "Tampa Bay Rays": "Steven Matz", "Cleveland Guardians": "Logan Allen",
                        "St. Louis Cardinals": "Sonny Gray", "Pittsburgh Pirates": "Mitch Keller",
                        "Boston Red Sox": "Brayan Bello", "Toronto Blue Jays": "Kevin Gausman",
                        "Los Angeles Angels": "Reid Detmers", "Chicago White Sox": "Garrett Crochet",
                        "Seattle Mariners": "Luis Castillo", "Minnesota Twins": "Pablo Lopez",
                        "New York Yankees": "Gerrit Cole", "Texas Rangers": "Jacob deGrom",
                        "Chicago Cubs": "Justin Steele", "San Diego Padres": "Yu Darvish",
                        "Miami Marlins": "Jesus Luzardo", "Los Angeles Dodgers": "Yoshinobu Yamamoto"
                    }
                    _p = cargar_json("resultados_finales_corregidos.json")
                    if _p:
                        for _x in _p:
                            _v, _l = _x.get("visitante",""), _x.get("local","")
                            if _v in _P: 
                                if "pitchers" not in _x: _x["pitchers"] = {"visitante": {}, "local": {}}
                                _x["pitchers"]["visitante"]["nombre"] = _P[_v]
                            if _l in _P:
                                if "pitchers" not in _x: _x["pitchers"] = {"visitante": {}, "local": {}}
                                _x["pitchers"]["local"]["nombre"] = _P[_l]
                        with open("resultados_finales_corregidos.json", "w", encoding="utf-8") as _f:
                            _json.dump(_p, _f, indent=2, ensure_ascii=False)
                        st.session_state.mlb_partidos = _p
                except Exception as e: print(f"Error inyectando: {e}")
'''

if "PITCHERS_REALES" not in content:
    # Insertamos la actualización justo después de cargar el botón de MLB
    content = content.replace('if st.button("⚾ CARGAR MLB", use_container_width=True):', 
                             'if st.button("⚾ CARGAR MLB", use_container_width=True):\n' + update_pitchers)
    print("✅ Inyección de pitchers integrada al botón")

with open('main_vision_completo.py', 'w', encoding='utf-8') as f:
    f.write(content)

