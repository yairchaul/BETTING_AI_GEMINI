# -*- coding: utf-8 -*-
"""
DIAGNÓSTICO COMPLETO BETTING_AI V24
Verifica la integridad de todos los componentes del sistema
"""

import os
import sys
import json
import sqlite3
from datetime import datetime
import logging
import asyncio

# Imports para pruebas de conexión real
try:
    import google.generativeai as genai
    from groq import Groq
    from openai import OpenAI
except ImportError:
    genai = None
    OpenAI = None

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class DiagnosticoBettingAI:
    def __init__(self):
        self.resultados = {
            "scrapers": {},
            "motores": {},
            "visualizadores": {},
            "ias": {},
            "archivos": {},
            "base_datos": {},
            "timestamp": datetime.now().isoformat()
        }
        
    def verificar_scrapers(self):
        """Verifica que todos los scrapers estén presentes y funcionales"""
        print("\n🔍 VERIFICANDO SCRAPERS...")
        scrapers_esperados = {
            "ESPN_NBA": "scrapers/espn_nba.py",
            "ESPN_MLB": "scrapers/espn_mlb.py",
            "ESPN_UFC": "scrapers/espn_ufc.py",
            "ESPN_Futbol": "scrapers/espn_futbol.py",
            "NBA_Stats": "scrapers/nba_stats_scraper_fixed.py",
            "UFC_Stats": "scrapers/ufc_stats_scraper.py",
            "MLB_Resultados": "scrapers/mlb_resultados_scraper.py"
        }
        
        for nombre, ruta in scrapers_esperados.items():
            existe = os.path.exists(ruta)
            self.resultados["scrapers"][nombre] = "✅ OK" if existe else "❌ FALTANTE"
            print(f"  {nombre}: {self.resultados['scrapers'][nombre]}")
            
            if existe:
                # Verificar importación
                try:
                    if "nba" in ruta.lower():
                        from scrapers.espn_nba import ESPN_NBA
                    elif "mlb" in ruta.lower():
                        from scrapers.espn_mlb import ESPN_MLB_Mejorado
                    elif "ufc" in ruta.lower() and "stats" in ruta.lower():
                        from scrapers.ufc_stats_scraper import UFCStatsScraper
                    elif "ufc" in ruta.lower():
                        from scrapers.espn_ufc import ESPN_UFC
                    self.resultados["scrapers"][nombre] += " (Importable)"
                except Exception as e:
                    self.resultados["scrapers"][nombre] = f"⚠️ Error de importación: {str(e)[:50]}"
                    print(f"    ⚠️ Error: {str(e)[:100]}")
    
    def verificar_motores(self):
        """Verifica que todos los motores de análisis estén presentes"""
        print("\n⚙️ VERIFICANDO MOTORES...")
        motores_esperados = {
            "NBA_Heurístico": "motors/analizar_nba_pro_v17.py",
            "NBA_OverUnder": "motors/motor_nba_over_under.py",
            "MLB_Heurístico": "motors/analizar_mlb_pro_v20.py",
            "MLB_HR": "motors/predictor_hr.py",
            "MLB_K": "motors/predictor_ponches.py",
            "MLB_OverUnder": "motors/motor_over_under.py",
            "UFC_Analyzer": "motors/ufc_analyzer.py",
            "Futbol_Jerarquico": "motors/futbol_analyzer_jerarquico.py",
            "Motor_Momentum": "motors/motor_momentum.py",
            "Decision_Inteligente": "motors/motor_decision_inteligente.py"
        }
        
        for nombre, ruta in motores_esperados.items():
            existe = os.path.exists(ruta)
            self.resultados["motores"][nombre] = "✅ OK" if existe else "❌ FALTANTE"
            print(f"  {nombre}: {self.resultados['motores'][nombre]}")
    
    def verificar_visualizadores(self):
        """Verifica visualizadores activos y detecta duplicados"""
        print("\n🎨 VERIFICANDO VISUALIZADORES...")
        visualizadores_activos = {
            "NBA": "visualizers/visual_nba_mejorado.py",
            "MLB": "visualizers/visual_mlb.py",
            "UFC": "visualizers/visual_ufc_mejorado_v2.py",
            "Futbol": "visualizers/visual_futbol_triple.py"
        }
        
        for nombre, ruta in visualizadores_activos.items():
            existe = os.path.exists(ruta)
            self.resultados["visualizadores"][nombre] = "✅ ACTIVO" if existe else "❌ FALTANTE"
            print(f"  {nombre}: {self.resultados['visualizadores'][nombre]}")
        
        # Verificar duplicados movidos a _deprecated
        deprecated_dir = "visualizers/_deprecated"
        if os.path.exists(deprecated_dir):
            deprecated_count = len([f for f in os.listdir(deprecated_dir) if f.endswith('.py')])
            print(f"  📦 {deprecated_count} archivos en _deprecated/")
            self.resultados["visualizadores"]["deprecated"] = f"{deprecated_count} archivos archivados"
        else:
            print("  ⚠️ Carpeta _deprecated no existe (duplicados no movidos)")
    
    def _probar_conexion_ia_real(self, nombre_ia, api_key):
        """Intenta una conexión real con la API de la IA."""
        prompt_test = "Hola, responde solo OK"
        try:
            if nombre_ia == "Gemini" and genai:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content(prompt_test)
                if "OK" in response.text:
                    return "✅ Conexión Válida"
                else:
                    return f"⚠️ Conectado, pero respuesta inesperada: {response.text[:30]}"
            
            elif nombre_ia == "Groq" and 'Groq' in globals():
                client = Groq(api_key=api_key)
                chat_completion = client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt_test}],
                    model="llama3-8b-8192",
                )
                if "OK" in chat_completion.choices[0].message.content:
                    return "✅ Conexión Válida"
                else:
                    return "⚠️ Conectado, pero respuesta inesperada"
            
            elif nombre_ia == "DeepSeek" and 'OpenAI' in globals() and OpenAI:
                client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")
                chat_completion = client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt_test}],
                    model="deepseek-chat",
                    max_tokens=10
                )
                if "OK" in chat_completion.choices[0].message.content:
                    return "✅ Conexión Válida"
                else:
                    return f"⚠️ Conectado, pero respuesta inesperada: {chat_completion.choices[0].message.content[:30]}"
            
            # Aquí se podrían añadir más pruebas para DeepSeek, OpenAI, etc.
            
            return " (Prueba no implementada)"
        
        except Exception as e:
            error_str = str(e)
            if "API key is invalid" in error_str or "AuthenticationError" in error_str:
                return "❌ Key Inválida"
            elif "quota" in error_str.lower():
                return "⚠️ Sin Saldo/Cuota"
            return f"❌ Error: {error_str[:40]}..."

    def verificar_ias(self):
        """Verifica clientes de IA y sus API keys"""
        print("\n🤖 VERIFICANDO INTELIGENCIA ARTIFICIAL...")
        from dotenv import load_dotenv
        load_dotenv()
        
        ias_config = { # Se mantiene OpenAI por si se usa en el futuro
            "Gemini": "GEMINI_API_KEY",
            "Groq": "GROQ_API_KEY",
            "DeepSeek": "DEEPSEEK_API_KEY",
            "OpenAI": "OPENAI_API_KEY" 
        }
        
        for nombre, var_env in ias_config.items():
            key = os.getenv(var_env, '')
            if key and len(key) > 10:
                # Realizar prueba de conexión real
                status_conexion = self._probar_conexion_ia_real(nombre, key)
                self.resultados["ias"][nombre] = f"✅ Configurada (***{key[-4:]}) - {status_conexion}"
                print(f"  {nombre}: {self.resultados['ias'][nombre]}")
            else:
                self.resultados["ias"][nombre] = "❌ API Key no encontrada"
                print(f"  {nombre}: {self.resultados['ias'][nombre]}")
    
    def verificar_archivos_criticos(self):
        """Verifica existencia y estado de archivos de datos"""
        print("\n💾 VERIFICANDO ARCHIVOS DE DATOS...")
        archivos_criticos = {
            "Database": "data/betting_stats.db",
            "MLB_Partidos": "data/resultados_finales_corregidos.json",
            "MLB_Resultados": "data/resultados_reales_15dias.json",
            "NBA_Cache": "data/nba_team_stats_cache.json",
            "UFC_Cache": "data/ufc_stats_cache.json",
            "Bitácora": "data/bitacora_maestra.csv",
            "Pesos_Motores": "data/pesos_motores.json",
            "Aprendizaje": "data/aprendizaje_semanal.json"
        }
        
        for nombre, ruta in archivos_criticos.items():
            if os.path.exists(ruta):
                size_kb = os.path.getsize(ruta) / 1024
                self.resultados["archivos"][nombre] = f"✅ {size_kb:.1f} KB"
                print(f"  {nombre}: {self.resultados['archivos'][nombre]}")
            else:
                self.resultados["archivos"][nombre] = "❌ FALTANTE"
                print(f"  {nombre}: {self.resultados['archivos'][nombre]}")
    
    def verificar_base_datos(self):
        """Verifica estructura de la base de datos SQLite"""
        print("\n🗄️ VERIFICANDO BASE DE DATOS...")
        db_path = "data/betting_stats.db"
        
        if not os.path.exists(db_path):
            print("  ❌ Base de datos no existe")
            self.resultados["base_datos"]["estado"] = "❌ No existe"
            return
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Verificar tablas
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tablas = [row[0] for row in cursor.fetchall()]
            
            for tabla in tablas:
                cursor.execute(f"SELECT COUNT(*) FROM {tabla}")
                count = cursor.fetchone()[0]
                self.resultados["base_datos"][tabla] = f"✅ {count} registros"
                print(f"  Tabla '{tabla}': {count} registros")
            
            conn.close()
            
            if not tablas:
                print("  ⚠️ Base de datos vacía (sin tablas)")
                self.resultados["base_datos"]["estado"] = "⚠️ Sin tablas"
        except Exception as e:
            print(f"  ❌ Error al verificar BD: {e}")
            self.resultados["base_datos"]["error"] = str(e)
    
    def generar_reporte(self):
        """Genera reporte JSON del diagnóstico"""
        reporte_path = "data/diagnostico_sistema.json"
        os.makedirs("data", exist_ok=True)
        
        with open(reporte_path, 'w', encoding='utf-8') as f:
            json.dump(self.resultados, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 Reporte guardado en: {reporte_path}")
        
        # Resumen de estado
        print("\n" + "="*60)
        print("📊 RESUMEN DEL DIAGNÓSTICO")
        print("="*60)
        
        for categoria, items in self.resultados.items():
            if categoria == "timestamp":
                continue
            total = len(items)
            ok_count = sum(1 for v in items.values() if "✅" in str(v))
            print(f"{categoria.upper()}: {ok_count}/{total} OK")
        
        print("="*60)
    
    def ejecutar_diagnostico_completo(self):
        """Ejecuta todas las verificaciones"""
        print("🏥 INICIANDO DIAGNÓSTICO COMPLETO DE BETTING_AI V24")
        print("="*60)
        
        self.verificar_scrapers()
        self.verificar_motores()
        self.verificar_visualizadores()
        self.verificar_ias()
        self.verificar_archivos_criticos()
        self.verificar_base_datos()
        self.generar_reporte()
        
        print("\n✅ Diagnóstico completado")

if __name__ == "__main__":
    diagnostico = DiagnosticoBettingAI()
    diagnostico.ejecutar_diagnostico_completo()
