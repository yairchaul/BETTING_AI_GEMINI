import re

with open('visual_mlb.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Buscar la línea de cada candidato HR y agregar pitcher rival
old_hr_line = 'st.caption(f"💣 {hr} HR")'
new_hr_line = 'st.caption(f"💣 {hr} HR | 🧤 vs {hp if b.get(\"equipo\",\"\") == away else ap}")'

if old_hr_line in content:
    content = content.replace(old_hr_line, new_hr_line)
    print('✅ Pitcher rival agregado en Candidatos HR')
else:
    print('⚠️ Buscando línea de HR...')
    if '💣 {hr} HR' in content:
        content = content.replace(
            'st.caption(f"💣 {hr} HR")',
            'st.caption(f"💣 {hr} HR | 🧤 vs {hp if b.get(\"equipo\",\"\") == away else ap}")'
        )
        print('   Agregado por parche')

with open('visual_mlb.py', 'w', encoding='utf-8') as f:
    f.write(content)
