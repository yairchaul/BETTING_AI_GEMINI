# -*- coding: utf-8 -*-
import unicodedata, json, os

def normalizar(texto):
    if not texto: return ""
    texto = unicodedata.normalize('NFD', texto)
    texto = texto.encode('ascii', 'ignore').decode("utf-8")
    return texto.lower().replace(".", "").replace("-", "").strip()

def super_match(nombre_dataset, nombre_lineup):
    """Compara nombres ignorando formato (Judge, A. = Aaron Judge)"""
    n1 = normalizar(nombre_dataset)
    n2 = normalizar(nombre_lineup)
    if n1 == n2: return True
    palabras = n1.split()
    for p in palabras:
        if len(p) > 3 and p in n2: return True
        if len(p) > 3 and n2 in p: return True
    return False

# ==================== FILTROS ====================
def verificar_lineup(nombre, equipo, fecha, lineups_db):
    """Verifica si el jugador está en el lineup del día"""
    for clave, lineup in lineups_db.items():
        if fecha in clave and equipo.lower() in clave.lower():
            for j in lineup:
                if super_match(nombre, j):
                    return True
    return False

def ajustar_por_pitcher(prob_bateador, pitcher_nombre, pitchers_db):
    """Ajusta probabilidad según el pitcher rival"""
    if pitcher_nombre not in pitchers_db:
        return prob_bateador
    
    p = pitchers_db[pitcher_nombre]
    hr9 = p.get("hr_por_juego", 1.0)
    
    factor = 1.0
    if hr9 > 1.5:    factor = 1.25  # Pitcher vulnerable: +25%
    elif hr9 > 1.2:  factor = 1.15  # Algo vulnerable: +15%
    elif hr9 < 0.8:  factor = 0.85  # Pitcher elite: -15%
    elif hr9 < 0.6:  factor = 0.70  # Super elite: -30%
    
    return round(min(92, prob_bateador * factor), 1)

# ==================== PRUEBA ====================
if __name__ == "__main__":
    # Cargar datos
    with open("hr_datasets_completos.json", "r", encoding="utf-8") as f:
        hr_data = json.load(f)
    bateadores = hr_data.get("bateadores", {})
    pitchers = hr_data.get("pitchers", {})
    
    print("=" * 70)
    print("🧠 PREDICTOR HR V5 - PRUEBA DE FILTROS")
    print("=" * 70)
    print()
    
    # Lineups de prueba (26 Abril)
    lineups = {
        "2026-04-26|Los Angeles Dodgers": ["Shohei Ohtani", "Mookie Betts", "Freddie Freeman"],
        "2026-04-26|New York Yankees": ["Aaron Judge", "Juan Soto", "Giancarlo Stanton"],
    }
    
    # Probar con bateadores
    pruebas = [
        ("Aaron Judge", "NYY", "2026-04-26", "Gerrit Cole"),
        ("Shohei Ohtani", "LAD", "2026-04-26", "Logan Webb"),
        ("Spencer Torkelson", "DET", "2026-04-26", "Tanner Bibee"),
        ("Mike Trout", "LAA", "2026-04-26", "Pablo Lopez"),
    ]
    
    for nombre, equipo, fecha, pitcher_rival in pruebas:
        prob_base = bateadores.get(nombre, {}).get("hr_por_juego", 0) * 100
        en_lineup = verificar_lineup(nombre, equipo, fecha, lineups)
        prob_ajustada = ajustar_por_pitcher(prob_base, pitcher_rival, pitchers) if en_lineup else 0
        
        emoji = "✅" if en_lineup else "❌"
        print(f"{emoji} {nombre} ({equipo}):")
        print(f"   Prob base: {prob_base:.0f}%")
        print(f"   En lineup: {'SI' if en_lineup else 'NO'}")
        print(f"   Pitcher rival: {pitcher_rival}")
        print(f"   Prob ajustada: {prob_ajustada:.0f}%")
        print()
