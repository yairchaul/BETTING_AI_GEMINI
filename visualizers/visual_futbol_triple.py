# -*- coding: utf-8 -*-
"""
VISUAL FUTBOL TRIPLE - Muestra partidos de fútbol con formato de 3 columnas (Local, Empate, Visitante)
"""
import streamlit as st

class VisualFutbolTriple:
    def __init__(self):
        self.colores = {
            'local': '#3b82f6',    # Blue
            'visitante': '#ef4444', # Red
            'empate': '#fbbf24',   # Amber
            'fondo': '#1f2937',
            'texto': '#e5e7eb'
        }

    def render(self, partido, idx, liga, tracker=None, analisis_heuristico=None, analisis_ia=None, **kwargs):
        """Renderiza un partido de fútbol con formato de 3 columnas."""
        
        local = partido.get('home', 'Local')
        visitante = partido.get('away', 'Visitante')
        fecha = partido.get('fecha_partido', 'Fecha no disponible')
        
        # Extraer datos adicionales para una vista más completa
        local_logo = partido.get('local_logo', '')
        visitante_logo = partido.get('visitante_logo', '')
        local_record = partido.get('local_record', '0-0-0')
        visitante_record = partido.get('visitante_record', '0-0-0')
        local_streak = partido.get('local_streak', '')
        visitante_streak = partido.get('visitante_streak', '')
        
        odds = partido.get('odds', {})
        moneyline = odds.get('moneyline', {})
        ml_local = moneyline.get('home', 'N/A')
        ml_empate = moneyline.get('draw', 'N/A')
        ml_visitante = moneyline.get('away', 'N/A')
        
        st.markdown(f"""
        <div style="background: {self.colores['fondo']}; padding: 15px; border-radius: 10px; margin-bottom: 15px; border-left: 4px solid {self.colores['local']};">
            <!-- Header con logos, récords y rachas -->
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <div style="display: flex; align-items: center; gap: 10px; flex: 1;">
                    <img src="{local_logo}" width="25" height="25" style="object-fit: contain; background: white; border-radius: 50%;">
                    <span style="color: {self.colores['texto']}; font-weight: bold;">{local}</span>
                    <small style="color: #9ca3af;">{local_record} ({local_streak})</small>
                </div>
                <span style="color: #9ca3af; font-size: 0.9em; margin: 0 10px;">vs</span>
                <div style="display: flex; align-items: center; gap: 10px; flex: 1; justify-content: flex-end;">
                    <small style="color: #9ca3af;">{visitante_record} ({visitante_streak})</small>
                    <span style="color: {self.colores['texto']}; font-weight: bold;">{visitante}</span>
                    <img src="{visitante_logo}" width="25" height="25" style="object-fit: contain; background: white; border-radius: 50%;">
                </div>
            </div>
            <div style="text-align: center; color: #9ca3af; font-size: 0.9em; border-top: 1px solid #374151; padding-top: 5px; margin-bottom: 10px;">
                📅 {fecha}
            </div>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; text-align: center;">
                <div>
                    <div style="background: rgba(59, 130, 246, 0.1); padding: 10px; border-radius: 8px;">
                        <p style="margin: 0; font-size: 0.9em; color: #9ca3af;">Gana Local</p>
                        <p style="margin: 5px 0 0 0; font-size: 1.2em; font-weight: bold; color: {self.colores['local']};">{ml_local}</p>
                    </div>
                </div>
                <div>
                    <div style="background: rgba(251, 191, 36, 0.1); padding: 10px; border-radius: 8px;">
                        <p style="margin: 0; font-size: 0.9em; color: #9ca3af;">Empate</p>
                        <p style="margin: 5px 0 0 0; font-size: 1.2em; font-weight: bold; color: {self.colores['empate']};">{ml_empate}</p>
                    </div>
                </div>
                <div>
                    <div style="background: rgba(239, 68, 68, 0.1); padding: 10px; border-radius: 8px;">
                        <p style="margin: 0; font-size: 0.9em; color: #9ca3af;">Gana Visitante</p>
                        <p style="margin: 5px 0 0 0; font-size: 1.2em; font-weight: bold; color: {self.colores['visitante']};">{ml_visitante}</p>
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Mostrar análisis si está disponible
        if analisis_heuristico:
            pick = analisis_heuristico.get('pick', 'N/A')
            confianza = analisis_heuristico.get('confianza', 0)
            regla = analisis_heuristico.get('regla', 'N/A')
            
            st.markdown(f"""
            <div style="background: #2d3748; padding: 10px; border-radius: 8px; margin-top: -10px; margin-bottom: 10px;">
                <p style="margin: 0; color: #a0aec0;">
                    <b>Análisis Heurístico:</b> {pick} (Conf: {confianza:.1f}%, Regla: #{regla})
                </p>
            </div>
            """, unsafe_allow_html=True)

        if analisis_ia:
            pick_ia = analisis_ia.get('pick', 'N/A')
            conf_ia = analisis_ia.get('confianza', 0)
            st.markdown(f"""
            <div style="background: #2d3748; padding: 10px; border-radius: 8px; margin-top: -10px; margin-bottom: 10px;">
                <p style="margin: 0; color: #a0aec0;">
                    <b>Análisis IA:</b> {pick_ia} (Conf: {conf_ia}%)
                </p>
            </div>
            """, unsafe_allow_html=True)

        # Botón de análisis
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            button_text = "🔄 Actualizar Análisis" if analisis_heuristico else "🔍 Analizar Partido"
            if st.button(button_text, key=f"futbol_btn_{liga}_{idx}", use_container_width=True):
                return "analizar"
        
        return None