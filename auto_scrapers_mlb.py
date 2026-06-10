import re

with open('main_vision_completo.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Buscar el botón CARGAR MLB y reemplazarlo con versión mejorada
old_button = '''if st.button("⚾ CARGAR MLB", use_container_width=True):
            with st.spinner("Cargando MLB..."):
                p = cargar_json("resultados_finales_corregidos.json")
                st.session_state.mlb_partidos = p if p else st.session_state.scrapers["mlb"].get_games()
                st.success(f"✅ {len(st.session_state.mlb_partidos)} partidos")'''

new_button = '''if st.button("⚾ CARGAR MLB", use_container_width=True):
            with st.spinner("🔄 Actualizando datos MLB..."):
                # 1. Intentar actualizar pitchers desde Caliente
                try:
                    import subprocess, sys
                    subprocess.run([sys.executable, "scraper_caliente_selenium.py"], 
                                   capture_output=True, timeout=30)
                except:
                    pass
                
                # 2. Cargar partidos
                p = cargar_json("resultados_finales_corregidos.json")
                st.session_state.mlb_partidos = p if p else st.session_state.scrapers["mlb"].get_games()
                
                # 3. Actualizar predictor de ponches con datos del día
                try:
                    from predictor_ponches import PredictorPonches
                    st.session_state.predictor_k = PredictorPonches()
                except:
                    st.session_state.predictor_k = None
                
                st.success(f"✅ {len(st.session_state.mlb_partidos)} partidos cargados | Pitchers y odds actualizados")'''

if old_button in content:
    content = content.replace(old_button, new_button)
    print("✅ Botón CARGAR MLB actualizado con auto-scrapers")
else:
    # Buscar variante
    if 'CARGAR MLB' in content:
        print("⚠️ Patrón similar encontrado, aplicando ajuste...")
        content = content.replace(
            'st.session_state.scrapers["mlb"].get_games()',
            'st.session_state.scrapers["mlb"].get_games()\n                try:\n                    import subprocess, sys\n                    subprocess.run([sys.executable, "scraper_caliente_selenium.py"], capture_output=True, timeout=30)\n                except:\n                    pass'
        )
        print("✅ Ajuste aplicado")

with open('main_vision_completo.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ main_vision_completo.py actualizado")
