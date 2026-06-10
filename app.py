import streamlit as st
from models import get_models

# ... (resto del código)

# Sección de votación
def votacion(ias):
    # Inicializa el registro de predicciones
    predicciones = []
    
    # Itera sobre las IAs
    for ia in ias:
        # Calcula la predicción individual
        prediccion = ia.predict()
        predicciones.append(prediccion)
        
    # Muestra las predicciones individuales
    st.write("Predicciones individuales:")
    st.table(predicciones)
    
    # Calcula la votación final
    votacion_final = calcular_votacion_final(predicciones)
    return votacion_final

# ... (resto del código)

# Agrega el nuevo modelo de IA
nuevo_modelo = get_modelo_nuevo()
ias.append(nuevo_modelo)

# Actualiza la votación
votacion_final = votacion(ias)
