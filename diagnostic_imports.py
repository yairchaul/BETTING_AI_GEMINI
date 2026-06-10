# diagnostic_imports.py
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(__file__))

print("🔍 DIAGNÓSTICO DE IMPORTS")
print("="*40)

# Verificar cada módulo
modulos = [
    ("motors", "Carpeta motors"),
    ("scrapers", "Carpeta scrapers"),
    ("visualizers", "Carpeta visualizers"),
    ("utils", "Carpeta utils"),
]

for modulo, desc in modulos:
    if os.path.isdir(modulo):
        print(f"✅ {desc}: '{modulo}' existe")
        # Verificar si tiene __init__.py
        init_file = os.path.join(modulo, "__init__.py")
        if os.path.exists(init_file):
            print(f"   ✅ {modulo}/__init__.py existe")
        else:
            print(f"   ⚠️ {modulo}/__init__.py falta (crealo)")
    else:
        print(f"❌ {desc}: '{modulo}' NO existe")

# Probar importar motors
try:
    import motors
    print("✅ motors importado correctamente")
except ImportError as e:
    print(f"❌ Error importando motors: {e}")
