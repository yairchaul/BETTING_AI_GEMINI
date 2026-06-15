import re

print("=" * 60)
print("🔍 VERIFICANDO CEREBRO_GEMINI_PRO.PY")
print("=" * 60)

with open('cerebro_gemini_pro.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Verificar si tiene el prompt NUEVO o VIEJO
if 'LANZADORES CONFIRMADOS' in content or 'LANZADORES:' in content:
    print("✅ PROMPT NUEVO ENCONTRADO (incluye pitchers, WHIP, K, O/U)")
elif 'None vs None' in content:
    print("❌ PROMPT VIEJO ENCONTRADO (dice 'None vs None')")
elif '_build_mlb_json_prompt' in content:
    # Ver el contenido de _build_mlb_json_prompt
    match = re.search(r'def _build_mlb_json_prompt.*?return f""".*?"""', content, re.DOTALL)
    if match:
        texto = match.group(0)
        if 'LANZADORES' in texto or 'pitcher_v' in texto or 'whip_v' in texto:
            print("✅ PROMPT NUEVO (incluye pitcher_v, whip_v, k_proy_v)")
        elif 'None vs None' in texto:
            print("❌ PROMPT VIEJO (dice 'None vs None')")
        else:
            print(f"⚠️ CONTENIDO DEL PROMPT:\n{texto[:300]}")
else:
    print("⚠️ No se encontró la función _build_mlb_json_prompt")
    # Buscar cualquier función de prompt
    funcs = re.findall(r'def (\w+)\(', content)
    print(f"   Funciones encontradas: {funcs}")
