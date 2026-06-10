# -*- coding: utf-8 -*-
import streamlit as st

class VisualNBAProps:
    def __init__(self):
        self.header_color = "#f59e0b"  # Color naranja/ámbar para NBA

    def render_prop_card(self, prop_data):
        """
        Dibuja una tarjeta individual para una apuesta de jugador (Prop)
        """
        with st.container():
            st.markdown(f"""
            <div style="padding:15px; border-radius:10px; background: rgba(245, 158, 11, 0.1); border: 1px solid {self.header_color}; margin-bottom: 10px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-weight: bold; color: white; font-size: 1.1rem;">👤 {prop_data.get('jugador', 'Jugador Desconocido')}</span>
                    <span style="background: {self.header_color}; color: black; padding: 2px 8px; border-radius: 5px; font-weight: bold;">
                        {prop_data.get('prediccion', 'N/A')}
                    </span>
                </div>
                <div style="margin-top: 8px; color: #94a3b8;">
                    Prop: <strong>{prop_data.get('linea', '0.0')} {prop_data.get('prop', 'puntos')}</strong>
                </div>
                <div style="margin-top: 5px; font-size: 0.9rem; color: #4ade80;">
                    🎯 Confianza: {prop_data.get('confianza', 0)}%
                </div>
            </div>
            """, unsafe_allow_html=True)

    def render(self, lista_props, idx=0):
        """
        Método principal llamado por el main para mostrar las props
        """
        if not lista_props:
            st.info("No hay props analizadas para este partido aún.")
            return

        st.subheader("🔥 Mejores Props del Encuentro")
        for prop in lista_props:
            self.render_prop_card(prop)

if __name__ == "__main__":
    print("Módulo Visual NBA Props cargado correctamente.")
