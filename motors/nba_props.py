# -*- coding: utf-8 -*-
"""
NBA PROPS — Props de jugador (Puntos / Asistencias / Triples) con Over/Under.

Genera líneas y recomendación por jugador a partir de promedios de temporada
2024-25. La línea sugerida va medio punto por debajo del promedio (estándar de
sportsbook) y la confianza depende de la consistencia/volumen del jugador.

Fuente de datos: promedios 2024-25 (estáticos, verificables). Si la DB tiene
datos en vivo (player_stats nba) se usan primero.
"""

# Top jugadores por equipo: (nombre, PPG puntos, APG asistencias, 3PM triples, RPG rebotes)
_NBA_PLAYERS = {
    "Oklahoma City Thunder": [("Shai Gilgeous-Alexander", 30.1, 6.2, 2.1, 5.5), ("Chet Holmgren", 16.5, 2.0, 1.5, 8.7)],
    "Denver Nuggets": [("Nikola Jokic", 27.0, 10.2, 1.2, 12.7), ("Jamal Murray", 21.4, 6.0, 2.6, 4.0)],
    "Milwaukee Bucks": [("Giannis Antetokounmpo", 30.4, 6.5, 0.5, 11.9), ("Damian Lillard", 24.6, 7.1, 3.1, 4.4)],
    "Dallas Mavericks": [("Luka Doncic", 28.1, 7.8, 3.5, 8.2), ("Kyrie Irving", 24.7, 4.6, 2.9, 4.6)],
    "Los Angeles Lakers": [("Luka Doncic", 28.1, 7.8, 3.5, 8.2), ("LeBron James", 24.4, 8.2, 2.1, 7.8), ("Austin Reaves", 20.2, 5.8, 2.4, 4.5)],
    "Boston Celtics": [("Jayson Tatum", 26.8, 5.9, 3.2, 8.7), ("Jaylen Brown", 22.2, 4.5, 2.4, 5.8)],
    "Phoenix Suns": [("Devin Booker", 25.6, 6.9, 2.5, 4.1), ("Kevin Durant", 26.6, 4.2, 2.2, 6.0)],
    "Philadelphia 76ers": [("Tyrese Maxey", 26.3, 6.1, 3.0, 3.6), ("Joel Embiid", 23.8, 4.5, 1.2, 8.8)],
    "New York Knicks": [("Jalen Brunson", 26.0, 7.3, 2.1, 2.9), ("Karl-Anthony Towns", 24.4, 3.1, 2.0, 12.8)],
    "Cleveland Cavaliers": [("Donovan Mitchell", 24.0, 5.0, 3.0, 4.5), ("Evan Mobley", 18.5, 3.2, 0.8, 9.3)],
    "Minnesota Timberwolves": [("Anthony Edwards", 27.6, 4.5, 4.1, 5.7), ("Rudy Gobert", 12.0, 1.5, 0.0, 10.9)],
    "Atlanta Hawks": [("Trae Young", 24.2, 11.6, 2.2, 3.1), ("Jalen Johnson", 18.9, 5.0, 1.6, 10.0)],
    "Sacramento Kings": [("DeMar DeRozan", 22.2, 4.4, 0.7, 3.9), ("Domantas Sabonis", 19.1, 6.0, 0.6, 13.9)],
    "Golden State Warriors": [("Stephen Curry", 24.5, 6.0, 4.4, 4.4), ("Jimmy Butler", 17.0, 5.5, 1.0, 5.9)],
    "Indiana Pacers": [("Tyrese Haliburton", 18.6, 9.2, 2.5, 3.5), ("Pascal Siakam", 20.2, 3.4, 1.2, 7.0)],
    "Houston Rockets": [("Jalen Green", 21.0, 3.4, 2.5, 4.6), ("Alperen Sengun", 19.1, 4.9, 0.4, 10.3)],
    "Memphis Grizzlies": [("Ja Morant", 23.2, 7.3, 1.5, 4.1), ("Jaren Jackson Jr", 22.2, 2.0, 1.9, 5.6)],
    "Los Angeles Clippers": [("James Harden", 21.8, 8.5, 2.9, 5.8), ("Ivica Zubac", 16.8, 2.7, 0.0, 12.6)],
    "Orlando Magic": [("Paolo Banchero", 25.9, 4.8, 1.4, 7.5), ("Franz Wagner", 24.0, 4.7, 1.5, 5.7)],
    "Detroit Pistons": [("Cade Cunningham", 26.1, 9.1, 2.0, 6.1), ("Jalen Duren", 12.0, 2.5, 0.0, 10.3)],
    "Miami Heat": [("Tyler Herro", 23.9, 5.5, 3.0, 5.2), ("Bam Adebayo", 18.1, 4.3, 0.6, 9.6)],
    "San Antonio Spurs": [("Victor Wembanyama", 24.3, 3.7, 2.0, 11.0), ("De'Aaron Fox", 23.5, 6.1, 1.5, 4.0)],
    "Chicago Bulls": [("Coby White", 20.4, 4.5, 2.9, 3.7), ("Nikola Vucevic", 18.5, 3.5, 1.8, 10.1)],
    "Portland Trail Blazers": [("Anfernee Simons", 19.3, 4.8, 3.0, 2.6), ("Deni Avdija", 16.9, 3.9, 1.6, 7.3)],
    "Toronto Raptors": [("Scottie Barnes", 19.3, 5.8, 1.6, 7.6), ("RJ Barrett", 21.1, 5.4, 1.8, 6.5)],
    "Brooklyn Nets": [("Cam Thomas", 24.0, 3.8, 2.5, 3.3), ("Nic Claxton", 10.0, 2.1, 0.0, 9.4)],
    "Charlotte Hornets": [("LaMelo Ball", 25.2, 7.4, 3.5, 4.9), ("Miles Bridges", 20.0, 3.2, 1.5, 7.3)],
    "Utah Jazz": [("Lauri Markkanen", 19.0, 1.9, 2.4, 6.0), ("Walker Kessler", 11.1, 1.5, 0.0, 11.9)],
    "Washington Wizards": [("Jordan Poole", 20.5, 4.5, 2.6, 2.9), ("Alex Sarr", 13.0, 2.4, 1.1, 6.5)],
    "New Orleans Pelicans": [("Zion Williamson", 24.6, 5.3, 0.2, 7.2), ("Brandon Ingram", 22.2, 5.6, 1.6, 5.6)],
}


