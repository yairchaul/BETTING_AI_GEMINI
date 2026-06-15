import re

with open('visual_mlb.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Agregar K proyectados debajo del nombre del pitcher en el header
# Buscar la línea del pitcher visitante y local
old_ap = '<p style="color:#94a3b8;font-size:12px">🥎 {ap}</p>'
new_ap = '''<p style="color:#94a3b8;font-size:12px">🥎 {ap}</p>
        <p style="color:#f59e0b;font-size:10px">⚡ K/9: {k9_v} | Proy: {k_proy_v}K</p>'''

old_hp = '<p style="color:#94a3b8;font-size:12px">🥎 {hp}</p>'
new_hp = '''<p style="color:#94a3b8;font-size:12px">🥎 {hp}</p>
        <p style="color:#f59e0b;font-size:10px">⚡ K/9: {k9_h} | Proy: {k_proy_h}K</p>'''

# Necesitamos agregar las variables k9_v, k_proy_v, k9_h, k_proy_h
# Buscar donde se definen ap y hp y agregar el cálculo de K
old_pitchers = '''ap = pit.get("visitante", {}).get("nombre", "TBD") if isinstance(pit.get("visitante"), dict) else str(pit.get("visitante", "TBD"))
        hp = pit.get("local", {}).get("nombre", "TBD") if isinstance(pit.get("local"), dict) else str(pit.get("local", "TBD"))'''

new_pitchers = '''ap = pit.get("visitante", {}).get("nombre", "TBD") if isinstance(pit.get("visitante"), dict) else str(pit.get("visitante", "TBD"))
        hp = pit.get("local", {}).get("nombre", "TBD") if isinstance(pit.get("local"), dict) else str(pit.get("local", "TBD"))
        
        # Calcular K proyectados
        k9_v, k_proy_v, k9_h, k_proy_h = 0, 0, 0, 0
        try:
            from predictor_ponches import PredictorPonches
            pp = PredictorPonches()
            if ap in pp.pitchers_k:
                k9_v = pp.pitchers_k[ap]["k9"]
                k_proy_v = round(k9_v * 0.67, 1)
            if hp in pp.pitchers_k:
                k9_h = pp.pitchers_k[hp]["k9"]
                k_proy_h = round(k9_h * 0.67, 1)
        except:
            pass'''

if old_pitchers in content:
    content = content.replace(old_pitchers, new_pitchers)
    content = content.replace(old_ap, new_ap)
    content = content.replace(old_hp, new_hp)
    print("✅ K proyectados agregados a la tarjeta")
else:
    print("⚠️ No se encontró el patrón exacto de pitchers")

with open('visual_mlb.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ visual_mlb.py actualizado con K proyectados")
