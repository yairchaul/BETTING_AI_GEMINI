# test_system.py
import json
import os

print("\n" + "="*50)
print("   TEST DE CONEXIÓN DEL SISTEMA")
print("="*50)

errors = []

# 1. Test MLB
print("\n📋 1. MLB - Lanzadores y Candidatos HR")
mlb_file = "resultados_finales_corregidos.json"
if os.path.exists(mlb_file):
    with open(mlb_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    tbd_count = sum(1 for p in data if 'TBD' in str(p.get('pitchers', {})))
    print(f"   Partidos: {len(data)} | Pitchers TBD: {tbd_count}")
    if tbd_count > 0:
        errors.append("MLB: Hay pitchers TBD - ejecuta scraper_caliente_selenium.py")
else:
    errors.append("MLB: Archivo no encontrado")

# 2. Test NBA Radar
print("\n📋 2. NBA - Radar de Triples")
try:
    from scrapers.balldontlie_client import balldontlie
    teams = balldontlie.get_players()
    print(f"   Conectado: {len(teams.get('data', []))} jugadores")
    from scrapers.nba_com_scraper import NBAComScraper # Corrected import path
    scraper = NBAComScraper()
    players = scraper.get_players_stats()
    print(f"   NBA.com Scraper: {len(players)} jugadores obtenidos.")
except Exception as e:
    errors.append(f"NBA: {e}")
    errors.append(f"NBA: Error con NBA.com Scraper: {e}")

# 3. Test UFC
print("\n📋 3. UFC - Datos de Peleadores")
try:
    from scrapers.ufc_stats_scraper import UFCStatsScraper
    scraper = UFCStatsScraper()
    test_fighter = "Alex Perez"
    stats = scraper.get_fighter_stats(test_fighter)
    print(f"   {test_fighter}: Record {stats.get('record', 'N/A')}")
    if stats.get('record') == '0-0-0':
        errors.append("UFC: Datos no cargados correctamente")
except Exception as e:
    errors.append(f"UFC: {e}")

# 4. Test Fútbol
print("\n📋 4. Fútbol - Historial")
try:
    import sqlite3
    conn = sqlite3.connect("data/betting_stats.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM historial_equipos WHERE deporte='soccer'")
    count = cursor.fetchone()[0]
    print(f"   Registros históricos: {count}")
    conn.close()
except Exception as e:
    errors.append(f"Fútbol: {e}")

print("\n" + "="*50)
if errors:
    print("❌ ERRORES DETECTADOS:")
    for e in errors:
        print(f"   • {e}")
else:
    print("✅ TODOS LOS SISTEMAS FUNCIONAN CORRECTAMENTE")
print("="*50)
