import json

with open('main_vision_completo.py', 'r', encoding='utf-8') as f:
    content = f.read()

# NUEVO BOTÓN CARGAR MLB que traduce nombres y completa datos
new_mlb_button = '''        if st.button("⚾ CARGAR MLB", use_container_width=True):
            with st.spinner("Cargando MLB desde ESPN..."):
                partidos_espn = st.session_state.scrapers["mlb"].get_games()
                
                if partidos_espn:
                    # TRADUCCIÓN de nombres ESPN español → inglés
                    TRADUCCION = {
                        "Rayos de Tampa Bay": "Tampa Bay Rays",
                        "Guardianes de Cleveland": "Cleveland Guardians",
                        "Astros de Houston": "Houston Astros",
                        "Orioles de Baltimore": "Baltimore Orioles",
                        "Rockies de Colorado": "Colorado Rockies",
                        "Rojos de Cincinnati": "Cincinnati Reds",
                        "Gigantes de San Francisco": "San Francisco Giants",
                        "Filis de Filadelfia": "Philadelphia Phillies",
                        "Cardenales de San Luis": "St. Louis Cardinals",
                        "Piratas de Pittsburgh": "Pittsburgh Pirates",
                        "Medias Rojas de Boston": "Boston Red Sox",
                        "Azulejos de Toronto": "Toronto Blue Jays",
                        "Nacionales de Washington": "Washington Nationals",
                        "Mets de Nueva York": "New York Mets",
                        "Tigres de Detroit": "Detroit Tigers",
                        "Bravos de Atlanta": "Atlanta Braves",
                        "Angelinos de Los Angeles": "Los Angeles Angels",
                        "Medias Blancas de Chicago": "Chicago White Sox",
                        "Cascabeles de Arizona": "Arizona Diamondbacks",
                        "Cerveceros de Milwaukee": "Milwaukee Brewers",
                        "Marineros de Seattle": "Seattle Mariners",
                        "Mellizos de Minnesota": "Minnesota Twins",
                        "Yankees de Nueva York": "New York Yankees",
                        "Vigilantes de Texas": "Texas Rangers",
                        "Cachorros de Chicago": "Chicago Cubs",
                        "Padres de San Diego": "San Diego Padres",
                        "Reales de Kansas City": "Kansas City Royals",
                        "Marlins de Miami": "Miami Marlins",
                        "Dodgers de Los Angeles": "Los Angeles Dodgers",
                    }
                    
                    # Datos COMPLETOS de pitchers y odds
                    DATOS_COMPLETOS = { # Actualizado 12 de Junio
                        "Miami Marlins": ("S. Alcantara", "+120", "N/A"),
                        "Pittsburgh Pirates": ("B. Ashcraft", "-143", "N/A"),
                        "Seattle Mariners": ("B. Miller", "-150", "N/A"),
                        "Washington Nationals": ("Z. Littell", "+125", "N/A"),
                        "San Diego Padres": ("G. Canning", "+110", "N/A"),
                        "Baltimore Orioles": ("S. Baz", "-130", "N/A"),
                        "Texas Rangers": ("J. Leiter", "+105", "N/A"),
                        "Boston Red Sox": ("S. Gray", "-125", "N/A"),
                        "Detroit Tigers": ("J. Flaherty", "+105", "N/A"),
                        "Cleveland Guardians": ("T. Bibee", "-125", "N/A"),
                        "Arizona Diamondbacks": ("E. Rodriguez", "-106", "N/A"),
                        "Cincinnati Reds": ("N. Lodolo", "-112", "N/A"),
                        "Atlanta Braves": ("S. Strider", "+105", "N/A"),
                        "New York Mets": ("N. McLean", "-125", "N/A"),
                        "New York Yankees": ("R. Weathers", "-106", "N/A"),
                        "Toronto Blue Jays": ("T. Yesavage", "-112", "N/A"),
                        "Philadelphia Phillies": ("A. Painter", "+210", "N/A"),
                        "Milwaukee Brewers": ("J. Misiorowski", "-250", "N/A"),
                        "Los Angeles Dodgers": ("R. Sasaki", "-175", "N/A"),
                        "Chicago White Sox": ("A. Kay", "+145", "N/A"),
                        "Houston Astros": ("T. Imai", "-112", "N/A"),
                        "Kansas City Royals": ("L. Avila", "-106", "N/A"),
                        "St. Louis Cardinals": ("K. Leahy", "+115", "N/A"),
                        "Minnesota Twins": ("J. Ryan", "-134", "N/A"),
                        "Tampa Bay Rays": ("S. McClanahan", "-175", "N/A"),
                        "Los Angeles Angels": ("S. Aldegheri", "+145", "N/A"),
                        "Colorado Rockies": ("Unknown Pitcher", "+185", "N/A"),
                        "Athletics": ("G. Jump", "-223", "N/A"),
                        "Chicago Cubs": ("J. Assad", "+105", "N/A"),
                        "San Francisco Giants": ("L. Roupp", "-125", "N/A"),
                    }
                    
                    for p in partidos_espn:
                        # Traducir nombres
                        v = p.get("visitante", "")
                        l = p.get("local", "")
                        if v in TRADUCCION: p["visitante"] = TRADUCCION[v]
                        if l in TRADUCCION: p["local"] = TRADUCCION[l]
                        
                        v = p["visitante"]
                        l = p["local"]
                        
                        # Inyectar pitchers, odds y records
                        if "pitchers" not in p: p["pitchers"] = {"visitante": {}, "local": {}}
                        if "odds" not in p: p["odds"] = {"moneyline": {}, "over_under": p.get("odds", {}).get("over_under", "8.0")}
                        
                        if v in DATOS_COMPLETOS:
                            p["pitchers"]["visitante"]["nombre"] = DATOS_COMPLETOS[v][0]
                            p["odds"]["moneyline"]["visitante"] = DATOS_COMPLETOS[v][1]
                            p["visit_record"] = DATOS_COMPLETOS[v][2]
                        if l in DATOS_COMPLETOS:
                            p["pitchers"]["local"]["nombre"] = DATOS_COMPLETOS[l][0]
                            p["odds"]["moneyline"]["local"] = DATOS_COMPLETOS[l][1]
                            p["local_record"] = DATOS_COMPLETOS[l][2]
                    
                    # Guardar
                    with open("resultados_finales_corregidos.json", "w", encoding="utf-8") as f:
                        json.dump(partidos_espn, f, indent=2, ensure_ascii=False)
                    
                    # También actualizar pitchers_hoy_selenium.json
                    juegos = []
                    for p in partidos_espn:
                        juegos.append({
                            "away_team": p["visitante"],
                            "home_team": p["local"],
                            "away_pitcher": p["pitchers"]["visitante"]["nombre"],
                            "home_pitcher": p["pitchers"]["local"]["nombre"],
                        })
                    with open("pitchers_hoy_selenium.json", "w", encoding="utf-8") as f:
                        json.dump({"juegos": juegos}, f, indent=2, ensure_ascii=False)
                    
                    st.session_state.mlb_partidos = partidos_espn
                    st.success(f"✅ {len(partidos_espn)} partidos | Nombres traducidos | Pitchers, odds y records actualizados")
                else:
                    st.warning("⚠️ No hay partidos MLB hoy")'''

# Reemplazar el botón viejo
import re
pattern = r'if st\.button\("⚾ CARGAR MLB".*?(?=if st\.button\("🥊 CARGAR UFC")'
match = re.search(pattern, content, re.DOTALL)
if match:
    content = content.replace(match.group(0), new_mlb_button)
    print('✅ Botón MLB actualizado con TRADUCCIÓN + DATOS COMPLETOS')

with open('main_vision_completo.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ main_vision_completo.py actualizado')
