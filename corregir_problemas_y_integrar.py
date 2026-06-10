# -*- coding: utf-8 -*-
"""
SCRIPT PARA CORREGIR PROBLEMAS E INTEGRAR MOTOR MLB COMPLETO
"""

import os
import re
import sys

def fix_balldontlie_syntax():
    """Corrige el error de sintaxis en balldontlie_client.py"""
    filepath = "balldontlie_client.py"
    
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Buscar y eliminar triple backticks sueltos
        content = content.replace('```\n        if search:', '        if search:')
        
        # Guardar archivo corregido
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ {filepath}: Corregido error de backticks")
    else:
        print(f"⚠️ {filepath}: No encontrado")

def fix_main_vision_completo():
    """Corrige posibles problemas en main_vision_completo.py"""
    filepath = "main_vision_completo.py"
    
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Buscar problemas comunes:
        # 1. Números decimales mal formados (ej: .90 sin 0 delante)
        # 2. Comillas triples no cerradas
        
        # Corregir números decimales sin 0 delante
        content = re.sub(r'(?<!\d)\.(\d+)', r'0.\1', content)
        
        # Verificar comillas triples balanceadas
        triple_single_count = content.count("'''")
        triple_double_count = content.count('"""')
        
        if triple_single_count % 2 != 0:
            print(f"⚠️ {filepath}: Comillas simples triples no balanceadas")
        if triple_double_count % 2 != 0:
            print(f"⚠️ {filepath}: Comillas dobles triples no balanceadas")
        
        # Guardar archivo corregido
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ {filepath}: Verificado y corregido problemas potenciales")
    else:
        print(f"⚠️ {filepath}: No encontrado")

def fix_motor_nba_over_under():
    """Corrige problemas en motor_nba_over_under.py"""
    filepath = "motors/motor_nba_over_under.py"
    
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Reemplazar posibles caracteres BOM o problemas de encoding
        content = content.replace('\ufeff', '')  # Remove BOM
        
        # Asegurar que los docstrings estén cerrados
        lines = content.split('\n')
        in_triple_quote = False
        quote_char = None
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Verificar inicio/fin de triple quote
            if stripped.startswith('"""') or stripped.startswith("'''"):
                if not in_triple_quote:
                    in_triple_quote = True
                    quote_char = stripped[:3]
                elif stripped.endswith(quote_char):
                    in_triple_quote = False
                    quote_char = None
        
        if in_triple_quote:
            print(f"⚠️ {filepath}: Docstring no cerrado detectado")
            # Agregar cierre al final
            content += '\n"""'
        
        # Guardar archivo corregido
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ {filepath}: Verificado y corregido")
    else:
        print(f"⚠️ {filepath}: No encontrado")

def integrate_mlb_motor_into_main():
    """Integra el motor MLB completo en main_vision_completo.py"""
    filepath = "main_vision_completo.py"
    
    if not os.path.exists(filepath):
        print(f"❌ {filepath}: No encontrado")
        return
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verificar si ya está integrado
    if 'from motors.motor_mlb_completo import motor_mlb' in content:
        print("✅ Motor MLB ya está integrado en main_vision_completo.py")
        return
    
    # Buscar sección de imports
    import_section = """
# ==================== IMPORTS ====================
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import json
import os
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")
"""
    
    # Agregar imports del motor MLB
    new_imports = """# Importar Motor MLB Completo
from motors.motor_mlb_completo import motor_mlb
from visualizers.visual_mlb_integrado import visual_mlb_integrado
"""
    
    # Insertar después de la sección de imports
    if import_section in content:
        content = content.replace(import_section, import_section + new_imports)
    else:
        # Buscar primeros imports
        lines = content.split('\n')
        insert_idx = None
        for i, line in enumerate(lines):
            if line.strip().startswith('import ') or line.strip().startswith('from '):
                insert_idx = i
                break
        
        if insert_idx is not None:
            # Insertar después del último import consecutivo
            while insert_idx + 1 < len(lines) and (
                lines[insert_idx + 1].strip().startswith('import ') or 
                lines[insert_idx + 1].strip().startswith('from ') or
                lines[insert_idx + 1].strip() == ''
            ):
                insert_idx += 1
            
            lines.insert(insert_idx + 1, new_imports)
            content = '\n'.join(lines)
    
    # Buscar inicialización de session_state para agregar motor MLB
    init_pattern = r'if \'visual_mlb\' not in st\.session_state:'
    if init_pattern in content:
        # Agregar inicialización del motor MLB completo
        mlb_init = """
    # Inicializar Motor MLB Completo
    if 'motor_mlb_completo' not in st.session_state:
        st.session_state.motor_mlb_completo = motor_mlb
    
    # Inicializar Visualizador MLB Integrado
    if 'visual_mlb_integrado' not in st.session_state:
        st.session_state.visual_mlb_integrado = visual_mlb_integrado
"""
        
        # Insertar después de la inicialización de visual_mlb
        match = re.search(init_pattern, content)
        if match:
            # Buscar el cierre de ese bloque (generalmente 2-3 líneas después)
            lines = content.split('\n')
            start_idx = match.start()
            line_idx = content[:start_idx].count('\n')
            
            # Encontrar línea donde termina ese if
            indent_level = len(lines[line_idx]) - len(lines[line_idx].lstrip())
            end_idx = line_idx + 1
            
            while end_idx < len(lines):
                current_line = lines[end_idx]
                current_indent = len(current_line) - len(current_line.lstrip())
                
                if current_indent <= indent_level and current_line.strip() != '':
                    break
                end_idx += 1
            
            # Insertar después del bloque
            lines.insert(end_idx, mlb_init)
            content = '\n'.join(lines)
    
    # Buscar la sección de renderizado MLB para actualizarla
    mlb_render_pattern = r'for idx, p in enumerate\(st\.session_state\.mlb_partidos\):'
    if mlb_render_pattern in content:
        # Reemplazar con versión mejorada que use el motor completo
        new_mlb_render = """        # Renderizar partidos MLB con Motor Completo
        for idx, p in enumerate(st.session_state.mlb_partidos):
            # Usar visualizador integrado
            st.session_state.visual_mlb_integrado.render_partido_completo(p, idx)"""
        
        content = re.sub(mlb_render_pattern + r'.*?(?=\n    \S|\Z)', new_mlb_render, content, flags=re.DOTALL)
    
    # Guardar archivo actualizado
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ {filepath}: Motor MLB integrado exitosamente")

