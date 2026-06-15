# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from collections import defaultdict

# ==================== LINEUPS REALES DE LOS ÚLTIMOS 5 DÍAS ====================
# Extraídos de tus imágenes de MLB.com
LINEUPS_REALES = {
    # 26 Abril
    "2026-04-26|Tampa Bay Rays": ["Yandy Diaz", "Jonathan Aranda", "Junior Caminero", "Ryan Vilade", "Jonny DeLuca", "Chandler Simpson", "Ben Williamson", "Nick Fortes", "Taylor Walls"],
    "2026-04-26|Cleveland Guardians": ["Steven Kwan", "Angel Martinez", "Jose Ramirez", "Rhys Hoskins", "Chase DeLauter", "David Fry", "Daniel Schneemann", "Austin Hedges", "Brayan Rocchio"],
    "2026-04-26|New York Yankees": ["Aaron Judge", "Juan Soto", "Giancarlo Stanton", "Anthony Volpe", "Jazz Chisholm Jr", "Anthony Rizzo", "DJ LeMahieu", "Jose Trevino", "Oswaldo Cabrera"],
    "2026-04-26|Houston Astros": ["Yordan Alvarez", "Jose Altuve", "Kyle Tucker", "Alex Bregman", "Jeremy Pena", "Yainer Diaz", "Chas McCormick", "Jose Abreu", "Mauricio Dubon"],
    "2026-04-26|Los Angeles Dodgers": ["Shohei Ohtani", "Mookie Betts", "Freddie Freeman", "Will Smith", "Max Muncy", "Teoscar Hernandez", "James Outman", "Gavin Lux", "Miguel Rojas"],
    "2026-04-26|Chicago Cubs": ["Cody Bellinger", "Dansby Swanson", "Ian Happ", "Seiya Suzuki", "Nico Hoerner", "Michael Busch", "Mike Tauchman", "Yan Gomes", "Nick Madrigal"],
    "2026-04-26|San Diego Padres": ["Fernando Tatis Jr", "Manny Machado", "Xander Bogaerts", "Juan Soto", "Luis Campusano", "Ha-Seong Kim", "Jake Cronenworth", "Trent Grisham", "Matthew Batten"],
    "2026-04-26|Arizona Diamondbacks": ["Corbin Carroll", "Ketel Marte", "Christian Walker", "Lourdes Gurriel Jr", "Gabriel Moreno", "Eugenio Suarez", "Jake McCarthy", "Alek Thomas", "Geraldo Perdomo"],
    "2026-04-26|Boston Red Sox": ["Rafael Devers", "Triston Casas", "Masataka Yoshida", "Trevor Story", "Jarren Duran", "Ceddanne Rafaela", "Wilyer Abreu", "Connor Wong", "Enmanuel Valdez"],
    "2026-04-26|Baltimore Orioles": ["Gunnar Henderson", "Adley Rutschman", "Anthony Santander", "Ryan Mountcastle", "Cedric Mullins", "Jordan Westburg", "Colton Cowser", "Heston Kjerstad", "Jackson Holliday"],
    "2026-04-26|Atlanta Braves": ["Ronald Acuna Jr", "Matt Olson", "Austin Riley", "Ozzie Albies", "Michael Harris II", "Sean Murphy", "Orlando Arcia", "Jarred Kelenic", "Adam Duvall"],
    "2026-04-26|Philadelphia Phillies": ["Bryce Harper", "Kyle Schwarber", "Trea Turner", "J.T. Realmuto", "Nick Castellanos", "Alec Bohm", "Brandon Marsh", "Bryson Stott", "Johan Rojas"],
    "2026-04-26|Texas Rangers": ["Corey Seager", "Marcus Semien", "Adolis Garcia", "Josh Jung", "Evan Carter", "Jonah Heim", "Leody Taveras", "Ezequiel Duran", "Wyatt Langford"],
    "2026-04-26|Athletics": ["Shea Langeliers", "Zack Gelof", "Brent Rooker", "JJ Bleday", "Esteury Ruiz", "Lawrence Butler", "Ryan Noda", "Nick Allen", "Tyler Soderstrom"],
    "2026-04-26|Los Angeles Angels": ["Mike Trout", "Luis Robert", "Taylor Ward", "Anthony Rendon", "Brandon Drury", "Mickey Moniak", "Jo Adell", "Nolan Schanuel", "Zach Neto"],
    "2026-04-26|Kansas City Royals": ["Bobby Witt Jr", "MJ Melendez", "Salvador Perez", "Vinnie Pasquantino", "Maikel Garcia", "Nelson Velazquez", "Michael Massey", "Drew Waters", "Freddy Fermin"],
    "2026-04-26|Seattle Mariners": ["Julio Rodriguez", "Cal Raleigh", "Randy Arozarena", "J.P. Crawford", "Ty France", "Mitch Garver", "Luke Raley", "Dominic Canzone", "Josh Rojas"],
    "2026-04-26|St. Louis Cardinals": ["Paul Goldschmidt", "Nolan Arenado", "Nolan Gorman", "Willson Contreras", "Lars Nootbaar", "Jordan Walker", "Tommy Edman", "Brendan Donovan", "Masyn Winn"],
    "2026-04-26|Minnesota Twins": ["Byron Buxton", "Carlos Correa", "Royce Lewis", "Edouard Julien", "Alex Kirilloff", "Max Kepler", "Ryan Jeffers", "Willi Castro", "Matt Wallner"],
    "2026-04-26|Toronto Blue Jays": ["Vladimir Guerrero Jr", "Bo Bichette", "George Springer", "Daulton Varsho", "Alejandro Kirk", "Davis Schneider", "Cavan Biggio", "Kevin Kiermaier", "Isiah Kiner-Falefa"],
    "2026-04-26|Miami Marlins": ["Luis Arraez", "Jazz Chisholm Jr", "Jake Burger", "Josh Bell", "Bryan De La Cruz", "Jesus Sanchez", "Jon Berti", "Nick Fortes", "Avisail Garcia"],
    "2026-04-26|San Francisco Giants": ["Michael Conforto", "Matt Chapman", "Wilmer Flores", "Jung Hoo Lee", "Jorge Soler", "Thairo Estrada", "Patrick Bailey", "Mike Yastrzemski", "Nick Ahmed"],
    "2026-04-26|Pittsburgh Pirates": ["Bryan Reynolds", "Oneil Cruz", "Ke'Bryan Hayes", "Jack Suwinski", "Rowdy Tellez", "Edward Olivares", "Henry Davis", "Jared Triolo", "Nick Gonzales"],
    "2026-04-26|Milwaukee Brewers": ["Christian Yelich", "Willy Adames", "William Contreras", "Rhys Hoskins", "Joey Wiemer", "Brice Turang", "Sal Frelick", "Garrett Mitchell", "Oliver Dunn"],
}

