# -*- coding: utf-8 -*-
"""
VISUAL UFC MEJORADO - Letra reducida para datos físicos
"""
import streamlit as st

class VisualUFCMejorado:
    def __init__(self):
        self.colores = {
            'local': '#FF6B35',
            'visitante': '#0066CC',
            'green': '#4CAF50',
            'orange': '#FF9800',
            'blue': '#2196F3',
            'red': '#f44336',
            'gold': '#FFD700',
            'yellow': '#FFC107'
        }
    
    def render(self, combate, idx, tracker=None, 
                datos_peleador1=None, datos_peleador2=None,
                analisis_heurístico=None, analisis_gemini=None, analisis_premium=None):
        
        with st.container():
            if idx > 0:
                st.markdown("---")
            
            evento = combate.get('evento', 'UFC Event')
            fecha = combate.get('fecha', 'Próximamente')
            
            if datos_peleador1 and datos_peleador2:
                p1 = datos_peleador1
                p2 = datos_peleador2
            else:
                p1 = combate.get('peleador1', {})
                p2 = combate.get('peleador2', {})
                p1['altura'] = p1.get('altura', 'N/A')
                p1['peso'] = p1.get('peso', 'N/A')
                p1['alcance'] = p1.get('alcance', 'N/A')
                p1['postura'] = p1.get('postura', 'Desconocida')
                p2['altura'] = p2.get('altura', 'N/A')
                p2['peso'] = p2.get('peso', 'N/A')
                p2['alcance'] = p2.get('alcance', 'N/A')
                p2['postura'] = p2.get('postura', 'Desconocida')
            p1_ko_rate = p1.get('ko_rate', 0.0) * 100 # Convert to percentage
            p2_ko_rate = p2.get('ko_rate', 0.0) * 100 # Convert to percentage
            
            # Encabezado
            st.markdown(f"""
            <div style="background-color: #1E1E1E; padding: 20px; border-radius: 10px; border-left: 5px solid #FFD700;">
                <span style="color: #FFD700; font-weight: bold; font-size: 24px;">🥊 {evento}</span>
                <span style="color: #888; float: right;">📅 {fecha}</span>
            </div>
            """, unsafe_allow_html=True)
            
            # Peleadores con datos físicos
            col1, col2, col3 = st.columns([2, 1, 2])
            
            with col1:
                st.markdown(f"## 🔴 {p1.get('nombre', 'Desconocido')}")
                st.markdown(f"📊 **Récord:** {p1.get('record', '0-0-0')}")
                st.markdown(f"<p style='font-size: 14px; color: #888;'>📏 Altura: {p1.get('altura', 'N/A')} | ⚖️ Peso: {p1.get('peso', 'N/A')} | 📏 Alcance: {p1.get('alcance', 'N/A')} | 🥊 Postura: {p1.get('postura', 'Desconocida')}</p>", unsafe_allow_html=True)
                st.markdown(f"<p style='font-size: 14px; color: #FFD700;'>💥 KO Rate: {p1_ko_rate:.1f}%</p>", unsafe_allow_html=True)
                
                stats1 = p1.get('estadisticas_carrera', {})
                if stats1:
                    with st.expander("📊 Estadísticas de carrera", expanded=False):
                        col_s1, col_s2 = st.columns(2)
                        with col_s1:
                            st.metric("Golpes/min", stats1.get('sig_strikes_landed_per_min', 0))
                            st.metric("Precisión", f"{stats1.get('sig_strike_accuracy', 0)}%")
                        with col_s2:
                            st.metric("Derribos/15min", stats1.get('td_avg_per_15min', 0))
                            st.metric("Defensa Derribos", f"{stats1.get('td_defense', 0)}%")
            
            with col2:
                st.markdown("<h1 style='text-align: center; color: #666;'>VS</h1>", unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"## 🔵 {p2.get('nombre', 'Desconocido')}")
                st.markdown(f"📊 **Récord:** {p2.get('record', '0-0-0')}")
                st.markdown(f"<p style='font-size: 14px; color: #888;'>📏 Altura: {p2.get('altura', 'N/A')} | ⚖️ Peso: {p2.get('peso', 'N/A')} | 📏 Alcance: {p2.get('alcance', 'N/A')} | 🥊 Postura: {p2.get('postura', 'Desconocida')}</p>", unsafe_allow_html=True)
                st.markdown(f"<p style='font-size: 14px; color: #FFD700;'>💥 KO Rate: {p2_ko_rate:.1f}%</p>", unsafe_allow_html=True)
                
                stats2 = p2.get('estadisticas_carrera', {})
                if stats2:
                    with st.expander("📊 Estadísticas de carrera", expanded=False):
                        col_s1, col_s2 = st.columns(2)
                        with col_s1:
                            st.metric("Golpes/min", stats2.get('sig_strikes_landed_per_min', 0))
                            st.metric("Precisión", f"{stats2.get('sig_strike_accuracy', 0)}%")
                        with col_s2:
                            st.metric("Derribos/15min", stats2.get('td_avg_per_15min', 0))
                            st.metric("Defensa Derribos", f"{stats2.get('td_defense', 0)}%")
            
            st.markdown("---")
            
            col_a1, col_a2, col_a3 = st.columns(3)
            
            with col_a1:
                st.markdown("<h4 style='color: #FFD700;'>📊 HEURÍSTICO</h4>", unsafe_allow_html=True)
                if analisis_heurístico:
                    st.markdown(f"**{analisis_heurístico.get('apuesta', 'N/A')}**")
                    st.markdown(f"Confianza: {analisis_heurístico.get('confianza', 0)}%")
                    st.markdown(f"Método: {analisis_heurístico.get('metodo', 'N/A')}")
                else:
                    st.markdown("Pendiente")
            
            with col_a2:
                st.markdown("<h4 style='color: #FFD700;'>🔬 PREMIUM ANALYTICS</h4>", unsafe_allow_html=True)
                if analisis_premium:
                    edge = analisis_premium.get('edge_rating', 0)
                    st.markdown(f"**Edge Rating:** {edge}")
                    estrellas = "★" * int(edge) + "☆" * (10 - int(edge))
                    st.markdown(f"{estrellas}")
                else:
                    st.markdown("Pendiente")
            
            with col_a3:
                st.markdown("<h4 style='color: #FFD700;'>🤖 GEMINI IA</h4>", unsafe_allow_html=True)
                if analisis_gemini:
                    st.markdown(f"**Ganador:** {analisis_gemini.get('ganador', 'N/A')}")
                    st.markdown(f"**Método:** {analisis_gemini.get('metodo', 'N/A')}")
                else:
                    st.markdown("Pendiente")
            
            st.markdown("---")
            
            # Botones
            col_b1, col_b2, col_b3 = st.columns(3)
            with col_b1:
                if st.button(f"🔍 ANALIZAR", key=f"analizar_ufc_{idx}"):
                    return "analizar"
            with col_b2:
                if st.button(f"➕ AGREGAR AL PARLAY", key=f"add_ufc_{idx}"):
                    st.success("✓ Agregado")
            with col_b3:
                if st.button(f"📊 DETALLES", key=f"details_ufc_{idx}"):
                    st.json({'p1': p1, 'p2': p2})
