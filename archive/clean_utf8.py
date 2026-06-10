# clean_utf8.py
import os
import sys

def fix_encoding_issues():
    paths_to_fix = [
        "cerebro_gemini_pro.py",
        "main_vision_completo.py",
        "visual_nba_mejorado.py",
        "visual_mlb.py",
        "visual_ufc_final.py"
    ]
    
    for path in paths_to_fix:
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8-sig') as f:
                    content = f.read()
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"✅ Corregido: {path}")
            except Exception as e:
                print(f"⚠️ Error en {path}: {e}")

if __name__ == "__main__":
    fix_encoding_issues()
