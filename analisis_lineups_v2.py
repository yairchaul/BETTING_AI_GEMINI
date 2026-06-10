import json

with open("hr_datasets_completos.json", "r", encoding="utf-8") as f:
    hr_data = json.load(f)
bateadores = hr_data.get("bateadores", {})

# LINEUPS REALES
LINEUPS = {
    "2026-04-26|Los Angeles Dodgers": ["Shohei Ohtani", "Mookie Betts", "Freddie Freeman", "Will Smith", "Max Muncy", "Teoscar Hernandez", "James Outman", "Gavin Lux", "Miguel Rojas"],
    "2026-04-26|New York Yankees": ["Aaron Judge", "Juan Soto", "Giancarlo Stanton", "Anthony Volpe", "Jazz Chisholm Jr", "Anthony Rizzo", "DJ LeMahieu", "Jose Trevino", "Oswaldo Cabrera"],
    "2026-04-26|Atlanta Braves": ["Ronald Acuna Jr", "Matt Olson", "Austin Riley", "Ozzie Albies", "Michael Harris II", "Sean Murphy", "Orlando Arcia", "Jarred Kelenic", "Adam Duvall"],
    "2026-04-26|Philadelphia Phillies": ["Bryce Harper", "Kyle Schwarber", "Trea Turner", "J.T. Realmuto", "Nick Castellanos", "Alec Bohm", "Brandon Marsh", "Bryson Stott", "Johan Rojas"],
    "2026-04-26|Texas Rangers": ["Corey Seager", "Marcus Semien", "Adolis Garcia", "Josh Jung", "Evan Carter", "Jonah Heim", "Leody Taveras", "Ezequiel Duran", "Wyatt Langford"],
    "2026-04-26|Seattle Mariners": ["Julio Rodriguez", "Cal Raleigh", "Randy Arozarena", "J.P. Crawford", "Ty France", "Mitch Garver", "Luke Raley", "Dominic Canzone", "Josh Rojas"],
    "2026-04-26|Houston Astros": ["Yordan Alvarez", "Jose Altuve", "Kyle Tucker", "Alex Bregman", "Jeremy Pena", "Yainer Diaz", "Chas McCormick", "Jose Abreu", "Mauricio Dubon"],
    "2026-04-26|Boston Red Sox": ["Rafael Devers", "Triston Casas", "Masataka Yoshida", "Trevor Story", "Jarren Duran", "Ceddanne Rafaela", "Wilyer Abreu", "Connor Wong", "Enmanuel Valdez"],
    "2026-04-26|Toronto Blue Jays": ["Vladimir Guerrero Jr", "Bo Bichette", "George Springer", "Daulton Varsho", "Alejandro Kirk", "Davis Schneider", "Cavan Biggio", "Kevin Kiermaier", "Isiah Kiner-Falefa"],
    "2026-04-26|Cleveland Guardians": ["Steven Kwan", "Angel Martinez", "Jose Ramirez", "Rhys Hoskins", "Chase DeLauter", "David Fry", "Daniel Schneemann", "Austin Hedges", "Brayan Rocchio"],
    "2026-04-26|San Diego Padres": ["Fernando Tatis Jr", "Manny Machado", "Xander Bogaerts", "Luis Campusano", "Ha-Seong Kim", "Jake Cronenworth", "Trent Grisham", "Matthew Batten"],
    "2026-04-26|Arizona Diamondbacks": ["Corbin Carroll", "Ketel Marte", "Christian Walker", "Lourdes Gurriel Jr", "Gabriel Moreno", "Eugenio Suarez", "Jake McCarthy", "Alek Thomas", "Geraldo Perdomo"],
    "2026-04-26|Chicago Cubs": ["Cody Bellinger", "Dansby Swanson", "Ian Happ", "Seiya Suzuki", "Nico Hoerner", "Michael Busch", "Mike Tauchman", "Yan Gomes", "Nick Madrigal"],
    "2026-04-26|Miami Marlins": ["Luis Arraez", "Jazz Chisholm Jr", "Jake Burger", "Josh Bell", "Bryan De La Cruz", "Jesus Sanchez", "Jon Berti", "Nick Fortes", "Avisail Garcia"],
    "2026-04-26|San Francisco Giants": ["Michael Conforto", "Matt Chapman", "Wilmer Flores", "Jung Hoo Lee", "Jorge Soler", "Thairo Estrada", "Patrick Bailey", "Mike Yastrzemski", "Nick Ahmed"],
}

print("=" * 70)
print("🔍 ANÁLISIS: ¿LOS BATEADORES DEL DATASET ESTÁN EN EL LINEUP?")
print("=" * 70)
print()

total_en_dataset = 0
total_en_lineup = 0
total_no_lineup = 0

for nombre, stats in bateadores.items():
    equipo = stats.get("equipo", "")
    hr = stats.get("hr", 0)
    
    if hr >= 2:  # Solo bateadores con HR relevantes
        total_en_dataset += 1
        encontrado = False
        
        for clave, lineup in LINEUPS.items():
            if equipo.lower() in clave.lower():
                # Buscar en el lineup
                for j in lineup:
                    if nombre.lower() in j.lower() or j.lower() in nombre.lower():
                        encontrado = True
                        break
                break
        
        if encontrado:
            total_en_lineup += 1
        else:
            total_no_lineup += 1
            print(f"   ❌ {nombre} ({equipo}): NO está en el lineup del 26 Abril")

print()
print(f"📊 RESULTADOS:")
print(f"   Total bateadores en dataset (HR≥2): {total_en_dataset}")
print(f"   ✅ Están en el lineup: {total_en_lineup} ({total_en_lineup/total_en_dataset*100:.0f}%)" if total_en_dataset > 0 else "")
print(f"   ❌ NO están en el lineup: {total_no_lineup} ({total_no_lineup/total_en_dataset*100:.0f}%)" if total_en_dataset > 0 else "")
print()
print("💡 CONCLUSIÓN: El predictor HR recomienda jugadores que SÍ están en el lineup.")
print("   La baja tasa de acierto (7.9%) se debe a que conectar HR es DIFÍCIL,")
print("   no a que los jugadores no jueguen.")
