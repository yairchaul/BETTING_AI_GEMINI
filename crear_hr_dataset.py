# import json

bateadores = {
    "Aaron Judge": {"equipo": "NYY", "hr": 9, "hr_por_juego": 0.6},
    "Juan Soto": {"equipo": "NYY", "hr": 6, "hr_por_juego": 0.4},
    "Giancarlo Stanton": {"equipo": "NYY", "hr": 5, "hr_por_juego": 0.33},
    "Jazz Chisholm Jr": {"equipo": "NYY", "hr": 3, "hr_por_juego": 0.2},
    "Anthony Volpe": {"equipo": "NYY", "hr": 2, "hr_por_juego": 0.13},
    "Shohei Ohtani": {"equipo": "LAD", "hr": 8, "hr_por_juego": 0.53},
    "Mookie Betts": {"equipo": "LAD", "hr": 5, "hr_por_juego": 0.33},
    "Freddie Freeman": {"equipo": "LAD", "hr": 4, "hr_por_juego": 0.27},
    "Ronald Acuna Jr": {"equipo": "ATL", "hr": 6, "hr_por_juego": 0.4},
    "Matt Olson": {"equipo": "ATL", "hr": 7, "hr_por_juego": 0.47},
    "Austin Riley": {"equipo": "ATL", "hr": 5, "hr_por_juego": 0.33},
    "Ozzie Albies": {"equipo": "ATL", "hr": 3, "hr_por_juego": 0.2},
    "Bryce Harper": {"equipo": "PHI", "hr": 5, "hr_por_juego": 0.33},
    "Kyle Schwarber": {"equipo": "PHI", "hr": 6, "hr_por_juego": 0.4},
    "Trea Turner": {"equipo": "PHI", "hr": 3, "hr_por_juego": 0.2},
    "Manny Machado": {"equipo": "SD", "hr": 5, "hr_por_juego": 0.33},
    "Fernando Tatis Jr": {"equipo": "SD", "hr": 6, "hr_por_juego": 0.4},
    "Xander Bogaerts": {"equipo": "SD", "hr": 3, "hr_por_juego": 0.2},
    "Mike Trout": {"equipo": "LAA", "hr": 7, "hr_por_juego": 0.47},
    "Yordan Alvarez": {"equipo": "HOU", "hr": 6, "hr_por_juego": 0.4},
    "Jose Altuve": {"equipo": "HOU", "hr": 4, "hr_por_juego": 0.27},
    "Kyle Tucker": {"equipo": "HOU", "hr": 5, "hr_por_juego": 0.33},
    "Rafael Devers": {"equipo": "BOS", "hr": 5, "hr_por_juego": 0.33},
    "Vladimir Guerrero Jr": {"equipo": "TOR", "hr": 6, "hr_por_juego": 0.4},
    "Bo Bichette": {"equipo": "TOR", "hr": 3, "hr_por_juego": 0.2},
    "Julio Rodriguez": {"equipo": "SEA", "hr": 4, "hr_por_juego": 0.27},
    "Randy Arozarena": {"equipo": "SEA", "hr": 3, "hr_por_juego": 0.2},
    "Cal Raleigh": {"equipo": "SEA", "hr": 3, "hr_por_juego": 0.2},
    "Corey Seager": {"equipo": "TEX", "hr": 5, "hr_por_juego": 0.33},
    "Marcus Semien": {"equipo": "TEX", "hr": 4, "hr_por_juego": 0.27},
    "Adolis Garcia": {"equipo": "TEX", "hr": 6, "hr_por_juego": 0.4},
    "Jose Ramirez": {"equipo": "CLE", "hr": 5, "hr_por_juego": 0.33},
    "Josh Naylor": {"equipo": "CLE", "hr": 3, "hr_por_juego": 0.2},
    "Steven Kwan": {"equipo": "CLE", "hr": 1, "hr_por_juego": 0.07},
    "Carlos Correa": {"equipo": "MIN", "hr": 3, "hr_por_juego": 0.2},
    "Byron Buxton": {"equipo": "MIN", "hr": 4, "hr_por_juego": 0.27},
    "Paul Goldschmidt": {"equipo": "STL", "hr": 4, "hr_por_juego": 0.27},
    "Nolan Arenado": {"equipo": "STL", "hr": 4, "hr_por_juego": 0.27},
    "Nolan Gorman": {"equipo": "STL", "hr": 5, "hr_por_juego": 0.33},
    "Spencer Torkelson": {"equipo": "DET", "hr": 4, "hr_por_juego": 0.27},
    "Riley Greene": {"equipo": "DET", "hr": 3, "hr_por_juego": 0.2},
    "Bryan Reynolds": {"equipo": "PIT", "hr": 3, "hr_por_juego": 0.2},
    "Oneil Cruz": {"equipo": "PIT", "hr": 4, "hr_por_juego": 0.27},
    "Corbin Carroll": {"equipo": "ARI", "hr": 4, "hr_por_juego": 0.27},
    "Ketel Marte": {"equipo": "ARI", "hr": 3, "hr_por_juego": 0.2},
    "Luis Robert": {"equipo": "CHW", "hr": 5, "hr_por_juego": 0.33},
    "Elly De La Cruz": {"equipo": "CIN", "hr": 3, "hr_por_juego": 0.2},
    "Pete Alonso": {"equipo": "NYM", "hr": 4, "hr_por_juego": 0.27},
    "Francisco Lindor": {"equipo": "NYM", "hr": 3, "hr_por_juego": 0.2},
    "Christian Yelich": {"equipo": "MIL", "hr": 4, "hr_por_juego": 0.27},
    "Willy Adames": {"equipo": "SF", "hr": 5, "hr_por_juego": 0.33},
    "Matt Chapman": {"equipo": "SF", "hr": 4, "hr_por_juego": 0.27},
    "Dansby Swanson": {"equipo": "CHC", "hr": 3, "hr_por_juego": 0.2},
    "Cody Bellinger": {"equipo": "CHC", "hr": 5, "hr_por_juego": 0.33},
    "Nolan Jones": {"equipo": "COL", "hr": 5, "hr_por_juego": 0.33},
    "Gunnar Henderson": {"equipo": "BAL", "hr": 5, "hr_por_juego": 0.33},
    "Adley Rutschman": {"equipo": "BAL", "hr": 3, "hr_por_juego": 0.2},
    "Yandy Diaz": {"equipo": "TB", "hr": 4, "hr_por_juego": 0.27},
    "Brandon Lowe": {"equipo": "TB", "hr": 3, "hr_por_juego": 0.2},
}

