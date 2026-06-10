# -*- coding: utf-8 -*-
"""
TEST DE INTEGRACIÓN MLB - Verificación Completa
Prueba que todos los componentes MLB estén correctamente conectados
"""

import sys
import os
from datetime import datetime

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test 1: Verificar que todos los imports funcionen"""
    print("\n" + "="*70)
    print("TEST 1: VERIFICANDO IMPORTS MLB")
    print("="*70)
    
    try:
        from motors import analizar_mlb_pro_v20 as analizar_mlb
        print("[OK] analizar_mlb importado correctamente")
    except Exception as e:
        print(f"[FAIL] Error importando analizar_mlb: {e}")
        return False
    
    try:
        from motors.motor_over_under import MotorOverUnder
        print("[OK] MotorOverUnder importado correctamente")
    except Exception as e:
        print(f"[FAIL] Error importando MotorOverUnder: {e}")
        return False
    
    try:
        from motors.predictor_hr import predictor_hr
        print("[OK] predictor_hr importado correctamente")
    except Exception as e:
        print(f"[FAIL] Error importando predictor_hr: {e}")
        return False
    
    try:
        from motors.predictor_ponches import predictor_ponches
        print("[OK] predictor_ponches importado correctamente")
    except Exception as e:
        print(f"[FAIL] Error importando predictor_ponches: {e}")
        return False
    
    try:
        from utils.clima_mlb import ClimaMLB
        print("[OK] ClimaMLB importado correctamente")
    except Exception as e:
        print(f"[FAIL] Error importando ClimaMLB: {e}")
        return False
    
    return True

def test_motor_over_under():
    """Test 2: Verificar que MotorOverUnder tenga el método correcto"""
    print("\n" + "="*70)
    print("TEST 2: VERIFICANDO MOTOR OVER/UNDER")
    print("="*70)
    
    try:
        from motors.motor_over_under import MotorOverUnder
        motor = MotorOverUnder()
        
        # Verificar que tenga el método calcular_total
        if hasattr(motor, 'calcular_total'):
            print("[OK] Método 'calcular_total' existe")
        else:
            print("[FAIL] Método 'calcular_total' NO existe")
            print(f"   Métodos disponibles: {[m for m in dir(motor) if not m.startswith('_')]}")
            return False
        
        # Probar con datos de ejemplo
        partido_test = {
            'local': 'New York Yankees',
            'visitante': 'Boston Red Sox',
            'venue': 'Yankee Stadium',
            'pitchers': {
                'local': {'era': 3.50, 'nombre': 'Test Pitcher'},
                'visitante': {'era': 4.20, 'nombre': 'Test Pitcher 2'}
            },
            'clima': {
                'temp': 75,
                'wind_speed': 10,
                'wind_dir': 'In'
            }
        }
        
        resultado = motor.calcular_total(partido_test)
        print(f"[OK] calcular_total() ejecutado correctamente")
        print(f"   Proyección total: {resultado.get('proyeccion_total', 'N/A')}")
        print(f"   Recomendación: {resultado.get('recomendacion', 'N/A')}")
        
        return True
    except Exception as e:
        print(f"[FAIL] Error en MotorOverUnder: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_predictor_hr():
    """Test 3: Verificar PredictorHR"""
    print("\n" + "="*70)
    print("TEST 3: VERIFICANDO PREDICTOR DE HOME RUNS")
    print("="*70)
    
    try:
        from motors.predictor_hr import predictor_hr
        
        # Verificar métodos clave
        metodos_requeridos = ['obtener_predicciones_para_equipo', 'analizar_partido', 'obtener_bateadores_activos']
        for metodo in metodos_requeridos:
            if hasattr(predictor_hr, metodo):
                print(f"[OK] Método '{metodo}' existe")
            else:
                print(f"[FAIL] Método '{metodo}' NO existe")
                print(f"   Métodos disponibles: {[m for m in dir(predictor_hr) if not m.startswith('_')]}")
                return False
        
        # Probar análisis básico
        resultado = predictor_hr.obtener_predicciones_para_equipo('New York Yankees', game_pk=None)
        print(f"[OK] obtener_predicciones_para_equipo() ejecutado correctamente")
        print(f"   Predicciones encontradas: {len(resultado) if isinstance(resultado, list) else 0}")
        
        return True
    except Exception as e:
        print(f"[FAIL] Error en PredictorHR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_predictor_ponches():
    """Test 4: Verificar Predictor de Ponches"""
    print("\n" + "="*70)
    print("TEST 4: VERIFICANDO PREDICTOR DE STRIKEOUTS")
    print("="*70)
    
    try:
        from motors.predictor_ponches import predictor_ponches
        
        # Verificar método principal
        if hasattr(predictor_ponches, 'predecir_ponches_pitcher'):
            print("[OK] Método 'predecir_ponches_pitcher' existe")
        else:
            print("[FAIL] Método 'predecir_ponches_pitcher' NO existe")
            print(f"   Métodos disponibles: {[m for m in dir(predictor_ponches) if not m.startswith('_')]}")
            return False
        
        # Probar predicción
        resultado = predictor_ponches.predecir_ponches_pitcher(
            'Test Pitcher',
            'Boston Red Sox',
            5.5  # Línea O/U
        )
        print(f"[OK] predecir_ponches_pitcher() ejecutado correctamente")
        print(f"   Proyección: {resultado.get('k_proyectados', 'N/A')} ponches")
        print(f"   Recomendación: {resultado.get('recomendacion', 'N/A')}")
        
        return True
    except Exception as e:
        print(f"[FAIL] Error en PredictorPonches: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_clima_mlb():
    """Test 5: Verificar ClimaMLB"""
    print("\n" + "="*70)
    print("TEST 5: VERIFICANDO CLIMA MLB")
    print("="*70)
    
    try:
        from utils.clima_mlb import ClimaMLB
        clima = ClimaMLB()
        
        # Verificar método
        if hasattr(clima, 'obtener_clima'):
            print("[OK] Método 'obtener_clima' existe")
        else:
            print("[FAIL] Método 'obtener_clima' NO existe")
            return False
        
        # Probar obtención de clima (solo 1 parámetro: estadio)
        resultado = clima.obtener_clima('Yankee Stadium')
        print(f"[OK] obtener_clima() ejecutado correctamente")
        print(f"   Temperatura: {resultado.get('temp', 'N/A')}°F")
        print(f"   Viento: {resultado.get('wind_speed', 'N/A')}mph {resultado.get('wind_dir', 'N/A')}")
        
        return True
    except Exception as e:
        print(f"[FAIL] Error en ClimaMLB: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_integracion_completa():
    """Test 6: Prueba de integración completa"""
    print("\n" + "="*70)
    print("TEST 6: INTEGRACIÓN COMPLETA MLB")
    print("="*70)
    
    try:
        from motors import analizar_mlb_pro_v20 as analizar_mlb
        from motors.motor_over_under import MotorOverUnder
        from motors.predictor_hr import predictor_hr
        from motors.predictor_ponches import predictor_ponches
        from utils.clima_mlb import ClimaMLB
        
        # Partido de prueba completo
        partido = {
            'local': 'New York Yankees',
            'visitante': 'Boston Red Sox',
            'venue': 'Yankee Stadium',
            'estadio': 'Yankee Stadium',
            'fecha': datetime.now().strftime('%Y-%m-%d'),
            'game_pk': 123456,
            'pitchers': {
                'local': {'nombre': 'Gerrit Cole', 'era': 3.50, 'k9': 11.2, 'hr9': 0.9},
                'visitante': {'nombre': 'Chris Sale', 'era': 4.20, 'k9': 10.5, 'hr9': 1.2}
            }
        }
        
        print("\n1. Análisis Heurístico Base...")
        heur_res = analizar_mlb(partido, game_pk=partido['game_pk'])
        print(f"   [OK] Pick base: {heur_res.get('pick', 'N/A')}")
        
        print("\n2. Análisis de Home Runs...")
        hr_local = predictor_hr.obtener_predicciones_para_equipo(partido['local'], partido['game_pk'])
        hr_visit = predictor_hr.obtener_predicciones_para_equipo(partido['visitante'], partido['game_pk'])
        print(f"   [OK] HR Local: {len(hr_local)} candidatos")
        print(f"   [OK] HR Visitante: {len(hr_visit)} candidatos")
        
        print("\n3. Análisis de Strikeouts...")
        k_local = predictor_ponches.predecir_ponches_pitcher(
            partido['pitchers']['local']['nombre'], 
            partido['visitante'],
            5.5
        )
        k_visit = predictor_ponches.predecir_ponches_pitcher(
            partido['pitchers']['visitante']['nombre'], 
            partido['local'],
            5.5
        )
        print(f"   [OK] K Local: {k_local.get('k_proyectados', 'N/A')} proyectados")
        print(f"   [OK] K Visitante: {k_visit.get('k_proyectados', 'N/A')} proyectados")
        
        print("\n4. Análisis de Clima...")
        clima_mlb = ClimaMLB()
        clima = clima_mlb.obtener_clima(partido['estadio'])
        print(f"   [OK] Clima obtenido: {clima.get('temp', 'N/A')}°F, Viento {clima.get('wind_speed', 'N/A')}mph")
        
        print("\n5. Análisis Over/Under...")
        motor_ou = MotorOverUnder()
        partido['clima'] = clima  # Agregar clima al partido
        ou_analysis = motor_ou.calcular_total(partido)
        print(f"   [OK] Proyección O/U: {ou_analysis.get('proyeccion_total', 'N/A')} carreras")
        print(f"   [OK] Recomendación: {ou_analysis.get('recomendacion', 'N/A')}")
        
        print("\n" + "="*70)
        print("[OK] INTEGRACIÓN COMPLETA EXITOSA")
        print("="*70)
        return True
        
    except Exception as e:
        print(f"\n[FAIL] Error en integración completa: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_all_tests():
    """Ejecuta todos los tests"""
    print("\n" + "="*70)
    print(" "*15 + "TEST DE INTEGRACIÓN MLB V24.5.1")
    print("="*70)
    
    tests = [
        ("Imports", test_imports),
        ("Motor O/U", test_motor_over_under),
        ("Predictor HR", test_predictor_hr),
        ("Predictor K", test_predictor_ponches),
        ("Clima MLB", test_clima_mlb),
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
    print("\n" + "="*70)
    print(" "*25 + "RESUMEN FINAL")
    print("="*70)
    
    total = len(resultados)
    aprobados = sum(1 for _, r in resultados if r)
    
    for nombre, resultado in resultados:
        status = "OK" if resultado else "FAIL"
        print(f"  [{status}]  {nombre}")
    
    print("="*70)
    print(f"  Total: {aprobados}/{total} tests aprobados")
    print("="*70)
    
    return aprobados == total

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
