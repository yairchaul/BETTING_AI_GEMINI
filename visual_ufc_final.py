# -*- coding: utf-8 -*-
"""VISUAL UFC FINAL - CON IA (GROQ + GEMINI)"""
import streamlit as st
import json
import logging

logger = logging.getLogger(__name__)

class VisualUFCFinal:
    def __init__(self):
        self.odds_caliente = {}
        self.peleadores_reales = []
        self.db_path = "data/betting_stats.db" # Para el tracking de picks
    
    def render(self, partido, idx, tracker, analisis=None):
        p1_data = partido.get('peleador1', {})
        p2_data = partido.get('peleador2', {})
        
        p1_nombre = p1_data.get('nombre', 'Peleador 1')
        p2_nombre = p2_data.get('nombre', 'Peleador 2')
        p1_record = p1_data.get('record', 'N/A')
        p2_record = p2_data.get('record', 'N/A')
        p1_altura = p1_data.get('altura', 0)
        p2_altura = p2_data.get('altura', 0)
        p1_alcance = p1_data.get('alcance', 0)
        p2_alcance = p2_data.get('alcance', 0)
        p1_ko = p1_data.get('ko_rate', 'N/A')
        p1_sub = p1_data.get('sub_rate', 'N/A')
        p1_dec = p1_data.get('dec_rate', 'N/A')
        p2_ko = p2_data.get('ko_rate', 'N/A')
        p2_sub = p2_data.get('sub_rate', 'N/A')
        p2_dec = p2_data.get('dec_rate', 'N/A')
        
        p1_odds = self.odds_caliente.get(p1_nombre, p1_data.get('odds', 'N/A'))
        p2_odds = self.odds_caliente.get(p2_nombre, p2_data.get('odds', 'N/A'))
        
        # Lógica para detectar al favorito visualmente
        p1_is_fav = str(p1_odds).startswith('-')
        p2_is_fav = str(p2_odds).startswith('-')
        
        # Header NEON
        glow_class = "favorite-gold-card" if (p1_is_fav or p2_is_fav) else ""
        
        st.markdown(f"""
        <div class='{glow_class}' style='background: linear-gradient(135deg, #0f0f1a 0%, #1a1f2a 100%); 
                    border-radius: 15px; padding: 20px; margin: 15px 0; 
                    border: 1px solid {"#fbbf24" if glow_class else "#334155"};'>
            <div style='display: flex; justify-content: space-between;'>
                <div style='text-align: center; flex: 1;'>
                    <h2 style='color: #fff; margin:0;'>{p1_nombre}</h2>
                    <p style='color: #fbbf24; font-weight:bold;'>{"⭐ FAVORITO" if p1_is_fav else ""} 🎲 {p1_odds}</p>
                </div>
                <div style='text-align: center; flex: 0.5;'>
                    <h1 style='color: {"#fbbf24" if glow_class else "#00ff41"}; margin:0;'>VS</h1>
                </div>
                <div style='text-align: center; flex: 1;'>
                    <h2 style='color: #fff; margin:0;'>{p2_nombre}</h2>
                    <p style='color: #fbbf24; font-weight:bold;'>{"⭐ FAVORITO" if p2_is_fav else ""} 🎲 {p2_odds}</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            # Resaltar en ROJO si fue noqueado recientemente
            p1_vulnerable = p1_data.get('was_koed_recently', False)
            color_n1 = "#ff4b4b" if p1_vulnerable else "#fff"
            st.markdown(f"<b style='color:{color_n1};'>🔴 {p1_nombre}</b>", unsafe_allow_html=True)
            if p1_vulnerable: st.caption("⚠️ **VULNERABLE:** Viene de derrota por KO")
            st.caption(f"📊 Récord: {p1_record}")
            st.caption(f"📏 Altura: {p1_altura}cm | Alcance: {p1_alcance}cm")
            st.caption(f"🥊 KO: {p1_ko}% | 🥋 Sub: {p1_sub}% | ⚖️ Dec: {p1_dec}%")

        with col2:
            p2_vulnerable = p2_data.get('was_koed_recently', False)
            color_n2 = "#ff4b4b" if p2_vulnerable else "#fff"
            st.markdown(f"<b style='color:{color_n2};'>🔵 {p2_nombre}</b>", unsafe_allow_html=True)
            if p2_vulnerable: st.caption("⚠️ **VULNERABLE:** Viene de derrota por KO")
            st.caption(f"📊 Récord: {p2_record}")
            st.caption(f"📏 Altura: {p2_altura}cm | Alcance: {p2_alcance}cm")
            st.caption(f"🥊 KO: {p2_ko}% | 🥋 Sub: {p2_sub}% | ⚖️ Dec: {p2_dec}%")

        # Mostrar ventaja física
        if p1_alcance and p2_alcance and p1_alcance != p2_alcance:
            ventaja = p1_nombre if p1_alcance > p2_alcance else p2_nombre
            st.markdown(f"<div style='text-align:center;'><small style='color:#fbbf24;'>📏 Ventaja de Alcance: <b>{ventaja}</b></small></div>", unsafe_allow_html=True)

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🔥 ANALIZAR UFC", key=f"ufc_analizar_{p1_nombre}_{p2_nombre}_{idx}", use_container_width=True):
                if p1_record != 'N/A' and p2_record != 'N/A':
                    return "analizar"
                else:
                    st.error("❌ DATOS INSUFICIENTES")
        
        if analisis:
            st.markdown("---")
            st.markdown("###  VEREDICTO FINAL")

            ganador = analisis.get('ganador', 'N/A')
            confianza = analisis.get('confianza', 0)
            color_h = "#00ff41" if confianza >= 60 else "#ffcc00"
            
            st.markdown(f"""
            <div style='background: linear-gradient(135deg, #1a1f2a 0%, #0f1419 100%); 
                        border-radius: 12px; padding: 15px; margin: 10px 0; 
                        border-left: 4px solid {color_h};'>
                <h4 style='color: {color_h}; margin: 0;'>🎯 HEURÍSTICO: {ganador}</h4>
                <p style='color: #00ff41; margin:0;'>Confianza: {confianza}%</p>
            </div>
            """, unsafe_allow_html=True)
            
            if 'individual_ia_results' in analisis:
                with st.expander("🔍 Desglose de Votación (Todas las IAs)"):
                    for res in analisis['individual_ia_results']:
                        ia_pick = res.get('pick', 'N/A')
                        ia_conf = res.get('confianza', 0)
                        st.write(f"🤖 **IA**: {ia_pick} ({ia_conf}%)")
                        st.caption(f"💬 {res.get('razon', '')}")

                gem_winner = analisis.get('gemini_pick', 'N/A')
                gem_conf = analisis.get('gemini_confidence', 0)
                gem_method = analisis.get('gemini_method', 'N/A')
                gem_reason = analisis.get('gemini_reason', '')
                
                color_g = "#00ff41" if gem_conf >= 60 else "#ffcc00"
                
                st.markdown(f"""
                <div style='background: linear-gradient(135deg, #1a1f2a 0%, #0f1419 100%); 
                            border-radius: 12px; padding: 15px; margin: 10px 0; 
                            border-left: 4px solid {color_g};'>
                    <h4 style='color: {color_g}; margin: 0;'>?? {gem_winner}</h4>
                    <p style='color: #00ff41;'>Confianza: {gem_conf}%</p>
                </div>
                """, unsafe_allow_html=True)
                if gem_method != 'N/A':
                    st.caption(f"?? M?todo Gemini: {gem_method}")
                if gem_reason:
                    st.caption(f"?? {gem_reason}")
        
        # Botón para agregar al parlay
        col_add1, col_add2, col_add3 = st.columns([1,2,1])
        with col_add2:
            if st.button("➕ AGREGAR AL PARLAY", key=f"ufc_add_parlay_{idx}", use_container_width=True):
                if analisis and analisis.get('pick'):
                    tracker.agregar_pick({
                        "deporte": "UFC",
                        "partido": f"{p1_nombre} vs {p2_nombre}",
                        "pick": analisis['pick'],
                        "confianza": analisis.get('confianza', 0),
                        "cuota": p1_odds if analisis['pick'] == p1_nombre else p2_odds
                    })
                    st.success(f"✅ {analisis['pick']} agregado al parlay!")
                else:
                    st.warning("⚠️ Analiza el combate primero para agregar un pick.")
        return None
