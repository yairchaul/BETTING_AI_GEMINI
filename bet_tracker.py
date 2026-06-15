"""
BET TRACKER - Sistema de seguimiento de apuestas
"""
import streamlit as st
from datetime import datetime

class BetTracker:
    def __init__(self):
        if 'history' not in st.session_state:
            st.session_state.history = []
        if 'parlays' not in st.session_state:
            st.session_state.parlays = []
    
    def agregar_pick(self, pick):
        pick['timestamp'] = datetime.now().isoformat()
        pick['estado'] = 'Pendiente'
        st.session_state.history.append(pick)
    
    def guardar_parlay(self, nombre="Parlay"):
        if not st.session_state.history:
            return None
        
        parlay = {
            'id': f"P{len(st.session_state.parlays)+1}",
            'nombre': nombre,
            'fecha': datetime.now().isoformat(),
            'picks': st.session_state.history.copy(),
            'cuota_total': self._calcular_cuota(st.session_state.history),
            'estado': 'Activo'
        }
        
        st.session_state.parlays.append(parlay)
        st.session_state.history = []
        return parlay
    
    def _calcular_cuota(self, picks):
        cuota = 1.0
        for pick in picks:
            cuota *= pick.get('cuota', 2.0)
        return round(cuota, 2)
    
    def render_sidebar_tracker(self):
        st.sidebar.markdown("---")
        st.sidebar.subheader("📋 MI PARLAY")
        
        if st.session_state.history:
            for i, pick in enumerate(st.session_state.history):
                st.sidebar.markdown(f"{i+1}. {pick.get('partido', '')[:20]} - {pick.get('pick', '')[:15]}")
            
            cuota = self._calcular_cuota(st.session_state.history)
            st.sidebar.metric("CUOTA TOTAL", f"{cuota:.2f}")
            
            col1, col2 = st.sidebar.columns(2)
            with col1:
                if st.button("💾 GUARDAR", key="guardar_parlay"):
                    self.guardar_parlay()
                    st.rerun()
            with col2:
                if st.button("🧹 LIMPIAR", key="limpiar_parlay"):
                    st.session_state.history = []
                    st.rerun()
        else:
            st.sidebar.info("💡 Agrega picks desde los partidos")
