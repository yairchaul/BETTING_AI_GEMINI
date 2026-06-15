# -*- coding: utf-8 -*-
"""
VISUAL MLB PRO - Version corregida
"""

import streamlit as st
import plotly.express as px
import pandas as pd
import os
import json

class VisualMLBPro:
    def render(self, partido, idx, tracker, analisis_mlb=None, clima_engine=None, **kwargs):
        """Renderiza partido MLB"""
        
        # Datos basicos con valores por defecto
        local = partido.get('local', 'Local')
        visitante = partido.get('visitante', 'Visitante')
        local_rec = partido.get('local_record', '0-0')
        visit_rec = partido.get('visitante_record', '0-0')
        odds = partido.get('odds', {})
        local_streak = partido.get('local_streak', '')
        visitante_streak = partido.get('visitante_streak', '')
        ou = odds.get('over_under', 'N/A')
        
        pitchers = partido.get('pitchers', {})
        pitcher_local = pitchers.get('local', {}).get('nombre', 'TBD')
        pitcher_visitante = pitchers.get('visitante', {}).get('nombre', 'TBD')
        hora = partido.get('hora', 'TBD')
        venue = partido.get('venue', 'TBD')
        
        ml_local = odds.get('moneyline', {}).get('local', 'N/A')
        ml_visit = odds.get('moneyline', {}).get('visitante', 'N/A')
        
        # Header con columnas de Streamlit (evita HTML problemático)
        st.markdown(f"### ⚾ {local} vs {visitante}")
        st.caption(f"📅 {hora} | 🏟️ {venue}")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f"**🏠 {local}**")
            st.caption(f"Record: {local_rec} {local_streak}")
            st.metric("Moneyline", ml_local)
            st.caption(f"🥎 {pitcher_local}")
        
        with col2:
            st.markdown("**VS**")
            st.metric("Over/Under", ou)
            st.caption("MLB")
        
        with col3:
            st.markdown(f"**✈️ {visitante}**")
            st.caption(f"Record: {visit_rec} {visitante_streak}")
            st.metric("Moneyline", ml_visit)
            st.caption(f"🥎 {pitcher_visitante}")
        
        st.divider()
        
        # Mostrar analisis si existe
        if analisis_mlb:
            pick = analisis_mlb.get('pick', 'N/A')
            confianza = analisis_mlb.get('confianza', 0)
            
            if confianza >= 70:
                st.success(f"🎯 RECOMENDACION: {pick} (Confianza: {confianza}%)")
            elif confianza >= 50:
                st.info(f"🎯 RECOMENDACION: {pick} (Confianza: {confianza}%)")
            else:
                st.warning(f"🎯 RECOMENDACION: {pick} (Confianza: {confianza}%)")
        
        # Boton
        if st.button("🔍 Analizar MLB", key=f"mlb_btn_{idx}", use_container_width=True):
            return "analizar"
        
        return None

visual_mlb_pro = VisualMLBPro()
