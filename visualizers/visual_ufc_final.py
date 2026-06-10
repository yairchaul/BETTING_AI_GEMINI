# visual_ufc_final.py
import streamlit as st
import json # Para pretty print el análisis si es un dict

class VisualUFCFinal:
    def render(self, partido, idx, tracker, analisis=None, **kwargs):
        p1 = partido.get('peleador1', {})
        p2 = partido.get('peleador2', {})
        p1_nombre = p1.get('nombre', 'Peleador 1')
        p2_nombre = p2.get('nombre', 'Peleador 2')
        p1_record = p1.get('record', '0-0-0')
        p2_record = p2.get('record', '0-0-0')
        p1_altura = p1.get('altura', 'N/A')
        p2_altura = p2.get('altura', 'N/A')
        p1_alcance = p1.get('alcance', 'N/A')
        p2_alcance = p2.get('alcance', 'N/A')
        p1_ko = p1.get('ko_rate', 0)
        p2_ko = p2.get('ko_rate', 0)
        
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #1a1a2e, #16213e); padding: 20px; border-radius: 15px; margin: 10px 0; border: 1px solid #00ff41;">
            <div style="display: flex; justify-content: space-between; text-align: center;">
                <div style="width: 45%;">
                    <h3>🔴 {p1_nombre}</h3>
                    <p>📊 Record: {p1_record}</p>
                    <p>📏 Altura: {p1_altura} cm</p>
                    <p>📐 Alcance: {p1_alcance} cm</p>
                    <p>💥 KO: {p1_ko*100:.0f}%</p>
                </div>
                <div style="width: 10%;">
                    <h2>VS</h2>
                </div>
                <div style="width: 45%;">
                    <h3>🔵 {p2_nombre}</h3>
                    <p>📊 Record: {p2_record}</p>
                    <p>📏 Altura: {p2_altura} cm</p>
                    <p>📐 Alcance: {p2_alcance} cm</p>
                    <p>💥 KO: {p2_ko*100:.0f}%</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if analisis:
            st.markdown(f"""
            <div style="background: #0f0f1a; padding: 15px; border-radius: 10px; margin: 10px 0;">
                <h4>🥊 ANÁLISIS</h4>
                <p>Pick: {analisis.get('recomendacion', 'N/A')}</p>
                <p>Confianza: {analisis.get('confianza', 0)}%</p>
                <p>Método: {analisis.get('metodo', 'N/A')}</p>
            </div>
            """, unsafe_allow_html=True)
            st.progress(analisis.get('confianza', 0) / 100)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🥊 ANALIZAR UFC", key=f"ufc_btn_{idx}", use_container_width=True):
                return "analizar"
        
        return None
