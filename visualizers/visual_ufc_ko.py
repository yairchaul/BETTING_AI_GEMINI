# -*- coding: utf-8 -*-
import streamlit as st

class VisualUFCKO:
    def __init__(self):
        self.color_ko = "#ff4b4b"
        self.color_sub = "#3b82f6"

    def render_ko_prediction(self, p1_nombre, p2_nombre, probabilidad_ko):
        """
        Renderiza la tarjeta visual de predicción de KO
        """
        st.markdown(f"""
        <div style="padding:15px; border-radius:10px; background: rgba(255, 75, 75, 0.1); border: 1px solid {self.color_ko}">
            <h4 style="margin:0; color:{self.color_ko}">🔥 ALERTA DE FINALIZACIÓN</h4>
            <p style="margin:5px 0 0 0">Probabilidad de KO/TKO: <strong>{probabilidad_ko}%</strong></p>
            <div style="width:100%; background:#262730; border-radius:5px; margin-top:10px">
                <div style="width:{probabilidad_ko}%; background:{self.color_ko}; height:10px; border-radius:5px"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    def render(self, datos, idx, tracker):
        # Método genérico para que el main no rompa al llamar .render()
        st.write(f"Análisis de KO para combate {idx}")
        self.render_ko_prediction(datos.get('p1','Peleador 1'), datos.get('p2','Peleador 2'), 75)
