# -*- coding: utf-8 -*-
"""
TEST DEL SISTEMA COMPLETO - Verifica que toda la integración funcione
"""

import sys
import os
import json
from datetime import datetime

def test_importaciones():
    """Test de todas las importaciones necesarias"""
    print("="*60)
    print("🧪 TEST DE IMPORTACIONES DEL SISTEMA")
    print("="*60)
    
    modulos = [
        ("streamlit", "st"),
        ("motors.predictor_hr_pro", "PredictorHRPro"),
        ("visualizers.hr_panel_pro", "HRPanelPro"),
        ("visualizers.visual_mlb_pro", "VisualMLBPro"),
        ("motors.predictor_strikes", "predictor_strikes"),
        ("motors.motor_over_under", "motor_over_under"),
        ("motors.motor_lanzadores", "obtener_analisis_lanzadores")
    ]
    
    exitos = 0
    total = len(modulos)
    
    for modulo, elemento in modulos:
        try:
            if "." in modulo:
                # Importar módulo específico
                exec(f"from {modulo} import {elemento}")
            else:
                # Importar módulo completo
                exec(f"import {modulo}")
            
            print(f"✅ {modulo} importado correctamente")
            exitos += 1
        except Exception as e:
            print(f"❌ Error importando {modulo}: {e}")
    
    print(f"\n🎯 Resultado: {exitos}/{total} importaciones exitosas")
    return exitos == total

def test_datos_hr():
    """Test de los datos HR"""
    print("\n" + "="*60)
    print("📊 TEST DE DATOS HR")
    print("="*60)
    
    try:
        # Verificar archivo de datos
        archivo_datos = "hr_datasets_completos.json"
        
        if not os.path.exists(archivo_datos):
            print(f"❌ Archivo {archivo_datos} no encontrado")
            return False
        
        with open(archivo_datos, "r", encoding="utf-8") as f:
            datos = json.load(f)
        
        bateadores = datos.get("bateadores", {})
        pitchers = datos.get("pitchers", {})
        
        print(f"✅ Archivo {archivo_datos} cargado correctamente")
        print(f"   Bateadores: {len(bateadores)} registros")
        print(f"   Pitchers: {len(pitchers)} registros")
        
        # Verificar algunos bateadores clave
        bateadores_clave = ["Aaron Judge", "Juan Soto", "Shohei Ohtani"]
        for bc in bateadores_clave:
            if bc in bateadores:
                stats = bateadores[bc]
                print(f"   ✅ {bc}: {stats.get('hr', 0)} HR, {stats.get('hr_por_juego', 0)}/juego")
            else:
                print(f"   ⚠️ {bc} no encontrado en datos")
        
        return True
    except Exception as e:
        print(f"❌ Error en test de datos: {e}")
        return False

