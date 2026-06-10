# -*- coding: utf-8 -*-

with open('visual_mlb.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Reemplazar la obtención de K/9 desde predictor_ponches por motor_lanzadores
old_k = '''try:
            from predictor_ponches import PredictorPonches
            pp = PredictorPonches()
            if ap in pp.pitchers_k:
                k9_away = pp.pitchers_k[ap].get("k9", 0)
                k_proy_away = round(k9_away * 0.67, 1)
            if hp in pp.pitchers_k:
                k9_home = pp.pitchers_k[hp].get("k9", 0)
                k_proy_home = round(k9_home * 0.67, 1)
        except:
            pass'''

new_k = '''try:
            from motors.motor_lanzadores import obtener_analisis_lanzadores
            datos_k = st.session_state.get("datos_k", {})
            if not datos_k:
                datos_k = obtener_analisis_lanzadores()
                st.session_state["datos_k"] = datos_k
            
            # Buscar K/9 para el pitcher visitante
            for equipo, info in datos_k.items():
                if ap and ap.lower() in info.get("lanzador", "").lower():
                    k9_away = info.get("k9", 0)
                    k_proy_away = info.get("k_proyectados", 0)
                    break
                if ap and info.get("lanzador", "").lower() in ap.lower():
                    k9_away = info.get("k9", 0)
                    k_proy_away = info.get("k_proyectados", 0)
                    break
            
            # Buscar K/9 para el pitcher local
            for equipo, info in datos_k.items():
                if hp and hp.lower() in info.get("lanzador", "").lower():
                    k9_home = info.get("k9", 0)
                    k_proy_home = info.get("k_proyectados", 0)
                    break
                if hp and info.get("lanzador", "").lower() in hp.lower():
                    k9_home = info.get("k9", 0)
                    k_proy_home = info.get("k_proyectados", 0)
                    break
        except:
            pass'''

if old_k in content:
    content = content.replace(old_k, new_k)
    print('✅ K/9 ahora se obtiene desde MLB Stats API (motor_lanzadores)')
else:
    print('⚠️ No se encontró el bloque de K/9')

with open('visual_mlb.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ visual_mlb.py actualizado')
