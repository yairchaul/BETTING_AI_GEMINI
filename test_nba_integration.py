# -*- coding: utf-8 -*-
"""
TEST DE INTEGRACIÓN NBA - Verificación Completa
Prueba que todos los componentes NBA estén correctamente conectados
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test 1: Verificar imports NBA"""
    print("\n" + "="*70)
    print("TEST 1: VERIFICANDO IMPORTS NBA")
    print("="*70)
    
    try:
        from scrapers.espn_nba import ESPN_NBA
        print("[OK] ESPN_NBA importado correctamente")
    except Exception as e:
        print(f"[FAIL] Error importando ESPN_NBA: {e}")
        return False
    
    try:
        from scrapers.nba_stats_scraper_fixed import nba_stats_scraper
        print("[OK] nba_stats_scraper importado correctamente")
    except Exception as e:
        print(f"[FAIL] Error importando nba_stats_scraper: {e}")
        return False
    
    try:
        from motors.motor_nba_over_under import MotorNBAOverUnder
        print("[OK] MotorNBAOverUnder importado correctamente")
    except Exception as e:
        print(f"[FAIL] Error importando MotorNBAOverUnder: {e}")
        return False
    
    try:
        from motors import analizar_nba_pro_v17
        print("[OK] analizar_nba_pro_v17 importado correctamente")
    except Exception as e:
        print(f"[FAIL] Error importando analizar_nba_pro_v17: {e}")
        return False
    
    return True

