# test_connections.py
import streamlit as st

st.title("🔌 TEST DE CONEXIONES")

# Prueba 1: Importaciones
st.subheader("1. Importaciones")
try:
    from visual_nba_mejorado import VisualNBAMejorado
    st.success("✅ VisualNBAMejorado importado")
except Exception as e:
    st.error(f"❌ Error: {e}")

try:
    from visual_mlb import VisualMLB
    st.success("✅ VisualMLB importado")
except Exception as e:
    st.error(f"❌ Error: {e}")

try:
    from visual_futbol_triple import VisualFutbolTriple
    st.success("✅ VisualFutbolTriple importado")
except Exception as e:
    st.error(f"❌ Error: {e}")

try:
    from radar_triples_nba import radar_triples
    st.success("✅ radar_triples importado")
except Exception as e:
    st.error(f"❌ Error: {e}")

# Prueba 2: Datos
st.subheader("2. Datos de prueba")
partido_test = {
    "local": "Lakers",
    "visitante": "Warriors",
    "records": {"local": "52-30", "visitante": "53-29"},
    "odds": {"moneyline": {"local": -150, "visitante": +130}}
}

st.write("Partido de prueba creado:", partido_test)

st.info("✅ Si ves todos los ✅, las conexiones funcionan")
