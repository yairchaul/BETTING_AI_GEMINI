import re

with open('main_vision_completo.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Actualizar botón CARGAR MLB para ejecutar scrapers automáticamente
old_mlb_button = '''if st.button("⚾ CARGAR MLB", use_container_width=True):
            with st.spinner("Cargando MLB..."):
                p = cargar_json("resultados_finales_corregidos.json")
                st.session_state.mlb_partidos = p if p else st.session_state.scrapers["mlb"].get_games()
                st.success(f"✅ {len(st.session_state.mlb_partidos)} partidos")'''

new_mlb_button = '''if st.button("⚾ CARGAR MLB", use_container_width=True):
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

if old_mlb_button in content:
    content = content.replace(old_mlb_button, new_mlb_button)
    print('✅ Botón CARGAR MLB actualizado con auto-scrapers + HR Analyzer')
else:
    print('⚠️ Buscando variante del botón MLB...')
    if 'CARGAR MLB' in content:
        print('   Botón encontrado, aplicando parche...')
        content = content.replace(
            'st.session_state.scrapers["mlb"].get_games()',
            'st.session_state.scrapers["mlb"].get_games()\n                try:\n                    import subprocess, sys\n                    subprocess.run([sys.executable, "scraper_caliente_selenium.py"], capture_output=True, timeout=45)\n                    subprocess.run([sys.executable, "obtener_datos_ponches.py"], capture_output=True, timeout=30)\n                except: pass'
        )
        print('   Parche aplicado')

with open('main_vision_completo.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ main_vision_completo.py actualizado')