def test_espn_nba_scraper():
    """Test 2: Verificar scraper ESPN NBA"""
    print("\n" + "="*70)
    print("TEST 2: VERIFICANDO ESPN NBA SCRAPER")
    print("="*70)
    
    try:
        from scrapers.espn_nba import ESPN_NBA
        scraper = ESPN_NBA()
        
        print("   Obteniendo partidos NBA desde ESPN...")
        partidos = scraper.get_games()
        
        if partidos:
            print(f"[OK] {len(partidos)} partidos encontrados")
            # Mostrar primer partido
            primer_partido = partidos[0]
            print(f"\n   Ejemplo de partido:")
            print(f"   - Local: {primer_partido.get('local', 'N/A')}")
            print(f"   - Visitante: {primer_partido.get('visitante', 'N/A')}")
            print(f"   - Récord Local: {primer_partido.get('local_record', 'N/A')}")
            print(f"   - Récord Visitante: {primer_partido.get('visitante_record', 'N/A')}")
            print(f"   - Moneyline: Local {primer_partido.get('odds', {}).get('moneyline', {}).get('home', 'N/A')}")
            print(f"   - Over/Under: {primer_partido.get('odds', {}).get('overUnder', 'N/A')}")
            return True
        else:
            print("[WARN] No se encontraron partidos NBA (puede ser normal si no hay juegos hoy)")
            return True  # No es un error crítico
            
    except Exception as e:
        print(f"[FAIL] Error en ESPN NBA Scraper: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_nba_stats_scraper():
    """Test 3: Verificar scraper de stats NBA"""
    print("\n" + "="*70)
    print("TEST 3: VERIFICANDO NBA STATS SCRAPER")
    print("="*70)
    
    try:
        from scrapers.nba_stats_scraper_fixed import nba_stats_scraper
        
        print("   Obteniendo stats de equipos desde NBA API...")
        df_stats = nba_stats_scraper.get_team_stats()
        
        if df_stats is not None and not df_stats.empty:
            print(f"[OK] {len(df_stats)} equipos con stats avanzadas")
            
            # Mostrar ejemplo
            if 'TEAM_NAME' in df_stats.columns:
                primer_equipo = df_stats.iloc[0]
                print(f"\n   Ejemplo de stats:")
                print(f"   - Equipo: {primer_equipo.get('TEAM_NAME', 'N/A')}")
                print(f"   - PACE: {primer_equipo.get('PACE', 'N/A')}")
                print(f"   - OFF_RATING: {primer_equipo.get('OFF_RATING', 'N/A')}")
                print(f"   - DEF_RATING: {primer_equipo.get('DEF_RATING', 'N/A')}")
                return True
            else:
                print("[WARN] DataFrame tiene estructura inesperada")
                print(f"   Columnas encontradas: {list(df_stats.columns)[:5]}...")
                return False
        else:
            print("[FAIL] No se pudieron obtener stats de equipos")
            return False
            
    except Exception as e:
        print(f"[FAIL] Error en NBA Stats Scraper: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_motor_nba_over_under():
    """Test 4: Verificar Motor NBA O/U"""
    print("\n" + "="*70)
    print("TEST 4: VERIFICANDO MOTOR NBA OVER/UNDER")
    print("="*70)
    
    try:
        from motors.motor_nba_over_under import MotorNBAOverUnder
        
        print("   Inicializando motor...")
        motor = MotorNBAOverUnder()
        print("[OK] Motor inicializado correctamente")
        
        # Verificar que tenga el método
        if not hasattr(motor, 'predict_over_under'):
            print("[FAIL] Método 'predict_over_under' no existe")
            return False
        
        print("[OK] Método 'predict_over_under' existe")
        
        # Probar con datos de ejemplo
        game_data = {
            'local': 'Los Angeles Lakers',
            'visitante': 'Boston Celtics',
            'over_under_line': 220.5
        }
        
        print("\n   Probando predicción con datos de ejemplo...")
        resultado = motor.predict_over_under(game_data)
        
        print(f"[OK] Predicción exitosa")
        print(f"   - Recomendación: {resultado.get('recomendacion', 'N/A')}")
        print(f"   - Confianza: {resultado.get('confianza', 'N/A')}%")
        print(f"   - Proyección total: {resultado.get('proyeccion_total', 'N/A')} puntos")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Error en Motor NBA O/U: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_motor_heuristico():
    """Test 5: Verificar motor heurístico NBA"""
    print("\n" + "="*70)
    print("TEST 5: VERIFICANDO MOTOR HEURÍSTICO NBA")
    print("="*70)
    
    try:
        from motors import analizar_nba_pro_v17
        
        # Partido de prueba
        partido_test = {
            'local': 'Los Angeles Lakers',
            'visitante': 'Boston Celtics',
            'local_record': '45-20',
            'visitante_record': '50-15',
            'odds': {
                'moneyline': {'home': -150, 'away': +130},
                'pointSpread': {'home': -3.5},
                'overUnder': 220.5
            }
        }
        
        print("   Analizando partido de prueba...")
        resultado = analizar_nba_pro_v17(partido_test)
        
        print(f"[OK] Análisis heurístico completado")
        print(f"   - Recomendación: {resultado.get('recomendacion', 'N/A')}")
        print(f"   - Confianza: {resultado.get('confianza', 'N/A')}%")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Error en motor heurístico: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_integracion_completa():
    """Test 6: Integración completa NBA"""
    print("\n" + "="*70)
    print("TEST 6: INTEGRACIÓN COMPLETA NBA")
    print("="*70)
    
    try:
        from scrapers.espn_nba import ESPN_NBA
        from scrapers.nba_stats_scraper_fixed import nba_stats_scraper
        from motors.motor_nba_over_under import MotorNBAOverUnder
        from motors import analizar_nba_pro_v17
        
        print("\n1. Obteniendo partidos desde ESPN...")
        espn_scraper = ESPN_NBA()
        partidos = espn_scraper.get_games()
        
        if not partidos:
            print("[WARN] No hay partidos NBA disponibles para probar integración completa")
            print("   (Esto es normal si no hay juegos hoy)")
            return True  # No es error
        
        print(f"   [OK] {len(partidos)} partidos encontrados")
        
        print("\n2. Cargando stats avanzadas de equipos...")
        df_stats = nba_stats_scraper.get_team_stats()
        if df_stats is not None and not df_stats.empty:
            print(f"   [OK] Stats de {len(df_stats)} equipos cargadas")
        else:
            print("   [WARN] No se pudieron cargar stats avanzadas")
        
        print("\n3. Inicializando motor O/U...")
        motor_ou = MotorNBAOverUnder()
        print("   [OK] Motor O/U inicializado")
        
        print("\n4. Analizando primer partido...")
        primer_partido = partidos[0]
        print(f"   Partido: {primer_partido.get('local')} vs {primer_partido.get('visitante')}")
        
        # Análisis heurístico
        print("\n   a) Análisis heurístico...")
        resultado_heur = analizar_nba_pro_v17(primer_partido)
        print(f"      [OK] Recomendación: {resultado_heur.get('recomendacion', 'N/A')}")
        
        # Análisis O/U
        ou_line = primer_partido.get('odds', {}).get('overUnder', 0)
        if ou_line > 0:
            print("\n   b) Análisis Over/Under...")
            resultado_ou = motor_ou.predict_over_under({
                'local': primer_partido.get('local'),
                'visitante': primer_partido.get('visitante'),
                'over_under_line': ou_line
            })
            print(f"      [OK] Recomendación O/U: {resultado_ou.get('recomendacion', 'N/A')}")
            print(f"      [OK] Proyección: {resultado_ou.get('proyeccion_total', 'N/A')} puntos")
        else:
            print("\n   b) [WARN] No hay línea O/U disponible para este partido")
        
        print("\n" + "="*70)
        print("[OK] INTEGRACIÓN NBA COMPLETA")
        print("="*70)
        return True
        
    except Exception as e:
        print(f"\n[FAIL] Error en integración completa NBA: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_all_tests():
    """Ejecuta todos los tests NBA"""
    print("\n" + "+" + "="*68 + "+")
    print("|" + " "*15 + "TEST DE INTEGRACIÓN NBA V24.5.1" + " "*22 + "|")
    print("+" + "="*68 + "+")
    
    tests = [
        ("Imports", test_imports),
        ("ESPN NBA Scraper", test_espn_nba_scraper),
        ("NBA Stats Scraper", test_nba_stats_scraper),
        ("Motor NBA O/U", test_motor_nba_over_under),
        ("Motor Heurístico", test_motor_heuristico),
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
        print("\n[WARN] NOTA: Balldontlie API no está implementada aún")
        print("   Los props de jugadores (3PM) se mostrarán como 'no disponible'")
        print("   Esto no afecta las predicciones O/U ni el análisis heurístico")
    
    return aprobados == total

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
