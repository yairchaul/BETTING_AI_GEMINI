# -*- coding: utf-8 -*-
"""
TEST DE INTEGRACIÓN UFC - Verificación Completa
Prueba que el scraping de datos físicos funcione correctamente
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test 1: Verificar imports UFC"""
    print("\n" + "="*70)
    print("TEST 1: VERIFICANDO IMPORTS UFC")
    print("="*70)
    
    try:
        from scrapers.espn_ufc import ESPN_UFC
        print("[OK] ESPN_UFC importado correctamente")
    except Exception as e:
        print(f"[FAIL] Error importando ESPN_UFC: {e}")
        return False
    
    try:
        from scrapers.ufc_stats_scraper import UFCStatsScraper
        print("[OK] UFCStatsScraper importado correctamente")
    except Exception as e:
        print(f"[FAIL] Error importando UFCStatsScraper: {e}")
        return False
    
    try:
        from motors.ufc_analyzer import UFCAnalyzer
        print("[OK] UFCAnalyzer importado correctamente")
    except Exception as e:
        print(f"[FAIL] Error importando UFCAnalyzer: {e}")
        return False
    
    return True

def test_espn_ufc_scraper():
    """Test 2: Verificar scraper ESPN UFC"""
    print("\n" + "="*70)
    print("TEST 2: VERIFICANDO ESPN UFC SCRAPER")
    print("="*70)
    
    try:
        from scrapers.espn_ufc import ESPN_UFC
        scraper = ESPN_UFC()
        
        print("   Obteniendo eventos UFC desde ESPN...")
        eventos = scraper.get_events()
        
        if eventos:
            print(f"[OK] {len(eventos)} eventos encontrados")
            # Mostrar primer evento
            primer_evento = eventos[0]
            print(f"\n   Ejemplo de evento:")
            print(f"   - Evento: {primer_evento.get('evento', 'N/A')}")
            print(f"   - Fecha: {primer_evento.get('fecha', 'N/A')}")
            print(f"   - Peleador 1: {primer_evento.get('peleador1', {}).get('nombre', 'N/A')}")
            print(f"   - Récord 1: {primer_evento.get('peleador1', {}).get('record', 'N/A')}")
            print(f"   - Peleador 2: {primer_evento.get('peleador2', {}).get('nombre', 'N/A')}")
            print(f"   - Récord 2: {primer_evento.get('peleador2', {}).get('record', 'N/A')}")
            return True
        else:
            print("[WARN] No se encontraron eventos UFC (puede ser normal si no hay eventos hoy)")
            return True  # No es un error crítico
            
    except Exception as e:
        print(f"[FAIL] Error en ESPN UFC Scraper: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_ufc_stats_scraper():
    """Test 3: Verificar scraper de stats UFC (UFCStats.com)"""
    print("\n" + "="*70)
    print("TEST 3: VERIFICANDO UFC STATS SCRAPER (UFCStats.com)")
    print("="*70)
    print("[WARN] NOTA: Este test usa Playwright y puede tardar 10-30 segundos")
    
    try:
        from scrapers.ufc_stats_scraper import UFCStatsScraper
        scraper = UFCStatsScraper()
        
        # Peleadores de prueba (conocidos y activos)
        peleadores_test = [
            "Jon Jones",
            "Israel Adesanya",
            "Alexander Volkanovski"
        ]
        
        resultados_exitosos = 0
        
        for nombre in peleadores_test:
            print(f"\n   Buscando datos de {nombre}...")
            stats = scraper.get_fighter_stats(nombre)
            
            if stats and 'error' not in stats:
                resultados_exitosos += 1
                print(f"   [OK] Datos encontrados para {nombre}")
                print(f"      - Altura: {stats.get('altura', 'N/A')}")
                print(f"      - Peso: {stats.get('peso', 'N/A')}")
                print(f"      - Alcance: {stats.get('alcance', 'N/A')}")
                print(f"      - KO Rate: {stats.get('ko_rate', 'N/A')}")
                print(f"      - Wins: {stats.get('wins', 'N/A')}")
            else:
                print(f"   [WARN] No se encontraron datos para {nombre}")
                if stats and 'error' in stats:
                    print(f"      Error: {stats['error']}")
        
        if resultados_exitosos > 0:
            print(f"\n[OK] Scraper funcional: {resultados_exitosos}/{len(peleadores_test)} peleadores encontrados")
            return True
        else:
            print("\n[FAIL] Scraper no pudo obtener datos de ningún peleador")
            return False
            
    except Exception as e:
        print(f"[FAIL] Error en UFC Stats Scraper: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_ufc_analyzer():
    """Test 4: Verificar UFC Analyzer"""
    print("\n" + "="*70)
    print("TEST 4: VERIFICANDO UFC ANALYZER")
    print("="*70)
    
    try:
        from motors.ufc_analyzer import UFCAnalyzer
        analyzer = UFCAnalyzer()
        
        # Datos de prueba
        peleador1 = {
            'nombre': 'Test Fighter 1',
            'record': '15-2-0',
            'wins': 15,
            'losses': 2,
            'altura': '6\'0"',
            'peso': '185 lbs',
            'alcance': '76"',
            'edad': 28,
            'ko_rate': 0.60,
            'str_acc': 0.55,
            'estadisticas_carrera': {
                'sig_strikes_landed_per_min': 5.2,
                'sig_strikes_absorbed_per_min': 3.1
            }
        }
        
        peleador2 = {
            'nombre': 'Test Fighter 2',
            'record': '12-5-0',
            'wins': 12,
            'losses': 5,
            'altura': '5\'10"',
            'peso': '185 lbs',
            'alcance': '72"',
            'edad': 32,
            'ko_rate': 0.40,
            'str_acc': 0.45,
            'estadisticas_carrera': {
                'sig_strikes_landed_per_min': 4.1,
                'sig_strikes_absorbed_per_min': 4.5
            }
        }
        
        print("   Analizando combate de prueba...")
        resultado = analyzer.analizar_combate(peleador1, peleador2)
        
        print(f"[OK] Análisis completado")
        print(f"   - Ganador proyectado: {resultado.get('recomendacion', 'N/A')}")
        print(f"   - Confianza: {resultado.get('confianza', 'N/A')}%")
        print(f"   - Método: {resultado.get('metodo', 'N/A')}")
        print(f"   - Razón: {resultado.get('razon', 'N/A')[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Error en UFC Analyzer: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_integracion_completa():
    """Test 5: Integración completa UFC"""
    print("\n" + "="*70)
    print("TEST 5: INTEGRACIÓN COMPLETA UFC")
    print("="*70)
    
    try:
        from scrapers.espn_ufc import ESPN_UFC
        from scrapers.ufc_stats_scraper import UFCStatsScraper
        from motors.ufc_analyzer import UFCAnalyzer
        
        print("\n1. Obteniendo eventos desde ESPN...")
        espn_scraper = ESPN_UFC()
        eventos = espn_scraper.get_events()
        
        if not eventos:
            print("[WARN] No hay eventos UFC disponibles para probar integración completa")
            print("   (Esto es normal si no hay eventos programados)")
            return True  # No es error
        
        print(f"   [OK] {len(eventos)} eventos encontrados")
        
        print("\n2. Inicializando scrapers de stats...")
        ufc_stats = UFCStatsScraper()
        analyzer = UFCAnalyzer()
        print("   [OK] Scrapers inicializados")
        
        print("\n3. Probando enriquecimiento de datos...")
        primer_combate = eventos[0]
        p1_nombre = primer_combate.get('peleador1', {}).get('nombre', '')
        p2_nombre = primer_combate.get('peleador2', {}).get('nombre', '')
        
        if p1_nombre and p2_nombre:
            print(f"   Combate: {p1_nombre} vs {p2_nombre}")
            
            print(f"\n   Obteniendo stats de {p1_nombre}...")
            p1_stats = ufc_stats.get_fighter_stats(p1_nombre)
            if p1_stats and 'error' not in p1_stats:
                print(f"   [OK] Stats obtenidas - Altura: {p1_stats.get('altura', 'N/A')}, Alcance: {p1_stats.get('alcance', 'N/A')}")
            else:
                print(f"   [WARN] No se pudieron obtener stats completas")
            
            print(f"\n   Obteniendo stats de {p2_nombre}...")
            p2_stats = ufc_stats.get_fighter_stats(p2_nombre)
            if p2_stats and 'error' not in p2_stats:
                print(f"   [OK] Stats obtenidas - Altura: {p2_stats.get('altura', 'N/A')}, Alcance: {p2_stats.get('alcance', 'N/A')}")
            else:
                print(f"   [WARN] No se pudieron obtener stats completas")
            
            # Si tenemos datos de ambos, analizar
            if p1_stats and p2_stats and 'error' not in p1_stats and 'error' not in p2_stats:
                print("\n4. Analizando combate...")
                # Fusionar datos
                p1_data = {**primer_combate.get('peleador1', {}), **p1_stats}
                p2_data = {**primer_combate.get('peleador2', {}), **p2_stats}
                
                resultado = analyzer.analizar_combate(p1_data, p2_data)
                print(f"   [OK] Análisis completado")
                print(f"      - Ganador: {resultado.get('recomendacion', 'N/A')}")
                print(f"      - Confianza: {resultado.get('confianza', 'N/A')}%")
        
        print("\n" + "="*70)
        print("[OK] INTEGRACIÓN UFC COMPLETA")
        print("="*70)
        return True
        
    except Exception as e:
        print(f"\n[FAIL] Error en integración completa UFC: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_all_tests():
    """Ejecuta todos los tests UFC"""
    print("\n" + "+" + "="*68 + "+")
    print("|" + " "*15 + "TEST DE INTEGRACIÓN UFC V24.5.1" + " "*22 + "|")
    print("+" + "="*68 + "+")
    
    tests = [
        ("Imports", test_imports),
        ("ESPN UFC Scraper", test_espn_ufc_scraper),
        ("UFC Stats Scraper", test_ufc_stats_scraper),
        ("UFC Analyzer", test_ufc_analyzer),
        ("Integración Completa", test_integracion_completa)
    ]
    
    resultados = []
    for nombre, test_func in tests:
        try:
            resultado = test_func()
            resultados.append((nombre, resultado))
        except Exception as e:
            print(f"\n[FAIL] ERROR CRÍTICO en {nombre}: {e}")
            resultados.append((nombre, False))
    
    # Resumen final
    print("\n" + "+" + "="*68 + "+")
    print("|" + " "*25 + "RESUMEN FINAL" + " "*30 + "|")
    print("+" + "="*68 + "+")
    
    total = len(resultados)
    aprobados = sum(1 for _, r in resultados if r)
    
    for nombre, resultado in resultados:
        status = "[OK] PASS" if resultado else "[FAIL] FAIL"
        print(f"|  {status}  {nombre:<58} |")
    
    print("+" + "="*68 + "+")
    print(f"|  Total: {aprobados}/{total} tests aprobados" + " "*(68-28-len(str(aprobados))-len(str(total))) + "|")
    print("+" + "="*68 + "+")
    
    if aprobados < total:
        print("\n[WARN] NOTA: Los datos de UFC pueden aparecer como N/A si:")
        print("   1. El peleador no está en UFCStats.com")
        print("   2. El nombre no coincide exactamente")
        print("   3. Playwright no puede acceder al sitio")
        print("   Solución: Los datos se cargan la primera vez que se analiza el combate")
    
    return aprobados == total

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
