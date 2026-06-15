# -*- coding: utf-8 -*-
import streamlit as st
import json
import os

def mostrar_analisis_ia():
    st.subheader("🧠 Análisis Estratégico de DeepSeek R1")
    
    path_analisis = os.path.join("data", "analisis_ia_rendimiento.json")
    
    if os.path.exists(path_analisis):
        with open(path_analisis, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Precisión Global", data.get("precision_global", "N/A"))
        with col2:
            st.metric("Mejor Deporte", data.get("mejor_deporte", "N/A"))
        with col3:
            st.error(f"Peor Deporte: {data.get('peor_deporte', 'N/A')}")
            
        st.info(f"**Conclusión del Agente:** {data.get('conclusión', 'Sin datos')}")
    else:
        st.warning("No hay análisis de IA disponible. Ejecuta 'automation_deepseek_r1.py' para generarlo.")

if __name__ == "__main__":
    st.title("Test UI Rendimiento")
    mostrar_analisis_ia()