# -*- coding: utf-8 -*-
"""
VERIFICADOR DE INTEGRIDAD TOTAL

Este script es la herramienta definitiva para asegurar la salud del proyecto.
Verifica tres áreas críticas:
1.  Importaciones Locales: Detecta `ModuleNotFoundError` antes de que ocurran.
2.  Dependencias Externas: Comprueba si todas las librerías están instaladas.
3.  Sincronización de `requirements.txt`: Avisa si hay dependencias no documentadas o en desuso.

Uso:
  python verificador_integridad.py
"""
import os
import sys
import ast
import importlib.util
import logging
import re

# --- Configuración ---
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
logging.basicConfig(level=logging.INFO, format='%(message)s')
sys.path.insert(0, PROJECT_ROOT)

# --- Funciones de Ayuda ---

def get_installed_packages():
    """Obtiene una lista de paquetes de terceros instalados."""
    try:
        from importlib.metadata import distributions
        return {dist.metadata['Name'].lower() for dist in distributions()}
    except Exception:
        return set()

def get_std_lib_modules():
    """Obtiene la lista completa de módulos internos de Python."""
    # En Python 3.10+ existe stdlib_module_names
    try:
        return set(sys.stdlib_module_names)
    except AttributeError:
        # Fallback manual para versiones donde no esté disponible
        return set(sys.builtin_module_names) | {
            'os', 'sys', 'json', 're', 'logging', 'ast', 'io', 'random', 'shutil', 
            'importlib', 'subprocess', 'datetime', 'time', 'collections', 'sqlite3', 
            'math', 'hashlib', 'unicodedata', 'traceback', 're'
        }

def get_project_modules():
    """Genera una lista de todos los módulos locales del proyecto."""
    project_modules = set()
    for root, _, files in os.walk(PROJECT_ROOT):
        if '.venv' in root or '__pycache__' in root or '.git' in root:
            continue
        for file in files:
            if file.endswith('.py'):
                rel_path = os.path.relpath(os.path.join(root, file), PROJECT_ROOT)
                module_name = os.path.splitext(rel_path)[0].replace(os.sep, '.')
                project_modules.add(module_name)
                if '.' in module_name:
                    project_modules.add(module_name.split('.')[0])
    return project_modules

