# test_ias.py
import os
from dotenv import load_dotenv

load_dotenv()

print("\n🔍 DIAGNÓSTICO DE IAS")
print("="*40)

gemini_key = os.getenv("GEMINI_API_KEY")
groq_key = os.getenv("GROQ_API_KEY")

if gemini_key and gemini_key.startswith("AIza"):
    print("✅ GEMINI_API_KEY válida")
else:
    print("❌ GEMINI_API_KEY inválida o no encontrada")

if groq_key and groq_key.startswith("gsk_"):
    print("✅ GROQ_API_KEY válida")
else:
    print("❌ GROQ_API_KEY inválida o no encontrada")

# Probar conexión Groq
if groq_key and groq_key.startswith("gsk_"):
    try:
        from groq import Groq
        client = Groq(api_key=groq_key)
        print("✅ Groq cliente creado correctamente")
    except Exception as e:
        print(f"❌ Error con Groq: {e}")

print("="*40)
