# -*- coding: utf-8 -*-
"""
SCRIPT DE VALIDACIÓN DE DATOS UFC
Verifica la integridad y conexión de los datos de UFC, desde el scraper de eventos
hasta el scraper de estadísticas de peleadores.
"""
import sys
import os

# Añadir la raíz del proyecto al path para poder importar módulos
if __name__ == '__main__':
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

def validate_ufc_data_flow():
    """Función principal para ejecutar todas las validaciones de UFC."""
    print("--- INICIANDO VALIDACIÓN DE DATOS UFC ---")

    # 1. Verificar Scraper de Eventos (ESPN)
    print("\n[Paso 1: Verificación del Scraper de Eventos - ESPN_UFC]")
    try:
        from scrapers.espn_ufc import ESPN_UFC
        espn_scraper = ESPN_UFC()
        eventos = espn_scraper.get_events()
        if not eventos:
            print("  ⚠️  ADVERTENCIA: No se encontraron eventos. El scraper podría estar usando datos de fallback.")
            # No retornamos para poder seguir validando el scraper de stats
        else:
            print(f"  ✅ Scraper de eventos OK ({len(eventos)} combates encontrados).")
            primer_combate = eventos[0]
            p1_nombre = primer_combate.get('peleador1', {}).get('nombre', 'N/A')
            p2_nombre = primer_combate.get('peleador2', {}).get('nombre', 'N/A')
            print(f"  🥊 Combate de prueba: {p1_nombre} vs {p2_nombre}")

    except Exception as e:
        print(f"  ❌ ERROR CRÍTICO: No se pudo inicializar o ejecutar ESPN_UFC: {e}")
        return

    # 2. Verificar Scraper de Estadísticas
    print("\n[Paso 2: Verificación del Scraper de Estadísticas - UFCStatsScraper]")
    try:
        from scrapers.ufc_stats_scraper import UFCStatsScraper
        stats_scraper = UFCStatsScraper()
        # Probar con un peleador conocido para ver si la API responde
        stats_test = stats_scraper.get_fighter_stats("Jon Jones")
        if not stats_test or 'altura' not in stats_test:
            print("  ❌ ERROR: El scraper de estadísticas no devolvió datos válidos para 'Jon Jones'.")
            return
        print("  ✅ Scraper de estadísticas OK (responde correctamente).")

    except Exception as e:
        print(f"  ❌ ERROR CRÍTICO: No se pudo inicializar o ejecutar UFCStatsScraper: {e}")
        return

    # 3. Verificar Conexión entre Scrapers (si se obtuvieron eventos)
    if 'p1_nombre' in locals() and p1_nombre != 'N/A':
        print("\n[Paso 3: Verificación de la Conexión de Datos (Evento -> Stats)]")
        print(f"  🔍 Buscando estadísticas para '{p1_nombre}' del primer combate...")
        stats_p1 = stats_scraper.get_fighter_stats(p1_nombre)
        if stats_p1 and 'altura' in stats_p1 and stats_p1['altura'] != 'N/A':
            print(f"    ✅ ¡ÉXITO! Se encontraron estadísticas completas para {p1_nombre}.")
            print(f"      -> Altura: {stats_p1['altura']}, Alcance: {stats_p1['alcance']}, Record: {stats_p1.get('record', 'N/A')}")
        else:
            print(f"    ❌ FALLO: No se encontraron estadísticas para {p1_nombre}. Revisa el nombre o la cobertura del scraper.")
    else:
        print("\n[Paso 3: Verificación de la Conexión de Datos (Evento -> Stats)]")
        print("  ⚠️  No se puede verificar la conexión porque no se obtuvo un nombre de peleador válido en el Paso 1.")

    print("\n--- ✅ VALIDACIÓN DE UFC COMPLETADA ---")

if __name__ == "__main__":
    validate_ufc_data_flow()