def get_requirements():
    """Lee y parsea el archivo requirements.txt."""
    requirements = set()
    try:
        with open(os.path.join(PROJECT_ROOT, 'requirements.txt'), 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    match = re.match(r'^[a-zA-Z0-9_-]+', line)
                    if match:
                        requirements.add(match.group(0).lower())
    except FileNotFoundError:
        pass
    return requirements

# --- Clase Principal de Verificación ---

class IntegrityVerifier:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.std_lib = get_std_lib_modules()
        self.installed = get_installed_packages()
        self.project_modules = get_project_modules()
        self.requirements = get_requirements()
        self.all_used_externals = set()

    def verify(self):
        """Ejecuta todas las verificaciones en el proyecto."""
        print("="*60)
        print("🛡️  INICIANDO VERIFICACIÓN DE INTEGRIDAD DEL PROYECTO")
        print("="*60)

        for root, _, files in os.walk(PROJECT_ROOT):
            if '.venv' in root or '__pycache__' in root or '.git' in root:
                continue
            for file in files:
                if file.endswith('.py'):
                    self._verify_file(os.path.join(root, file))
        
        self._verify_requirements_completeness()
        self._print_summary()

    def _verify_file(self, file_path):
        """Verifica las importaciones de un solo archivo."""
        rel_path = os.path.relpath(file_path, PROJECT_ROOT)
        print(f"\n--- Analizando: {rel_path} ---")
        found_issues = False
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().replace('\ufeff', '')
                tree = ast.parse(content, filename=file_path)
            
            for node in ast.walk(tree):
                module_to_check = None
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module_to_check = alias.name
                        if self._check_import(module_to_check, rel_path): found_issues = True
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    module_to_check = node.module
                    if self._check_import(module_to_check, rel_path): found_issues = True
        except Exception as e:
            self.errors.append(f"Error procesando '{rel_path}': {e}")
            print(f"  ❌ Error Inesperado: {e}")
            found_issues = True
        
        if not found_issues:
            print("  ✅ Sin problemas de importación.")

    def _check_import(self, module_name, file_path):
        """Clasifica y verifica un solo módulo importado."""
        top_level_module = module_name.split('.')[0]
        import_to_pkg = {
            'bs4': 'beautifulsoup4',
            'google': 'google-generativeai',
            'dotenv': 'python-dotenv',
            'statsapi': 'mlb-statsapi',
            'httpx': 'httpx',
            'mcp': 'fastmcp', # Dependencia para el servidor MCP unificado
            'cachetools': 'cachetools', # Para el caché del servidor MCP
            'playwright': 'playwright' # Para el scraper de UFC
        }

        if top_level_module in self.std_lib: return False

        if top_level_module in self.project_modules or module_name in self.project_modules:
            try:
                if importlib.util.find_spec(module_name) is None: 
                    # Intentar verificar si es un submodulo de un paquete que si existe
                    if '.' in module_name and importlib.util.find_spec(module_name.split('.')[0]) is not None:
                        return False
                    raise ImportError
            except (ImportError, ModuleNotFoundError):
                self.errors.append(f"Importación Rota en '{file_path}': No se puede encontrar el módulo local '{module_name}'.")
                print(f"  ❌ ROTO (Local): 'from {module_name} import ...'")
                return True
            return False

        pkg_name = import_to_pkg.get(top_level_module.lower(), top_level_module.lower())
        self.all_used_externals.add(pkg_name)
        
        if pkg_name not in self.installed:
            self.errors.append(f"Dependencia Faltante en '{file_path}': Paquete '{pkg_name}' no instalado. Ejecuta 'pip install {pkg_name}'.")
            print(f"  ❌ NO INSTALADO: '{pkg_name}' (usa 'pip install ...')")
            return True
        return False

    def _verify_requirements_completeness(self):
        """Compara los módulos externos usados con requirements.txt."""
        if not os.path.exists(os.path.join(PROJECT_ROOT, 'requirements.txt')): self.warnings.append("'requirements.txt' no existe.")
        import_to_pkg = {
            'bs4': 'beautifulsoup4', 
            'google': 'google-generativeai', 
            'dotenv': 'python-dotenv',
            'statsapi': 'mlb-statsapi'
        }
        mapped_used = {import_to_pkg.get(m, m) for m in self.all_used_externals}
        for pkg in mapped_used - self.requirements: self.warnings.append(f"Dependencia No Documentada: '{pkg}' se usa pero no está en requirements.txt.")
        for pkg in self.requirements - mapped_used: self.warnings.append(f"Dependencia No Utilizada: '{pkg}' está en requirements.txt pero no se usa.")

    def _print_summary(self):
        """Imprime el resumen final de la verificación."""
        print("\n" + "="*60 + "\n✅ RESUMEN DE INTEGRIDAD DEL PROYECTO\n" + "="*60)
        if not self.errors and not self.warnings:
            print("\n🎉 ¡Excelente! No se encontraron problemas de dependencias o importaciones.\nEl programa debería lanzarse sin errores de 'ModuleNotFoundError'.")
        else:
            if self.errors:
                print("\n❌ ERRORES CRÍTICOS (Deben ser solucionados):")
                for error in self.errors: print(f"  - {error}")
            if self.warnings:
                print("\n⚠️ ADVERTENCIAS (Recomendado revisar):")
                for warning in self.warnings: print(f"  - {warning}")
        print("\n" + "="*60)

if __name__ == "__main__":
    verifier = IntegrityVerifier()
    verifier.verify()