def test_instancias():
    """Test de creación de instancias"""
    print("\n" + "="*60)
    print("🔧 TEST DE CREACIÓN DE INSTANCIAS")
    print("="*60)
    
    try:
        from motors.predictor_hr_pro import PredictorHRPro
        from visualizers.hr_panel_pro import HRPanelPro
        from visualizers.visual_mlb_pro import VisualMLBPro
        
        # Cargar datos
        archivo_datos = "hr_datasets_completos.json"
        with open(archivo_datos, "r", encoding="utf-8") as f:
            datos = json.load(f)
        
        # Crear instancias
        predictor = PredictorHRPro(data_source=datos)
        panel = HRPanelPro()
        visualizador = VisualMLBPro()
        
        print("✅ Todas las instancias creadas correctamente")
        print(f"   PredictorHRPro: {type(predictor).__name__}")
        print(f"   HRPanelPro: {type(panel).__name__}")
        print(f"   VisualMLBPro: {type(visualizador).__name__}")
        
        # Verificar que tienen los métodos principales
        metodos_predictor = ['analizar_equipo_completo', 'analizar_partido_completo', 'generar_html_visualizacion']
        metodos_panel = ['render_panel']
        metodos_visual = ['render']
        
        for metodo in metodos_predictor:
            if hasattr(predictor, metodo):
                print(f"   ✅ Predictor tiene método: {metodo}")
            else:
                print(f"   ❌ Predictor no tiene método: {metodo}")
        
        return True
    except Exception as e:
        print(f"❌ Error creando instancias: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_partido_completo():
    """Test de análisis completo de partido"""
    print("\n" + "="*60)
    print("🎯 TEST DE ANÁLISIS DE PARTIDO COMPLETO")
    print("="*60)
    
    try:
        from motors.predictor_hr_pro import PredictorHRPro
        
        # Cargar datos
        archivo_datos = "hr_datasets_completos.json"
        with open(archivo_datos, "r", encoding="utf-8") as f:
            datos = json.load(f)
        
        # Crear datos de partido de prueba
        partido_prueba = {
            "local": "New York Yankees",
            "visitante": "Boston Red Sox",
            "game_pk": "20230608_NYY_BOS",
            "venue": "Yankee Stadium",
            "pitchers": {
                "local": {"nombre": "Gerrit Cole", "mano": "R", "era": 2.90, "k9": 11.2, "hr9": 0.9},
                "visitante": {"nombre": "Chris Sale", "mano": "L", "era": 3.20, "k9": 12.8, "hr9": 1.1}
            }
        }
        
        mlb_partidos_hoy = [partido_prueba]
        
        # Crear predictor
        predictor = PredictorHRPro(data_source=datos, mlb_partidos_hoy=mlb_partidos_hoy)
        
        # Ejecutar análisis
        clima = {"temp": 78, "wind_speed": 12, "wind_dir": "Out"}
        analisis = predictor.analizar_partido_completo(
            "New York Yankees",
            "Boston Red Sox",
            "20230608_NYY_BOS",
            "Yankee Stadium",
            clima
        )
        
        print("✅ Análisis de partido completado")
        print(f"   Local: {len(analisis.get('local', []))} bateadores analizados")
        print(f"   Visitante: {len(analisis.get('visitante', []))} bateadores analizados")
        print(f"   Game PK: {analisis.get('game_pk')}")
        print(f"   Timestamp: {analisis.get('timestamp')}")
        
        # Mostrar algunos resultados
        if analisis.get('local'):
            print("\n📈 Bateadores locales (top 3):")
            for b in analisis['local'][:3]:
                print(f"   {b['nombre']}: {b['probabilidad']}% HR ({b['stake']}) - {b['recomendacion']}")
        
        if analisis.get('visitante'):
            print("\n📈 Bateadores visitantes (top 3):")
            for b in analisis['visitante'][:3]:
                print(f"   {b['nombre']}: {b['probabilidad']}% HR ({b['stake']}) - {b['recomendacion']}")
        
        return True
    except Exception as e:
        print(f"❌ Error en análisis de partido: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_html_generacion():
    """Test de generación de HTML"""
    print("\n" + "="*60)
    print("🖥️ TEST DE GENERACIÓN DE HTML")
    print("="*60)
    
    try:
        from motors.predictor_hr_pro import PredictorHRPro
        
        # Cargar datos
        archivo_datos = "hr_datasets_completos.json"
        with open(archivo_datos, "r", encoding="utf-8") as f:
            datos = json.load(f)
        
        # Crear datos de partido y análisis
        partido_prueba = {
            "local": "New York Yankees",
            "visitante": "Boston Red Sox",
            "game_pk": "20230608_NYY_BOS"
        }
        
        mlb_partidos_hoy = [partido_prueba]
        predictor = PredictorHRPro(data_source=datos, mlb_partidos_hoy=mlb_partidos_hoy)
        
        # Análisis simulado
        analisis_simulado = {
            "local": [
                {
                    "nombre": "Aaron Judge",
                    "probabilidad": 95.0,
                    "color": "#00ff41",
                    "icono": "🔥🔥🔥",
                    "stake": "4u",
                    "recomendacion": "ELITE",
                    "pitcher_rival": "Chris Sale",
                    "mano_pitcher": "L",
                    "hr9_pitcher": 1.1,
                    "hr_total": 12,
                    "hr_por_juego": 0.80,
                    "factores": ["Pitcher vulnerable", "Viento favorable", "Racha caliente"]
                }
            ],
            "visitante": [
                {
                    "nombre": "Rafael Devers",
                    "probabilidad": 65.0,
                    "color": "#fbbf24",
                    "icono": "🔥🔥",
                    "stake": "3u",
                    "recomendacion": "ALTA",
                    "pitcher_rival": "Gerrit Cole",
                    "mano_pitcher": "R",
                    "hr9_pitcher": 0.9,
                    "hr_total": 9,
                    "hr_por_juego": 0.60,
                    "factores": ["Bateador en racha", "Estadio favorable"]
                }
            ],
            "game_pk": "20230608_NYY_BOS",
            "estadio": "Yankee Stadium",
            "timestamp": datetime.now().isoformat()
        }
        
        # Generar HTML
        html = predictor.generar_html_visualizacion(analisis_simulado, partido_prueba)
        
        print(f"✅ HTML generado correctamente ({len(html)} caracteres)")
        print(f"   Contiene 'PREDICTOR HR PRO': {'PREDICTOR HR PRO' in html}")
        print(f"   Contiene 'New York Yankees': {'New York Yankees' in html}")
        print(f"   Contiene 'Boston Red Sox': {'Boston Red Sox' in html}")
        print(f"   Contiene 'Aaron Judge': {'Aaron Judge' in html}")
        print(f"   Contiene 'Rafael Devers': {'Rafael Devers' in html}")
        
        # Guardar muestra para inspección
        with open("test_html_muestra.html", "w", encoding="utf-8") as f:
            f.write(html)
        
        print("📄 Muestra de HTML guardada en 'test_html_muestra.html'")
        
        return True
    except Exception as e:
        print(f"❌ Error generando HTML: {e}")
        return False

def main():
    """Función principal de test"""
    print("🚀 TEST COMPLETO DEL SISTEMA HR PRO INTEGRADO")
    print("="*60)
    
    # Añadir directorio actual al path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    # Ejecutar todos los tests
    tests = [
        ("Importaciones", test_importaciones),
        ("Datos HR", test_datos_hr),
        ("Instancias", test_instancias),
        ("Partido Completo", test_partido_completo),
        ("HTML Generación", test_html_generacion)
    ]
    
    resultados = []
    
    for nombre_test, funcion_test in tests:
        print(f"\n▶️ Ejecutando: {nombre_test}")
        try:
            resultado = funcion_test()
            resultados.append((nombre_test, resultado))
        except Exception as e:
            print(f"❌ Error ejecutando {nombre_test}: {e}")
            resultados.append((nombre_test, False))
    
    # Resumen
    print("\n" + "="*60)
    print("📊 RESUMEN FINAL DE TESTS")
    print("="*60)
    
    exitos = sum(1 for _, resultado in resultados if resultado)
    total = len(resultados)
    
    for nombre, resultado in resultados:
        status = "✅ PASÓ" if resultado else "❌ FALLÓ"
        print(f"   {nombre}: {status}")
    
    print(f"\n🎯 Resultado final: {exitos}/{total} tests exitosos ({exitos/total*100:.0f}%)")
    
    if exitos == total:
        print("\n✨ ¡FELICITACIONES! El sistema HR Pro está completamente integrado.")
        print("\n📋 PARA USAR EL SISTEMA:")
        print("1. Ejecuta main_vision_completo.py para iniciar la aplicación")
        print("2. Selecciona la pestaña MLB")
        print("3. Carga partidos desde el panel de control")
        print("4. Verás el nuevo panel 'PREDICTOR HR PRO' en cada partido")
        print("\n💡 Características nuevas:")
        print("   - 💣 Panel de HR Pro expandible")
        print("   - 📊 Análisis por equipo (Local/Visitante)")
        print("   - 🎯 Probabilidades inteligentes con múltiples factores")
        print("   - ⭐ Clasificación por stake (1u-4u)")
        print("   - 🔥 Indicadores visuales de confianza")
        print("   - 📈 Factores de ajuste visibles")
    else:
        print("\n⚠️ Algunos tests fallaron. Revisa los errores arriba.")
        print("Problemas comunes:")
        print("   - Archivos de datos faltantes")
        print("   - Dependencias no instaladas")
        print("   - Errores de importación")
    
    return exitos == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)