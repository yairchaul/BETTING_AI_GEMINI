import importlib
import os

def diagnostico():
    print("\n" + "="*40)
    print("🔍 AUDITORÍA DE MÓDULOS - BETTING_AI")
    print("="*40)
    
    # Lista de archivos y las clases que DEBEN tener dentro
    configuracion = {
        "analizador_premium_profesional": ["AnalizadorPremiumProfesional"],
        "calculador_probabilidades_futbol": ["CalculadorProbabilidadesFutbol"],
        "analizador_gemini_nba": ["AnalizadorIANBA"],
        "config_api": ["API_KEY"]
    }

    faltantes = 0
    for mod_name, clases in configuracion.items():
        try:
            modulo = importlib.import_module(mod_name)
            print(f"✅ {mod_name:30} | ENCONTRADO")
            for clase in clases:
                if hasattr(modulo, clase):
                    print(f"   └── ⭐ Clase '{clase}': OK")
                else:
                    print(f"   └── ❌ ERROR: Falta la clase '{clase}'")
                    faltantes += 1
        except ImportError:
            print(f"❌ {mod_name:30} | NO EXISTE EL ARCHIVO")
            faltantes += 1
    
    print("\n" + "="*40)
    if faltantes == 0:
        print("💎 TODO PERFECTO: Puedes lanzar main_vision_completo.py")
    else:
        print(f"⚠️  TIENES {faltantes} ERRORES PENDIENTES")
    print("="*40 + "\n")

if __name__ == "__main__":
    diagnostico()
