# fix_gemini.py
import os
import sys
from dotenv import load_dotenv

print("🔍 DIAGNÓSTICO DE GEMINI")
print("="*40)

# 1. Verificar archivo .env
env_path = ".env"
if os.path.exists(env_path):
    print("✅ Archivo .env encontrado")
    load_dotenv()
else:
    print("❌ Archivo .env NO encontrado")
    print("   Creando archivo .env...")
    api_key = input("📝 Ingresa tu GEMINI_API_KEY: ")
    with open(".env", "w") as f:
        f.write(f"GEMINI_API_KEY={api_key}")
    load_dotenv()
    print("✅ .env creado")

# 2. Verificar API key
gemini_key = os.getenv("GEMINI_API_KEY")
if gemini_key:
    print(f"✅ GEMINI_API_KEY encontrada: {gemini_key[:10]}...")
else:
    print("❌ GEMINI_API_KEY no encontrada")

# 3. Probar conexión a Gemini
if gemini_key:
    try:
        import google.generativeai as genai
        genai.configure(api_key=gemini_key)
        
        # Listar modelos disponibles
        models = genai.list_models()
        available = [m.name for m in models if 'generateContent' in m.supported_generation_methods]
        
        if available:
            print(f"✅ Gemini disponible. Modelos: {len(available)}")
            # Probar modelo rápido
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content("Responde solo OK")
            print(f"✅ Prueba exitosa: {response.text}")
        else:
            print("❌ No hay modelos disponibles")
    except ImportError:
        print("❌ google-generativeai no instalado")
        print("   Ejecuta: pip install google-generativeai")
    except Exception as e:
        print(f"❌ Error: {e}")

print("="*40)
