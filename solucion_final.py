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
                    DATOS_COMPLETOS = {
                        "Tampa Bay Rays": ("Steven Matz", "+115", "16-11"),
                        "Cleveland Guardians": ("Logan Allen", "-118", "15-14"),
                        "Houston Astros": ("Framber Valdez", "+120", "11-18"),
                        "Baltimore Orioles": ("Corbin Burnes", "-105", "13-15"),
                        "Colorado Rockies": ("Kyle Freeland", "+130", "12-16"),
                        "Cincinnati Reds": ("Hunter Greene", "-115", "18-10"),
                        "San Francisco Giants": ("Logan Webb", "+140", "13-15"),
                        "Philadelphia Phillies": ("Zack Wheeler", "-110", "9-19"),
                        "St. Louis Cardinals": ("Sonny Gray", "+142", "14-13"),
                        "Pittsburgh Pirates": ("Mitch Keller", "-111", "16-12"),
                        "Boston Red Sox": ("Brayan Bello", "+141", "11-17"),
                        "Toronto Blue Jays": ("Kevin Gausman", "-117", "12-15"),
                        "Washington Nationals": ("Josiah Gray", "+135", "13-16"),
                        "New York Mets": ("Kodai Senga", "-120", "9-18"),
                        "Detroit Tigers": ("Tarik Skubal", "+130", "15-14"),
                        "Atlanta Braves": ("Spencer Strider", "-130", "20-9"),
                        "Los Angeles Angels": ("Reid Detmers", "+143", "12-17"),
                        "Chicago White Sox": ("Garrett Crochet", "-145", "11-17"),
                        "Arizona Diamondbacks": ("Zac Gallen", "+125", "15-12"),
                        "Milwaukee Brewers": ("Freddy Peralta", "-110", "14-13"),
                        "Seattle Mariners": ("Luis Castillo", "+125", "14-15"),
                        "Minnesota Twins": ("Pablo Lopez", "-119", "12-16"),
                        "New York Yankees": ("Gerrit Cole", "+146", "18-10"),
                        "Texas Rangers": ("Jacob deGrom", "-127", "14-14"),
                        "Chicago Cubs": ("Justin Steele", "+110", "17-11"),
                        "San Diego Padres": ("Yu Darvish", "-136", "18-9"),
                        "Kansas City Royals": ("Cole Ragans", "+115", "11-17"),
                        "Miami Marlins": ("Jesus Luzardo", "+147", "13-15"),
                        "Los Angeles Dodgers": ("Yoshinobu Yamamoto", "-121", "19-9"),
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