def _confianza_prop(promedio, tipo):
    """Confianza del Over/Under según el volumen (jugadores de alto volumen son más estables)."""
    if tipo == "puntos":
        return 58 if promedio >= 25 else 55 if promedio >= 18 else 52
    if tipo == "asistencias":
        return 57 if promedio >= 7 else 54 if promedio >= 4 else 51
    if tipo == "rebotes":
        return 58 if promedio >= 10 else 55 if promedio >= 7 else 52
    return 56 if promedio >= 3 else 53 if promedio >= 2 else 51  # triples


def _prob_doble_doble(ppg, apg, rpg):
    """Probabilidad de doble-doble (10+ en dos categorías)."""
    # Cuenta cuántas categorías están cerca/arriba de 10
    cerca = sum(1 for v in (ppg, apg, rpg) if v >= 8.5)
    altas = sum(1 for v in (ppg, apg, rpg) if v >= 10)
    if altas >= 2:
        return 72  # ya promedia doble-doble
    if altas == 1 and cerca >= 2:
        return 55  # una categoría segura + otra cercana
    if cerca >= 2:
        return 42
    return 0


def _props_jugador(nombre, ppg, apg, tpm, rpg=0):
    """Genera props (puntos, rebotes, asistencias, triples) + doble-doble."""
    props = []
    for tipo, prom in (("puntos", ppg), ("rebotes", rpg), ("asistencias", apg), ("triples", tpm)):
        if prom <= 0:
            continue
        linea = round(prom - 1.5) if tipo == "puntos" else round(prom - 0.5, 1)
        linea = max(0.5, linea)
        props.append({
            "jugador": nombre, "tipo": tipo, "promedio": prom,
            "linea": linea, "prediccion": "OVER",
            "pick": f"{tipo.capitalize()} OVER {linea}",
            "confianza": _confianza_prop(prom, tipo),
        })
    # Doble-doble
    prob_dd = _prob_doble_doble(ppg, apg, rpg)
    if prob_dd >= 40:
        props.append({
            "jugador": nombre, "tipo": "doble-doble", "promedio": 0,
            "linea": "", "prediccion": "SÍ", "pick": "Doble-doble SÍ",
            "confianza": prob_dd,
        })
    return props


def obtener_props_partido(local, visitante, db=None):
    """Props de los jugadores top de ambos equipos para un partido NBA."""
    resultado = {"local": [], "visitante": []}
    for lado, equipo in (("local", local), ("visitante", visitante)):
        jugadores = []
        # 1. DB en vivo (si hay)
        if db is not None:
            try:
                top = db.get_top_player_stat(equipo, "points", limit=2, deporte="nba")
                if top:
                    for p in (top if isinstance(top, list) else [top]):
                        jugadores.append((p.get("nombre", "?"), p.get("puntos", 0),
                                          p.get("asistencias", 0), p.get("triples_por_partido", 0),
                                          p.get("rebotes", 0)))
            except Exception:
                pass
        # 2. Dataset estático
        if not jugadores:
            for key, lista in _NBA_PLAYERS.items():
                if key.lower() in (equipo or "").lower() or (equipo or "").lower() in key.lower():
                    jugadores = lista
                    break
        for jug in jugadores[:3]:
            # Soportar tuplas de 4 (sin rebotes) o 5 elementos
            nombre, ppg, apg, tpm = jug[0], jug[1], jug[2], jug[3]
            rpg = jug[4] if len(jug) > 4 else 0
            resultado[lado].extend(_props_jugador(nombre, ppg, apg, tpm, rpg))
    return resultado
