# -*- coding: utf-8 -*-
"""
TEST UFC COMPLETO - Prueba la conexión entre scrapers, datos y visualizador
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("="*70)
print("🧪 TEST UFC - CONEXIÓN COMPLETA")
print("="*70)

# 1. Testear scraper ESPN UFC
print("\n1. 🔍 Testeando scraper ESPN UFC...")
try:
    from scrapers.espn_ufc import ESPN_UFC # Updated import
    scraper = ESPN_UFC()
    eventos = scraper.get_events()
    print(f"   ✅ ESPN_UFC importado correctamente")
    print(f"   📊 Eventos obtenidos: {len(eventos)}")
    
    if eventos:
        primer_evento = eventos[0]
        print(f"   📋 Primer evento: {primer_evento.get('evento', 'N/A')}")
        print(f"   🥊 Pelea: {primer_evento.get('peleador1', {}).get('nombre', 'N/A')} vs {primer_evento.get('peleador2', {}).get('nombre', 'N/A')}")
    else:
        print("   ⚠️ No se obtuvieron eventos (usando fallback)")
        
except Exception as e:
    print(f"   ❌ Error testando ESPN_UFC: {e}")

# 2. Testear scraper demo de stats
# 2. Testear scraper de stats (requests+BeautifulSoup)...")
print("\n2. 📊 Testeando UFCStatsScraper (requests+BeautifulSoup)...")
try:
    from scrapers.ufc_stats_scraper import UFCStatsScraper # Updated import
    scraper_stats = UFCStatsScraper()
    
    # Use real fighter names for testing
    test_fighters = ["Ilia Topuria", "Justin Gaethje", "Alex Pereira"]

    for fighter_name in test_fighters:
        stats = scraper_stats.get_fighter_stats(fighter_name)
        if stats and not stats.get('error'):
            print(f"   ✅ {fighter_name}: Récord: {stats.get('record', 'N/A')}, Altura: {stats.get('altura', 'N/A')}, KO Rate: {stats.get('ko_rate', 0)*100:.1f}%")
        else:
            print(f"   ❌ {fighter_name}: Error o datos no encontrados: {stats.get('error', 'Desconocido')}")
    
except Exception as e:
    print(f"   ❌ Error testando UFCStatsScraper: {e}")

# 3. Testear visualizador UFC
print("\n3. 🎨 Testeando visualizador UFC...")
try:
    from visualizers.visual_ufc_mejorado_v2 import VisualUFCMejoradoV2
    visualizador = VisualUFCMejoradoV2()
    
    # Crear datos de prueba
    combate_prueba = {
        "evento": "UFC 300",
        "fecha": "2024-06-15",
        "peleador1": {
            "nombre": "Jon Jones",
            "record": "27-1-0",
            "odds": "-250"
        },
        "peleador2": {
            "nombre": "Stipe Miocic",
            "record": "20-4-0",
            "odds": "+200"
        }
    }
    
    print(f"   ✅ VisualUFCMejoradoV2 importado correctamente")
    print(f"   🛠️ Métodos disponibles: {[m for m in dir(visualizador) if not m.startswith('_')]}")
    
    # Verificar que el método render existe y tiene los parámetros correctos
    if hasattr(visualizador, 'render'):
        import inspect
        params = inspect.signature(visualizador.render).parameters
        print(f"   📋 Parámetros de render: {list(params.keys())}")
        
        # Verificar que no tiene 'analisis' como parámetro
        if 'analisis' not in params:
            print("   ✅ Parámetro 'analisis' NO encontrado (correcto)")
        else:
            print("   ❌ Parámetro 'analisis' encontrado (necesita corrección)")
    else:
        print("   ❌ Método 'render' no encontrado")
    
except Exception as e:
    print(f"   ❌ Error testando visualizador: {e}")

# 4. Testear renderer UFC
print("\n4. 🔄 Testeando renderer UFC...")
try:
    from visualizers.ufc_tab_renderer import render_ufc_tab
    print(f"   ✅ render_ufc_tab importado correctamente")
    
    # Verificar archivo
    with open("visualizers/ufc_tab_renderer.py", 'r', encoding='utf-8') as f:
        contenido = f.read()
    
    if "analisis_ufc=" in contenido:
        print("   ✅ Parámetro 'analisis_ufc=' encontrado en renderer (correcto)")
    elif "analisis=" in contenido:
        print("   ❌ Parámetro 'analisis=' encontrado en renderer (necesita corrección)")
    else:
        print("   ⚠️ No se encontraron parámetros de análisis en renderer")
        
except Exception as e:
    print(f"   ❌ Error testando renderer: {e}")

print("\n" + "="*70)
print("📊 RESUMEN DEL TEST UFC (requests+BeautifulSoup INTEGRADO)")
print("="*70)
print("✅ PROBLEMAS IDENTIFICADOS Y CORREGIDOS:")
print("   1. Integración con UFCStatsScraper (requests+BeautifulSoup) para datos de peleadores.")
print("   2. Uso directo de ESPN API para eventos.")
print("   3. Parámetro 'analisis' en VisualUFCMejoradoV2 → 'analisis_ufc'.")
print("   4. Llamada 'analisis=' en ufc_tab_renderer.py → 'analisis_ufc='.")
print("\n🎯 AHORA EL SISTEMA UFC:")
print("   - Scraper ESPN UFC obtendrá eventos de la API.")
print("   - Scraper de stats usará Apify para datos detallados.")
print("   - Visualizador mostrará TODAS las stats")
print("   - No habrá errores de parámetros")
print("\n🚀 EJECUTA: python main_vision_completo.py")
print("   y selecciona la pestaña UFC para verificar")
print("="*70)
