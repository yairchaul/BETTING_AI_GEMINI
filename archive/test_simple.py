# test_simple.py
import streamlit as st

st.set_page_config(page_title="Prueba de Conexión", layout="wide")

st.title("🔌 Prueba de Conexión - BETTING_AI")

# Probar importaciones
st.subheader("1. Verificando Importaciones")

try:
    from radar_triples_nba import radar_triples
    st.success("✅ radar_triples_nba importado")
    
    # Probar el radar con datos de prueba
    st.subheader("2. Probando Radar de Triples")
    radar_triples.render("Los Angeles Lakers", "Golden State Warriors")
    
except Exception as e:
    st.error(f"❌ Error: {e}")

try:
    from visual_nba_mejorado import VisualNBAMejorado
    st.success("✅ visual_nba_mejorado importado")
except Exception as e:
    st.error(f"❌ Error: {e}")

st.info("✅ Si ves jugadores en el Radar de Triples, la conexión funciona")
