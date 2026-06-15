import streamlit as st

def render_analisis_card(resultado):
    recomendacion = resultado.get('recomendacion', 'N/A')
    confianza = resultado.get('confianza', 0)
    color = "#00ff41" if confianza >= 60 else "#ffcc00"
    
    st.markdown(f'''
    <div style='background: #1a1f2a; border-radius: 12px; padding: 15px; 
                border-left: 4px solid {color}; margin: 10px 0;'>
        <h4 style='color: {color};'>🎯 {recomendacion}</h4>
        <p style='color: #00ff41;'>📊 Confianza: {confianza}%</p>
    </div>
    ''', unsafe_allow_html=True)

    # Mostrar predicciones individuales si están disponibles (Votación)
    if 'individual_ia_results' in resultado:
        with st.expander("🔍 Ver desgloses individuales de IA"):
            for i, res in enumerate(resultado['individual_ia_results']):
                ia_name = f"IA #{i+1}"
                if "error" in res:
                    st.error(f"**{ia_name}:** {res['error']}")
                else:
                    st.markdown(f"""
                    <div style='background: #0e1117; padding: 10px; border-radius: 8px; margin-bottom: 5px; border: 1px solid #30363d;'>
                        <p style='margin:0; font-size: 0.9rem;'>
                            <strong style='color: #3b82f6;'>{ia_name}:</strong> 
                            Pick: <b>{res.get('pick', 'N/A')}</b> | 
                            Confianza: {res.get('confianza', 0)}%
                        </p>
                        <p style='margin:0; font-size: 0.8rem; color: #94a3b8;'><i>{res.get('razon', '')}</i></p>
                    </div>
                    """, unsafe_allow_html=True)
