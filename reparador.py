import re

def fix_file():
    with open('main_vision_completo.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    skip_mode = False
    
    # Lista de pitchers para la inyección
    PITCHERS_INJECTION = """                # --- INYECCION DE PITCHERS ---
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
                                if "pitchers" not in _x: _x["pitchers"] = {"visitante": {"nombre": ""}, "local": {"nombre": ""}}
                                _x["pitchers"]["visitante"]["nombre"] = _P[_v]
                            if _l in _P:
                                if "pitchers" not in _x: _x["pitchers"] = {"visitante": {"nombre": ""}, "local": {"nombre": ""}}
                                _x["pitchers"]["local"]["nombre"] = _P[_l]
                        with open("resultados_finales_corregidos.json", "w", encoding="utf-8") as _f:
                            _json.dump(_p, _f, indent=2, ensure_ascii=False)
                except Exception as e: pass
"""

    for line in lines:
        # Si encontramos el botón de cargar MLB, insertamos el bloque con la sangría correcta
        if 'if st.button("⚾ CARGAR MLB"' in line:
            new_lines.append(line)
            new_lines.append(PITCHERS_INJECTION)
            continue
        
        # Filtramos líneas que quedaron huérfanas o rotas por el error anterior
        if "PITCHERS_REALES" in line or "import json as _json" in line and "try" not in line:
            continue
            
        new_lines.append(line)

    with open('main_vision_completo.py', 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print("✅ Indentación corregida y pitchers inyectados.")

if __name__ == "__main__":
    fix_file()
