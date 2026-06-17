# -*- coding: utf-8 -*-
"""
FÚTBOL PROPS — Probabilidad de que un jugador ANOTE en el partido.

Modelo: P(anota >=1) = 1 - e^(-tasa_goles_por_partido)  (Poisson), ajustado por
localía. Mismo enfoque que el de Home Runs. Usa un dataset curado de goleadores
top (selecciones del Mundial + clubes top). Si la DB tiene datos en vivo se usan.
"""
import math

# (nombre, equipo, goles_por_partido aprox temporada/selección)
_GOLEADORES = {
    # ── Selecciones ──
    "France": [("Kylian Mbappé", 0.72), ("Olivier Giroud", 0.45), ("Antoine Griezmann", 0.40)],
    "Argentina": [("Lionel Messi", 0.60), ("Lautaro Martínez", 0.50), ("Julián Álvarez", 0.45)],
    "Brazil": [("Vinicius Junior", 0.45), ("Rodrygo", 0.40), ("Raphinha", 0.42)],
    "England": [("Harry Kane", 0.68), ("Bukayo Saka", 0.40), ("Phil Foden", 0.38)],
    "Portugal": [("Cristiano Ronaldo", 0.62), ("Bruno Fernandes", 0.40), ("Rafael Leão", 0.38)],
    "Spain": [("Álvaro Morata", 0.45), ("Lamine Yamal", 0.40), ("Nico Williams", 0.38)],
    "Norway": [("Erling Haaland", 0.85)],
    "Belgium": [("Romelu Lukaku", 0.55), ("Kevin De Bruyne", 0.35)],
    "Netherlands": [("Memphis Depay", 0.50), ("Cody Gakpo", 0.42)],
    "Germany": [("Kai Havertz", 0.42), ("Jamal Musiala", 0.45), ("Florian Wirtz", 0.40)],
    "Egypt": [("Mohamed Salah", 0.70)],
    "Poland": [("Robert Lewandowski", 0.72)],
    "Uruguay": [("Darwin Núñez", 0.48), ("Federico Valverde", 0.35)],
    "Mexico": [("Santiago Giménez", 0.55), ("Raúl Jiménez", 0.42)],
    "United States": [("Christian Pulisic", 0.45), ("Folarin Balogun", 0.42)],
    "USA": [("Christian Pulisic", 0.45), ("Folarin Balogun", 0.42)],
    "Sweden": [("Alexander Isak", 0.55), ("Viktor Gyökeres", 0.70)],
    "Nigeria": [("Victor Osimhen", 0.62)],
    # ── Selecciones Mundial 2026 (cobertura completa, incl. equipos chicos) ──
    "South Korea": [("Son Heung-min", 0.50), ("Hwang Hee-chan", 0.30), ("Cho Gue-sung", 0.28)],
    "Korea Republic": [("Son Heung-min", 0.50), ("Hwang Hee-chan", 0.30)],
    "South Africa": [("Percy Tau", 0.30), ("Lyle Foster", 0.28)],
    "Czech Republic": [("Patrik Schick", 0.50), ("Adam Hložek", 0.28)],
    "Czechia": [("Patrik Schick", 0.50), ("Adam Hložek", 0.28)],
    "Canada": [("Jonathan David", 0.50), ("Cyle Larin", 0.35), ("Alphonso Davies", 0.25)],
    "Bosnia-Herzegovina": [("Edin Džeko", 0.45), ("Ermedin Demirović", 0.30)],
    "Bosnia & Herzegovina": [("Edin Džeko", 0.45), ("Ermedin Demirović", 0.30)],
    "Qatar": [("Almoez Ali", 0.50), ("Akram Afif", 0.40)],
    "Switzerland": [("Breel Embolo", 0.35), ("Xherdan Shaqiri", 0.30)],
    "Morocco": [("Youssef En-Nesyri", 0.40), ("Brahim Díaz", 0.30), ("Hakim Ziyech", 0.28)],
    "Haiti": [("Frantzdy Pierrot", 0.35)],
    "Scotland": [("Che Adams", 0.30), ("Scott McTominay", 0.30), ("John McGinn", 0.25)],
    "Paraguay": [("Miguel Almirón", 0.30), ("Antonio Sanabria", 0.30)],
    "Australia": [("Mitchell Duke", 0.30), ("Jackson Irvine", 0.25)],
    "Turkey": [("Arda Güler", 0.30), ("Kenan Yıldız", 0.30), ("Hakan Çalhanoğlu", 0.28)],
    "Türkiye": [("Arda Güler", 0.30), ("Kenan Yıldız", 0.30), ("Hakan Çalhanoğlu", 0.28)],
    "Turkiye": [("Arda Güler", 0.30), ("Kenan Yıldız", 0.30)],
    "Curacao": [("Tahith Chong", 0.25), ("Juninho Bacuna", 0.22)],
    "Curaçao": [("Tahith Chong", 0.25), ("Juninho Bacuna", 0.22)],
    "Japan": [("Kaoru Mitoma", 0.35), ("Takefusa Kubo", 0.30), ("Ayase Ueda", 0.30)],
    "Ivory Coast": [("Sébastien Haller", 0.40), ("Simon Adingra", 0.28)],
    "Ecuador": [("Enner Valencia", 0.40), ("Kendry Páez", 0.25)],
    "Tunisia": [("Youssef Msakni", 0.30), ("Wahbi Khazri", 0.28)],
    "Cape Verde": [("Ryan Mendes", 0.28), ("Garry Rodrigues", 0.25)],
    "Iran": [("Mehdi Taremi", 0.50), ("Sardar Azmoun", 0.40)],
    "New Zealand": [("Chris Wood", 0.45)],
    "Senegal": [("Sadio Mané", 0.45), ("Nicolas Jackson", 0.35), ("Boulaye Dia", 0.30)],
    "Algeria": [("Riyad Mahrez", 0.40), ("Islam Slimani", 0.30), ("Baghdad Bounedjah", 0.30)],
    "Austria": [("Marko Arnautović", 0.30), ("Marcel Sabitzer", 0.30), ("Michael Gregoritsch", 0.28)],
    "Jordan": [("Mousa Al-Tamari", 0.35), ("Yazan Al-Naimat", 0.28)],
    "DR Congo": [("Cédric Bakambu", 0.35), ("Yoane Wissa", 0.30), ("Silas Katompa", 0.28)],
    "Congo DR": [("Cédric Bakambu", 0.35), ("Yoane Wissa", 0.30)],
    "Uzbekistan": [("Eldor Shomurodov", 0.40)],
    "Colombia": [("Luis Díaz", 0.40), ("Jhon Durán", 0.35), ("James Rodríguez", 0.28)],
    "Croatia": [("Andrej Kramarić", 0.35), ("Ante Budimir", 0.30), ("Bruno Petković", 0.28)],
    "Ghana": [("Mohammed Kudus", 0.35), ("Iñaki Williams", 0.30), ("Jordan Ayew", 0.28)],
    "Panama": [("José Fajardo", 0.30), ("Ismael Díaz", 0.28)],
    "Saudi Arabia": [("Salem Al-Dawsari", 0.35), ("Firas Al-Buraikan", 0.30)],
    "Iraq": [("Aymen Hussein", 0.35), ("Ali Al-Hamadi", 0.28)],
    # ── Clubes top ──
    "Real Madrid": [("Kylian Mbappé", 0.75), ("Vinicius Junior", 0.50), ("Jude Bellingham", 0.45)],
    "Manchester City": [("Erling Haaland", 0.90), ("Phil Foden", 0.40)],
    "Bayern Munich": [("Harry Kane", 0.85), ("Jamal Musiala", 0.45)],
    "Inter Miami": [("Lionel Messi", 0.80), ("Luis Suárez", 0.55)],
    "Al Nassr": [("Cristiano Ronaldo", 0.85)],
    "Liverpool": [("Mohamed Salah", 0.75), ("Darwin Núñez", 0.45)],
    "Barcelona": [("Robert Lewandowski", 0.70), ("Lamine Yamal", 0.45)],
    "Arsenal": [("Bukayo Saka", 0.45), ("Kai Havertz", 0.42)],
    "Sporting CP": [("Viktor Gyökeres", 0.85)],
    "Napoli": [("Romelu Lukaku", 0.50)],
}


def _prob_anota(tasa, es_local):
    """P(anota >=1) por Poisson, +localía ligera."""
    factor = 1.08 if es_local else 1.0
    p = (1 - math.exp(-tasa * factor)) * 100
    return round(min(85, p))


def _buscar_equipo(nombre):
    if not nombre:
        return []
    ln = nombre.lower().strip()
    for k, v in _GOLEADORES.items():
        if k.lower() == ln or k.lower() in ln or ln in k.lower():
            return v
    return []


def obtener_goleadores_partido(local, visitante):
    """Props 'anota en el partido' de los jugadores clave de ambos equipos."""
    out = {"local": [], "visitante": []}
    for lado, equipo, es_local in (("local", local, True), ("visitante", visitante, False)):
        for nombre, tasa in _buscar_equipo(equipo)[:3]:
            out[lado].append({
                "jugador": nombre,
                "equipo": equipo,
                "tasa": tasa,
                "prob": _prob_anota(tasa, es_local),
                "pick": "Anota en el partido",
            })
        out[lado].sort(key=lambda x: x["prob"], reverse=True)
    return out
