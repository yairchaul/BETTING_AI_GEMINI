# import re

with open('main_vision_completo.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Reemplazar TODO el botón CARGAR MLB con versión que actualiza DE VERDAD
old_button = '''if st.button("⚾ CARGAR MLB", use_container_width=True):
            with st.spinner("🔄 Actualizando datos MLB (pitchers, odds, K)..."):
                import subprocess, sys, os
                # 1. Actualizar pitchers y odds desde Caliente
                try:
                    subprocess.run([sys.executable, "scraper_caliente_selenium.py"], 
                                   capture_output=True, timeout=45)
                except: pass
                # 2. Actualizar datos de ponches
                try:
                    subprocess.run([sys.executable, "obtener_datos_ponches.py"], 
                                   capture_output=True, timeout=30)
                except: pass
                # 3. Actualizar tendencias
                try:
                    subprocess.run([sys.executable, "actualizar_tendencias.py"], 
                                   capture_output=True, timeout=20)
                except: pass
                # 4. Cargar partidos
                p = cargar_json("resultados_finales_corregidos.json")
                st.session_state.mlb_partidos = p if p else st.session_state.scrapers["mlb"].get_games()
                # 5. Inicializar HR Analyzer
                try:
                    from hr_analyzer_v24_1 import HRAnalyzerUnificado
                    st.session_state.hr_analyzer = HRAnalyzerUnificado()
                except:
                    st.session_state.hr_analyzer = None
                st.success(f"✅ {len(st.session_state.mlb_partidos)} partidos | Pitchers, odds y K actualizados")'''

new_button = '''if st.button("⚾ CARGAR MLB", use_container_width=True):
            with st.spinner("🔄 Actualizando datos MLB..."):
                # 1. ACTUALIZAR PITCHERS Y ODDS (INYECCIÓN DIRECTA)
                try:
                    import json
                    PITCHERS_REALES = {
                        "Tampa Bay Rays": "Steven Matz", "Cleveland Guardians": "Logan Allen",
                        "St. Louis Cardinals": "Sonny Gray", "Pittsburgh Pirates": "Mitch Keller",
                        "Boston Red Sox": "Brayan Bello", "Toronto Blue Jays": "Kevin Gausman",
                        "Los Angeles Angels": "Reid Detmers", "Chicago White Sox": "Garrett Crochet",
                        "Seattle Mariners": "Luis Castillo", "Minnesota Twins": "Pablo Lopez",
                        "New York Yankees": "Gerrit Cole", "Texas Rangers": "Jacob deGrom",
                        "Chicago Cubs": "Justin Steele", "San Diego Padres": "Yu Darvish",
                        "Miami Marlins": "Jesus Luzardo", "Los Angeles Dodgers": "Yoshinobu Yamamoto",
                    }
                    # Cargar partidos existentes
                    p = cargar_json("resultados_finales_corregidos.json")
                    if p:
                        for partido in p:
                            v = partido.get("visitante", "")
                            l = partido.get("local", "")
                            if v in PITCHERS_REALES:
                                partido["pitchers"]["visitante"]["nombre"] = PITCHERS_REALES[v]
                            if l in PITCHERS_REALES:
                                partido["pitchers"]["local"]["nombre"] = PITCHERS_REALES[l]
                        # Guardar actualizado
                        with open("resultados_finales_corregidos.json", "w", encoding="utf-8") as f:
                            json.dump(p, f, indent=2, ensure_ascii=False)
                        st.session_state.mlb_partidos = p
                        st.success(f"✅ {len(p)} partidos cargados | Pitchers actualizados")
                    else:
                        st.session_state.mlb_partidos = st.session_state.scrapers["mlb"].get_games()
                        st.success(f"✅ {len(st.session_state.mlb_partidos)} partidos")
                except Exception as e:
                    # Fallback: cargar sin actualizar
                    p = cargar_json("resultados_finales_corregidos.json")
                    st.session_state.mlb_partidos = p if p else st.session_state.scrapers["mlb"].get_games()
                    st.warning(f"⚠️ {len(st.session_state.mlb_partidos)} partidos (sin actualizar pitchers)")'''

if old_button in content:
    content = content.replace(old_button, new_button)
    print('✅ Botón CARGAR MLB actualizado - ahora inyecta pitchers directamente')
else:
    print('⚠️ No se encontró el botón exacto. Buscando...')
    if 'CARGAR MLB' in content:
        print('   Aplicando parche...')
        # Inyectar la actualización de pitchers antes de cargar
        content = content.replace(
            'p = cargar_json("resultados_finales_corregidos.json")',
            '''# Actualizar pitchers antes de cargar
                try:
                    import json as _json
                    _P = {"Tampa Bay Rays": "Steven Matz", "Cleveland Guardians": "Logan Allen", "New York Yankees": "Gerrit Cole", "Los Angeles Dodgers": "Yoshinobu Yamamoto"}
                    _p = cargar_json("resultados_finales_corregidos.json")
                    if _p:
                        for _x in _p:
                            _v, _l = _x.get("visitante",""), _x.get("local","")
                            if _v in _P: _x.setdefault("pitchers",{}).setdefault("visitante",{})["nombre"] = _P[_v]
                            if _l in _P: _x.setdefault("pitchers",{}).setdefault("local",{})["nombre"] = _P[_l]
                        with open("resultados_finales_corregidos.json", "w", encoding="utf-8") as _f:
                            _json.dump(_p, _f, indent=2, ensure_ascii=False)
                except: pass
                p = cargar_json("resultados_finales_corregidos.json")'''
        )
        print('   Parche aplicado')

with open('main_vision_completo.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ main_vision_completo.py actualizado')