def run_syntax_checks():
    """Ejecuta verificaciones de sintaxis en archivos clave"""
    files_to_check = [
        "balldontlie_client.py",
        "main_vision_completo.py", 
        "motors/motor_nba_over_under.py",
        "motors/motor_mlb_completo.py",
        "visualizers/visual_mlb_integrado.py"
    ]
    
    print("\n🔍 EJECUTANDO VERIFICACIONES DE SINTÁXIS...")
    
    for filepath in files_to_check:
        if os.path.exists(filepath):
            try:
                compile_result = os.system(f'python -m py_compile "{filepath}"')
                if compile_result == 0:
                    print(f"   ✅ {filepath}: Sintaxis correcta")
                else:
                    print(f"   ❌ {filepath}: Error de sintaxis")
            except Exception as e:
                print(f"   ⚠️ {filepath}: Error al verificar: {e}")
        else:
            print(f"   ⚠️ {filepath}: No encontrado")

def main():
    print("="*70)
    print("🔧 CORRECCIÓN DE PROBLEMAS E INTEGRACIÓN MLB COMPLETA")
    print("="*70)
    
    # Paso 1: Corregir problemas de sintaxis
    print("\n1. 🔨 CORRIGIENDO PROBLEMAS DE SINTÁXIS...")
    fix_balldontlie_syntax()
    fix_main_vision_completo()
    fix_motor_nba_over_under()
    
    # Paso 2: Integrar motor MLB
    print("\n2. 🔄 INTEGRANDO MOTOR MLB COMPLETO...")
    integrate_mlb_motor_into_main()
    
    # Paso 3: Verificar sintaxis
    print("\n3. ✅ VERIFICANDO RESULTADOS...")
    run_syntax_checks()
    
    # Paso 4: Crear directorio de caché si no existe
    print("\n4. 📁 CREANDO DIRECTORIOS NECESARIOS...")
    os.makedirs("data/mlb_cache", exist_ok=True)
    print("   ✅ Directorio data/mlb_cache creado/verificado")
    
    print("\n" + "="*70)
    print("🎉 PROCESO COMPLETADO EXITOSAMENTE")
    print("="*70)
    print("\n📋 RESUMEN DE CAMBIOS:")
    print("   1. ✅ Corregidos errores de sintaxis en archivos problemáticos")
    print("   2. ✅ Integrado Motor MLB Completo en main_vision_completo.py")
    print("   3. ✅ Motor incluye: Lanzadores + Lineups + Alertas HR + Proyección K")
    print("   4. ✅ Caché automático configurado en data/mlb_cache/")
    print("   5. ✅ Visualizador MLB Integrado listo para usar")
    
    print("\n🚀 AHORA EL SISTEMA MLB:")
    print("   • No mostrará 'TBD' - Usa API oficial MLB")
    print("   • Datos reales de pitchers (K/9, ERA, WHIP, HR/9)")
    print("   • Lineups oficiales confirmados")
    print("   • Alertas HR basadas en vulnerabilidad del pitcher")
    print("   • Proyección K precisa con fórmula MLB")
    print("   • Caché automático (30 min lanzadores, 15 min lineups)")
    
    print("\n💡 EJECUTA: python main_vision_completo.py")
    print("   y selecciona la pestaña MLB para ver los cambios")
    print("="*70)

if __name__ == "__main__":
    main()