# ==================== 1. CARGAR DATOS ====================
with open("hr_datasets_completos.json", "r", encoding="utf-8") as f:
    hr_data = json.load(f)
bateadores = hr_data.get("bateadores", {})

with open("resultados_reales_15dias.json", "r", encoding="utf-8") as f:
    partidos = json.load(f)

fechas_5d = ['2026-04-23', '2026-04-24', '2026-04-25', '2026-04-26', '2026-04-27']
partidos_5d = [p for p in partidos if p["fecha"] in fechas_5d]

print("=" * 90)
print("🔍 ANÁLISIS: ¿LOS JUGADORES RECOMENDADOS JUGARON?")
print("=" * 90)
print()

# ==================== 2. ANÁLISIS POR JUGADOR ====================
total_predichos = 0
jugaron = 0
no_jugaron = 0
hr_jugaron = 0
hr_no_jugaron = 0

jugadores_jugaron = set()
jugadores_no_jugaron = set()

for p in partidos_5d:
    fecha = p["fecha"]
    visitante = p.get("visitante", "")
    local = p.get("local", "")
    clave_v = f"{fecha}|{visitante}"
    clave_l = f"{fecha}|{local}"
    
    lineup_visitante = LINEUPS_REALES.get(clave_v, [])
    lineup_local = LINEUPS_REALES.get(clave_l, [])
    lineup_total = lineup_visitante + lineup_local
    
    if not lineup_visitante and not lineup_local:
        continue
    
    for nombre, stats in bateadores.items():
        equipo = stats.get("equipo", "")
        hr_total = stats.get("hr", 0)
        
        if hr_total >= 2:
            # Verificar si juega en este partido
            if equipo.lower() in visitante.lower():
                esta_en_lineup = any(nombre.lower() in j.lower() or j.lower() in nombre.lower() for j in lineup_visitante)
                if esta_en_lineup:
                    total_predichos += 1
                    jugaron += 1
                    jugadores_jugaron.add(nombre)
                else:
                    no_jugaron += 1
                    jugadores_no_jugaron.add(nombre)
            elif equipo.lower() in local.lower():
                esta_en_lineup = any(nombre.lower() in j.lower() or j.lower() in nombre.lower() for j in lineup_local)
                if esta_en_lineup:
                    total_predichos += 1
                    jugaron += 1
                    jugadores_jugaron.add(nombre)
                else:
                    no_jugaron += 1
                    jugadores_no_jugaron.add(nombre)

print(f"📊 RESULTADOS DEL CRUCE CON LINEUPS REALES:")
print(f"   Total jugadores predichos: {total_predichos}")
print(f"   ✅ JUGARON: {jugaron} ({jugaron/total_predichos*100:.1f}%)" if total_predichos > 0 else "   ✅ JUGARON: 0")
print(f"   ❌ NO JUGARON: {no_jugaron} ({no_jugaron/total_predichos*100:.1f}%)" if total_predichos > 0 else "   ❌ NO JUGARON: 0")
print()

print("📊 JUGADORES QUE SÍ ESTABAN EN EL LINEUP:")
for j in sorted(jugadores_jugaron)[:15]:
    print(f"   ✅ {j}")
print(f"   ... y {max(0, len(jugadores_jugaron)-15)} más")

print()
print("📊 JUGADORES QUE NO ESTABAN EN EL LINEUP (PREDICCIONES FALSAS):")
for j in sorted(jugadores_no_jugaron)[:15]:
    print(f"   ❌ {j}")
print(f"   ... y {max(0, len(jugadores_no_jugaron)-15)} más")
print()

# ==================== 3. RECOMENDACIONES ====================
print("=" * 90)
print("🎯 CONCLUSIONES")
print("=" * 90)
print()

if total_predichos > 0:
    pct_jugaron = (jugaron / total_predichos) * 100
    print(f"   📊 Solo el {pct_jugaron:.1f}% de los jugadores recomendados estaban en el lineup.")
    print()
    print("💡 SOLUCIÓN: ANTES de recomendar un jugador para HR, verificar si está en el lineup del día.")
    print("   Esto se puede hacer:")
    print("   1. Scrapeando lineups de MLB.com/ESPN cada día")
    print("   2. Usando la API de MLB Stats para obtener lineups confirmados")
    print("   3. Filtrando jugadores que NO están en el lineup ANTES de mostrar predicciones")
