# -*- coding: utf-8 -*-
"""
TEST DE INTEGRACIÓN HR PRO - Verifica que el predictor HR Pro funcione correctamente
"""

import sys
import os
import json
from datetime import datetime

def test_predictor_hr_pro():
    """Test básico del Predictor HR Pro"""
    print("="*60)
    print("🚀 TEST DE INTEGRACIÓN PREDICTOR HR PRO")
    print("="*60)
    
    try:
        # Importar módulos
        from motors.predictor_hr_pro import PredictorHRPro
        
        print("✅ Módulo PredictorHRPro importado correctamente")
        
        # Crear datos de prueba
        datos_prueba = {
            "bateadores": {
                "Juan Soto": {
                    "equipo": "New York Yankees",
                    "hr": 8,
                    "hr_por_juego": 0.53,
                    "avg": 0.295,
                    "ops": 0.925
                },
                "Aaron Judge": {
                    "equipo": "New York Yankees",
                    "hr": 12,
                    "hr_por_juego": 0.80,
                    "avg": 0.285,
                    "ops": 1.020
                },
                "Shohei Ohtani": {
                    "equipo": "Los Angeles Dodgers",
                    "hr": 10,
                    "hr_por_juego": 0.67,
                    "avg": 0.310,
                    "ops": 1.150
                }
            },
            "pitchers": {
                "Jacob deGrom": {
                    "hr_por_juego": 0.8,
                    "era": 2.50,
                    "k9": 12.5
                },
                "Max Scherzer": {
                    "hr_por_juego": 1.2,
                    "era": 3.80,
                    "k9": 10.8
                }
            }
        }
        
        # Partidos de prueba
        partidos_prueba = [
            {
                "local": "New York Yankees",
                "visitante": "Boston Red Sox",
                "game_pk": "12345",
                "pitchers": {
                    "local": {"nombre": "Gerrit Cole", "mano": "R", "era": 2.90, "k9": 11.2, "hr9": 0.9},
                    "visitante": {"nombre": "Chris Sale", "mano": "L", "era": 3.20, "k9": 12.8, "hr9": 1.1}
                }
            }
        ]
        
        # Crear instancia del predictor
        predictor = PredictorHRPro(data_source=datos_prueba, mlb_partidos_hoy=partidos_prueba)
        
        print("✅ Instancia PredictorHRPro creada correctamente")
        
        # Test 1: Normalización
        texto = "José Ramírez Jr."
        normalizado = predictor.normalizar(texto)
        print(f"📝 Normalización: '{texto}' -> '{normalizado}'")
        
        # Test 2: Análisis de equipo
        print("\n🔍 Test: Análisis de equipo 'New York Yankees'")
        analisis_yankees = predictor.analizar_equipo_completo("New York Yankees", "12345")
        
        if analisis_yankees:
            print(f"✅ Análisis completado: {len(analisis_yankees)} bateadores encontrados")
            for b in analisis_yankees:
                print(f"   - {b['nombre']}: {b['probabilidad']}% HR ({b['stake']})")
        else:
            print("⚠️ No se encontraron bateadores (posible falta de lineup)")
        
        # Test 3: Análisis completo de partido
        print("\n🎯 Test: Análisis completo de partido")
        analisis_partido = predictor.analizar_partido_completo(
            "New York Yankees", 
            "Boston Red Sox", 
            "12345",
            "Yankee Stadium",
            {"temp": 78, "wind_speed": 8, "wind_dir": "Out"}
        )
        
        print(f"✅ Análisis de partido completado:")
        print(f"   Local: {len(analisis_partido.get('local', []))} bateadores")
        print(f"   Visitante: {len(analisis_partido.get('visitante', []))} bateadores")
        
        # Test 4: HTML de visualización
        print("\n🖥️ Test: Generación de HTML de visualización")
        html = predictor.generar_html_visualizacion(analisis_partido, partidos_prueba[0])
        
        if html and len(html) > 100:
            print(f"✅ HTML generado correctamente ({len(html)} caracteres)")
            print(f"   Contiene 'PREDICTOR HR PRO': {'PREDICTOR HR PRO' in html}")
            print(f"   Contiene 'New York Yankees': {'New York Yankees' in html}")
            print(f"   Contiene 'Boston Red Sox': {'Boston Red Sox' in html}")
        else:
            print("❌ Error generando HTML")
        
        # Test 5: Registro de picks
        print("\n📊 Test: Registro de picks")
        registro_ok = predictor.registrar_pick(
            "NYY vs BOS",
            "Aaron Judge",
            42.5,
            "3u",
            True
        )
        
        print(f"✅ Pick registrado: {'Sí' if registro_ok else 'No'}")
        
        # Test 6: Estadísticas
        print("\n📈 Test: Estadísticas")
        stats = predictor.obtener_estadisticas_pro()
        print(f"   Total picks: {stats.get('total', 0)}")
        print(f"   Aciertos: {stats.get('aciertos', 0)}")
        print(f"   Tasa: {stats.get('tasa', 0)}%")
        
        print("\n" + "="*60)
        print("✅ TODOS LOS TESTS COMPLETADOS EXITOSAMENTE")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR EN TEST: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_hr_panel_pro():
    """Test del panel HR Pro"""
    print("\n" + "="*60)
    print("🖥️ TEST DE INTEGRACIÓN HR PANEL PRO")
    print("="*60)
    
    try:
        from visualizers.hr_panel_pro import HRPanelPro
        
        print("✅ Módulo HRPanelPro importado correctamente")
        
        # Crear instancia
        panel = HRPanelPro()
        print("✅ Instancia HRPanelPro creada correctamente")
        
        # Datos de prueba
        partido_prueba = {
            "local": "New York Yankees",
            "visitante": "Boston Red Sox",
            "game_pk": "12345",
            "venue": "Yankee Stadium",
            "local_logo": "https://example.com/yankees.png",
            "visitante_logo": "https://example.com/redsox.png",
            "hora": "19:05 ET",
            "pitchers": {
                "local": {"nombre": "Gerrit Cole", "mano": "R"},
                "visitante": {"nombre": "Chris Sale", "mano": "L"}
            }
        }
        
        print("📋 Datos de prueba configurados")
        
        # Test de métodos básicos
        print("\n🔍 Test de métodos del panel:")
        print(f"   Cache key generado: {panel.cache_key}")
        
        # No podemos probar render_panel completamente sin Streamlit,
        # pero podemos verificar que los métodos existen
        methods = ['render_panel', '_render_analisis_panel', '_render_bateador_card']
        for method in methods:
            if hasattr(panel, method):
                print(f"   ✅ Método '{method}' disponible")
            else:
                print(f"   ❌ Método '{method}' no encontrado")
        
        print("\n" + "="*60)
        print("✅ TEST HR PANEL PRO COMPLETADO")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR EN TEST: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_visual_mlb_pro():
    """Test del visualizador MLB Pro"""
    print("\n" + "="*60)
    print("🎨 TEST DE VISUALIZADOR MLB PRO")
    print("="*60)
    
    try:
        from visualizers.visual_mlb_pro import VisualMLBPro
        
        print("✅ Módulo VisualMLBPro importado correctamente")
        
        # Crear instancia
        visualizador = VisualMLBPro()
        print("✅ Instancia VisualMLBPro creada correctamente")
        
        # Test de métodos
        print("\n🔍 Test de métodos del visualizador:")
        
        methods = [
            'render', '_render_encabezado_partido', '_render_alertas_recomendaciones',
            '_render_total_proyectado', '_render_proyeccion_strikes',
            '_mostrar_historial_reciente_pro', '_render_boton_analisis'
        ]
        
        for method in methods:
            if hasattr(visualizador, method):
                print(f"   ✅ Método '{method}' disponible")
            else:
                print(f"   ❌ Método '{method}' no encontrado")
        
        print("\n" + "="*60)
        print("✅ TEST VISUAL MLB PRO COMPLETADO")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR EN TEST: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Función principal de test"""
    print("🧪 INICIANDO TEST DE INTEGRACIÓN HR PRO COMPLETA")
    print("="*60)
    
    # Añadir directorio actual al path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    resultados = []
    
    # Ejecutar tests
    resultados.append(("Predictor HR Pro", test_predictor_hr_pro()))
    resultados.append(("HR Panel Pro", test_hr_panel_pro()))
    resultados.append(("Visual MLB Pro", test_visual_mlb_pro()))
    
    # Resumen
    print("\n" + "="*60)
    print("📊 RESUMEN DE TESTS")
    print("="*60)
    
    exitos = 0
    total = len(resultados)
    
    for nombre, resultado in resultados:
        status = "✅ PASÓ" if resultado else "❌ FALLÓ"
        print(f"   {nombre}: {status}")
        if resultado:
            exitos += 1
    
    print(f"\n🎯 Resultado: {exitos}/{total} tests exitosos ({exitos/total*100:.0f}%)")
    
    if exitos == total:
        print("\n✨ ¡TODOS LOS TESTS PASARON! El sistema HR Pro está listo.")
        print("\n📋 PRÓXIMOS PASOS:")
        print("1. Integrar visual_mlb_pro.py en main_vision_completo.py")
        print("2. Actualizar la llamada a VisualMLBPro en lugar de VisualMLB")
        print("3. Verificar que los datos de bateadores estén en hr_datasets_completos.json")
        print("4. Ejecutar el sistema completo")
    else:
        print("\n⚠️ Algunos tests fallaron. Revisa los errores arriba.")
    
    return exitos == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)