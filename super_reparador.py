import re

def super_fix():
    with open('main_vision_completo.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # Definimos el bloque NUEVO con la indentación exacta de 12 y 16 espacios
    # Este bloque reemplazará al que está roto.
    new_button_block = '''    if st.button("⚾ CARGAR MLB", use_container_width=True):
        with st.spinner("🔄 Actualizando datos y alineando pitchers..."):
            try:
                import json as _json
                # Diccionario de inyección manual
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
                
                # Cargar y actualizar JSON
                _p = cargar_json("resultados_finales_corregidos.json")
                if _p:
                    for _x in _p:
                        _v, _l = _x.get("visitante",""), _x.get("local","")
                        if _v in _P: 
                            if "pitchers" not in _x: _x["pitchers"] = {"visitante": {"nombre": ""}, "local": {"nombre": ""}}
                            _x["pitchers"]["visitante"]["nombre"] = _P[_v]
                        if _l in _P:
                            if "pitchers" not in _x: _x["pitchers"] = {"visitante": {"nombre": ""}, "local": {"nombre": ""}}
                            _x["pitchers"]["local"]["nombre"] = _P[_l]
                    
                    with open("resultados_finales_corregidos.json", "w", encoding="utf-8") as _f:
                        _json.dump(_p, _f, indent=2, ensure_ascii=False)
                
                # Actualizar estado de la sesión
                st.session_state.mlb_partidos = _p if _p else []
                st.success("✅ Datos de MLB y Pitchers actualizados correctamente")
            except Exception as e:
                st.error(f"Error en la carga: {str(e)}")
'''

    # Usamos una expresión regular para encontrar el bloque del botón viejo (aunque esté mal indentado)
    # y lo reemplazamos por nuestro bloque limpio.
    pattern = r'if st\.button\("⚾ CARGAR MLB".*?st\.success\(.*?\)'
    
    # Si no encuentra el success, intentamos una búsqueda más amplia hasta el siguiente bloque de código
    if not re.search(pattern, content, re.DOTALL):
        pattern = r'if st\.button\("⚾ CARGAR MLB".*?with st\.spinner\(.*?\):'
    
    fixed_content = re.sub(pattern, new_button_block, content, flags=re.DOTALL)

    with open('main_vision_completo.py', 'w', encoding='utf-8') as f:
        f.write(fixed_content)
    print("✅ Bloque MLB re-estructurado con éxito.")

if __name__ == "__main__":
    super_fix()
