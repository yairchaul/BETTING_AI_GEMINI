# check_syntax.py
import ast
import sys
import os

def check_syntax(file_path):
    """Verifica la sintaxis de un archivo Python"""
    try:
        if not os.path.exists(file_path):
            return False
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            content = f.read()
        ast.parse(content)
        print(f"✅ {file_path} - Sintaxis correcta")
        return True
    except SyntaxError as e:
        print(f"❌ {file_path} - Error en línea {e.lineno}: {e.msg}")
        print(f"   {e.text.strip() if e.text else ''}")
        return False

if __name__ == "__main__":
    files_to_check = [
        "main_vision_completo.py",
        os.path.join("visualizers", "visual_mlb.py"),
        os.path.join("visualizers", "visual_nba_mejorado.py"), # Corrected path
        os.path.join("visualizers", "visual_ufc_final.py"), # Corrected path
        os.path.join("visualizers", "visual_futbol_triple.py") # Corrected path
    ]

    print("\n" + "="*50)
    print("   VERIFICANDO SINTAXIS DE ARCHIVOS")
    print("="*50 + "\n")
    
    all_ok = True
    for file in files_to_check:
        if not check_syntax(file):
            all_ok = False
    
    if all_ok: print("\n✅ TODOS los archivos tienen sintaxis correcta")
    else: print("\n❌ Algunos archivos tienen errores de sintaxis")