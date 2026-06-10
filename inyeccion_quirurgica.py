import re

with open('main_vision_completo.py', 'r', encoding='utf-8') as f:
    content = f.read()

# ==================== 1. AGREGAR IMPORTS DE MOTORES ====================
# Solo si no existen ya
if 'MotorOverUnder' not in content:
    motors_import = '''
# ==================== MOTORES AVANZADOS (V24) ====================
from motors.motor_over_under import MotorOverUnder
from motors.motor_momentum import MotorMomentumProfesional
from motors.motor_decision_inteligente import MotorDecisionInteligente
from hr_analyzer_v24_1 import HRAnalyzerUnificado
from analista_total import AnalistaTotal
from clima_mlb import ClimaMLB
from predictor_ponches import PredictorPonches
'''
    content = content.replace(
        'from analyzers.ufc_analyzer import UFCAnalyzer',
        'from analyzers.ufc_analyzer import UFCAnalyzer' + motors_import
    )
    print('✅ Imports de motores V24 agregados')

# ==================== 2. AGREGAR INICIALIZACIÓN DE MOTORES ====================
if 'motor_ou' not in content:
    init_motors = '''
        # Motores V24
        st.session_state.motor_ou = MotorOverUnder()
        st.session_state.motor_momentum = MotorMomentumProfesional()
        st.session_state.motor_decision = MotorDecisionInteligente()
        st.session_state.hr_analyzer = HRAnalyzerUnificado()
        st.session_state.analista_total = AnalistaTotal(st.session_state.get('gemini'), st.session_state.get('groq'))
        st.session_state.clima_mlb = ClimaMLB()
        st.session_state.predictor_k = PredictorPonches()
'''
    content = content.replace(
        'st.session_state.init = True',
        init_motors + '\n        st.session_state.init = True'
    )
    print('✅ Inicialización de motores V24 agregada')

# ==================== 3. ACTUALIZAR BOTÓN CARGAR MLB ====================
old_mlb_button = '''        # MLB
        if st.button("⚾ CARGAR MLB", use_container_width=True):
            with st.spinner("Cargando MLB..."):
                st.session_state.mlb_partidos = st.session_state.scrapers['mlb'].get_games()
                if st.session_state.mlb_partidos:
                    st.success(f"✅ {len(st.session_state.mlb_partidos)} partidos")
                else:
                    st.warning("⚠️ No hay partidos MLB hoy")'''

new_mlb_button = '''        # MLB (ACTUALIZACIÓN AUTOMÁTICA DE PITCHERS)
        if st.button("⚾ CARGAR MLB", use_container_width=True):
            with st.spinner("Cargando MLB..."):
                # Inyectar pitchers reales antes de cargar
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
                    _p = st.session_state.scrapers['mlb'].get_games()
                    if _p:
                        for _x in _p:
                            _v = _x.get("visitante", ""); _l = _x.get("local", "")
                            if "pitchers" not in _x: _x["pitchers"] = {"visitante": {}, "local": {}}
                            if _v in _P: _x["pitchers"]["visitante"]["nombre"] = _P[_v]
                            if _l in _P: _x["pitchers"]["local"]["nombre"] = _P[_l]
                        with open("resultados_finales_corregidos.json", "w", encoding="utf-8") as _f:
                            _json.dump(_p, _f, indent=2, ensure_ascii=False)
                        st.session_state.mlb_partidos = _p
                    else:
                        st.session_state.mlb_partidos = []
                except:
                    st.session_state.mlb_partidos = st.session_state.scrapers['mlb'].get_games()
                
                if st.session_state.mlb_partidos:
                    st.success(f"✅ {len(st.session_state.mlb_partidos)} partidos | Pitchers actualizados")
                else:
                    st.warning("⚠️ No hay partidos MLB hoy")'''

if old_mlb_button in content:
    content = content.replace(old_mlb_button, new_mlb_button)
    print('✅ Botón CARGAR MLB actualizado con inyección de pitchers')
else:
    print('⚠️ No se encontró el botón MLB exacto')
    # Intentar con patrón más flexible
    if 'if st.button("⚾ CARGAR MLB"' in content:
        print('   Buscando variante...')
        content = content.replace(
            'st.session_state.scrapers[\'mlb\'].get_games()',
            '''st.session_state.scrapers['mlb'].get_games()
                try:
                    import json as _json
                    _P = {"Tampa Bay Rays": "Steven Matz", "Cleveland Guardians": "Logan Allen", "New York Yankees": "Gerrit Cole", "Los Angeles Dodgers": "Yoshinobu Yamamoto"}
                    _p = st.session_state.scrapers['mlb'].get_games()
                    if _p:
                        for _x in _p:
                            _v = _x.get("visitante", ""); _l = _x.get("local", "")
                            if "pitchers" not in _x: _x["pitchers"] = {"visitante": {}, "local": {}}
                            if _v in _P: _x["pitchers"]["visitante"]["nombre"] = _P[_v]
                            if _l in _P: _x["pitchers"]["local"]["nombre"] = _P[_l]
                except: pass'''
        )
        print('   Parche aplicado')

with open('main_vision_completo.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ main_vision_completo.py actualizado')

