import re

with open('visual_mlb.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Agregar recomendaciones múltiples después del resultado del botón
old_result_block = '''if "EVITAR" in d:
                st.warning(d)'''

new_result_block = '''if "EVITAR" in d:
                st.warning(d)
                st.caption("📊 Opciones alternativas:")
                col_a1, col_a2 = st.columns(2)
                with col_a1:
                    ou_rec = "OVER" if resultado_ou and resultado_ou.get('recomendacion') == 'OVER' else "UNDER"
                    st.info(f"📈 {ou_rec} {ou}")
                with col_a2:
                    k_rec = f"OVER {k_proy_away}K" if k_proy_away > 5.5 else f"UNDER {k_proy_away}K"
                    st.info(f"⚡ {k_rec}")'''

if old_result_block in content:
    content = content.replace(old_result_block, new_result_block)
    print('✅ Análisis Blindado ahora sugiere O/U y K cuando es EVITAR')
else:
    print('⚠️ No se encontró el bloque EVITAR')

with open('visual_mlb.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ visual_mlb.py actualizado')
