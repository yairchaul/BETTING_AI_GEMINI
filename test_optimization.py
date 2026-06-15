"""
Test del Sistema de Optimización de Tokens
"""

import sys
import os

# Agregar directorio actual al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from optimization.manager import optimization_manager
from optimization.integration import (
    get_mlb_analysis_optimized,
    get_todays_picks_optimized,
    get_system_metrics,
    clear_optimization_cache,
    warmup_optimization_system,
    debug_optimization_query
)


def test_basic_queries():
    """Prueba consultas básicas."""
    print("🧪 TEST 1: Consultas básicas")
    print("=" * 50)
    
    # Consulta 1: Picks MLB hoy
    print("\n1. Consultando 'picks mlb hoy'...")
    response1 = optimization_manager.process_query("picks mlb hoy")
    print(f"   Tipo: {response1.get('_meta', {}).get('query_type', 'unknown')}")
    print(f"   Cache: {'SÍ' if response1.get('from_cache') else 'NO'}")
    print(f"   Tokens estimados: {len(str(response1)) // 2}")
    
    # Consulta 2: Análisis específico
    print("\n2. Consultando 'análisis Yankees vs Red Sox'...")
    response2 = optimization_manager.process_query("análisis Yankees vs Red Sox")
    print(f"   Tipo: {response2.get('_meta', {}).get('query_type', 'unknown')}")
    print(f"   Cache: {'SÍ' if response2.get('from_cache') else 'NO'}")
    
    # Consulta 3: Ayuda
    print("\n3. Consultando 'ayuda'...")
    response3 = optimization_manager.process_query("ayuda")
    print(f"   Tipo: {response3.get('_meta', {}).get('query_type', 'unknown')}")
    print(f"   Longitud respuesta: {len(str(response3))} caracteres")
    
    print("\n" + "=" * 50)


def test_integration_functions():
    """Prueba funciones de integración."""
    print("\n🧪 TEST 2: Funciones de integración")
    print("=" * 50)
    
    # Test análisis MLB optimizado
    print("\n1. Probando get_mlb_analysis_optimized()...")
    mlb_analysis = get_mlb_analysis_optimized(
        game_data={'local': 'Red Sox', 'visitante': 'Yankees'}
    )
    print(f"   Resultado: {mlb_analysis.get('response_type', 'unknown')}")
    print(f"   Source: {mlb_analysis.get('source', 'unknown')}")
    
    # Test picks del día
    print("\n2. Probando get_todays_picks_optimized()...")
    picks = get_todays_picks_optimized('mlb')
    print(f"   Picks encontrados: {len(picks.get('picks', []))}")
    print(f"   Sport: {picks.get('sport', 'unknown')}")
    
    # Test métricas del sistema
    print("\n3. Probando get_system_metrics()...")
    metrics = get_system_metrics()
    print(f"   Sistema activo: {metrics.get('optimization_system', {}).get('status') == 'active'}")
    
    print("\n" + "=" * 50)


def test_cache_operations():
    """Prueba operaciones de caché."""
    print("\n🧪 TEST 3: Operaciones de caché")
    print("=" * 50)
    
    # Obtener estadísticas antes
    stats_before = optimization_manager.get_system_stats()
    print(f"Cache hits antes: {stats_before.get('cache_hits', 0)}")
    print(f"Cache misses antes: {stats_before.get('cache_misses', 0)}")
    
    # Hacer consultas repetidas para probar cache
    print("\n1. Haciendo consultas repetidas...")
    for i in range(3):
        response = optimization_manager.process_query("picks mlb hoy")
        cache_status = "CACHE" if response.get('from_cache') else "LIVE"
        print(f"   Intento {i+1}: {cache_status}")
    
    # Obtener estadísticas después
    stats_after = optimization_manager.get_system_stats()
    print(f"\nCache hits después: {stats_after.get('cache_hits', 0)}")
    print(f"Cache misses después: {stats_after.get('cache_misses', 0)}")
    
    # Limpiar caché
    print("\n2. Limpiando caché...")
    clear_result = clear_optimization_cache()
    print(f"   Resultado: {'Éxito' if clear_result.get('success') else 'Fallo'}")
    
    print("\n" + "=" * 50)


def test_debug_function():
    """Prueba función de debugging."""
    print("\n🧪 TEST 4: Función de debugging")
    print("=" * 50)
    
    debug_info = debug_optimization_query(
        "análisis Dodgers vs Giants",
        {'test': True}
    )
    
    print(f"Query: {debug_info.get('query')}")
    print(f"From cache: {debug_info.get('from_cache', False)}")
    print(f"Cache key: {debug_info.get('cache_key', 'N/A')}")
    
    # Mostrar logs (primeras líneas)
    logs = debug_info.get('logs', '')
    if logs:
        log_lines = logs.strip().split('\n')
        print(f"\nLogs ({len(log_lines)} líneas):")
        for line in log_lines[:5]:  # Primeras 5 líneas
            print(f"   {line}")
    
    print("\n" + "=" * 50)


def test_system_health():
    """Prueba salud del sistema."""
    print("\n🧪 TEST 5: Salud del sistema")
    print("=" * 50)
    
    health = optimization_manager.health_check()
    
    print(f"Estado general: {health.get('status', 'unknown')}")
    
    print("\nComponentes:")
    for component, info in health.get('components', {}).items():
        status = info.get('status', 'unknown')
        print(f"   {component}: {status}")
    
    print("\nProblemas detectados:")
    issues = health.get('issues', [])
    if issues:
        for issue in issues:
            print(f"   • {issue}")
    else:
        print("   Ninguno ✓")
    
    print("\n" + "=" * 50)


def run_all_tests():
    """Ejecuta todas las pruebas."""
    print("🚀 INICIANDO PRUEBAS DEL SISTEMA DE OPTIMIZACIÓN")
    print("=" * 60)
    
    try:
        # Precalentar sistema
        print("\n🔥 Precalentando sistema...")
        warmup_result = warmup_optimization_system()
        if warmup_result.get('success'):
            print("   Sistema precalentado exitosamente")
        else:
            print(f"   Error precalentando: {warmup_result.get('error')}")
        
        # Ejecutar pruebas
        test_basic_queries()
        test_integration_functions()
        test_cache_operations()
        test_debug_function()
        test_system_health()
        
        # Resumen final
        print("\n📊 RESUMEN FINAL")
        print("=" * 60)
        
        stats = optimization_manager.get_system_stats()
        total_queries = stats.get('total_queries', 0)
        cache_hits = stats.get('cache_hits', 0)
        
        if total_queries > 0:
            hit_rate = (cache_hits / total_queries) * 100
        else:
            hit_rate = 0
        
        print(f"Total consultas procesadas: {total_queries}")
        print(f"Cache hits: {cache_hits} ({hit_rate:.1f}%)")
        print(f"Cache misses: {stats.get('cache_misses', 0)}")
        print(f"Tiempo promedio: {stats.get('avg_processing_time', 0):.3f}s")
        print(f"Tokens ahorrados: {stats.get('total_tokens_saved', 0)}")
        print(f"Agentes cargados: {', '.join(stats.get('loaded_agents', []))}")
        
        print("\n✅ Todas las pruebas completadas exitosamente!")
        
    except Exception as e:
        print(f"\n❌ Error durante las pruebas: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()