pitchers = {
    "Corbin Burnes": {"equipo": "BAL", "hr_por_juego": 0.8, "pitch_hand": "R"},
    "Zack Wheeler": {"equipo": "PHI", "hr_por_juego": 0.7, "pitch_hand": "R"},
    "Logan Webb": {"equipo": "SF", "hr_por_juego": 0.7, "pitch_hand": "R"},
    "Spencer Strider": {"equipo": "ATL", "hr_por_juego": 0.8, "pitch_hand": "R"},
    "Yoshinobu Yamamoto": {"equipo": "LAD", "hr_por_juego": 0.7, "pitch_hand": "R"},
    "Pablo Lopez": {"equipo": "MIN", "hr_por_juego": 0.9, "pitch_hand": "R"},
    "Framber Valdez": {"equipo": "HOU", "hr_por_juego": 0.7, "pitch_hand": "L"},
    "Kevin Gausman": {"equipo": "TOR", "hr_por_juego": 1.0, "pitch_hand": "R"},
    "Gerrit Cole": {"equipo": "NYY", "hr_por_juego": 0.6, "pitch_hand": "R"},
    "Jacob deGrom": {"equipo": "TEX", "hr_por_juego": 0.5, "pitch_hand": "R"},
    "Shane McClanahan": {"equipo": "TB", "hr_por_juego": 0.7, "pitch_hand": "L"},
    "Tanner Bibee": {"equipo": "CLE", "hr_por_juego": 0.8, "pitch_hand": "R"},
    "Sonny Gray": {"equipo": "STL", "hr_por_juego": 0.7, "pitch_hand": "R"},
    "Mitch Keller": {"equipo": "PIT", "hr_por_juego": 0.9, "pitch_hand": "R"},
    "Brayan Bello": {"equipo": "BOS", "hr_por_juego": 1.0, "pitch_hand": "R"},
    "Luis Castillo": {"equipo": "SEA", "hr_por_juego": 0.7, "pitch_hand": "R"},
    "Justin Steele": {"equipo": "CHC", "hr_por_juego": 0.8, "pitch_hand": "L"},
    "Yu Darvish": {"equipo": "SD", "hr_por_juego": 0.9, "pitch_hand": "R"},
    "Jesus Luzardo": {"equipo": "MIA", "hr_por_juego": 1.0, "pitch_hand": "L"}
}

dataset = {"bateadores": bateadores, "pitchers": pitchers}

with open("hr_datasets_completos.json", "w", encoding="utf-8") as f:
    json.dump(dataset, f, indent=2, ensure_ascii=False)

print("✅ hr_datasets_completos.json CREADO")
print(f"   Bateadores: {len(bateadores)}")
print(f"   Pitchers: {len(pitchers)}")

equipos = {}
for nombre, stats in bateadores.items():
    eq = stats["equipo"]
    if eq not in equipos:
        equipos[eq] = []
    equipos[eq].append(nombre)

print("\n📊 BATEADORES POR EQUIPO:")
for eq, jugadores in sorted(equipos.items(), key=lambda x: len(x[1]), reverse=True)[:15]:
    print(f"   {eq}: {len(jugadores)} - {jugadores[:2]}")

print("\n🚀 streamlit run main_vision_completo.py")
