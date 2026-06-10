import re

print("=" * 60)
print("🔍 VERIFICANDO DATOS ENVIADOS A GEMINI DESDE VISUAL_MLB.PY")
print("=" * 60)

with open('visual_mlb.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Buscar el contexto_ia que se construye
match = re.search(r'contexto_ia\s*=\s*\{.*?\}', content, re.DOTALL)
if match:
    print("✅ CONTEXTO ENVIADO A GEMINI:")
    print(match.group(0)[:500])
else:
    print("❌ No se encontró contexto_ia")
    # Buscar la llamada a gemini
    match2 = re.search(r'gemini\.orquestrar_decision_final\(.*?\)', content, re.DOTALL)
    if match2:
        print(f"⚠️ Llamada a Gemini (sin contexto_ia):\n{match2.group(0)[:300]}")
