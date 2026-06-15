# Reglas Globales: BETTING_AI V24

## 1. Arquitectura de Datos
- **Base de Datos Principal:** Usar siempre SQLite ubicada en `data/betting_stats.db`.
- **Intercambio de Datos:** Priorizar `resultados_finales_corregidos.json` para MLB y el sistema de `st.session_state` para persistencia en Streamlit.
- **Normalización:** Antes de cualquier cruce de datos, usar la lógica de `mapeo_equipos.py` y `normalizador.py` para evitar errores de nombres entre ESPN y APIs oficiales.

## 2. Inteligencia Artificial
- **Modelo Primario:** Gemini 1.5/2.5 Flash (vía `cerebro_gemini_pro.py`).
- **Modelo de Respaldo:** Groq Llama 3 (vía `groq_ufc_engine.py`).
- **Regla de Formato:** Las respuestas de IA para el Dashboard deben estar en Markdown estructurado con tablas y bloques de cita.

## 3. Seguridad y Estilo
- **UI:** El Dashboard principal es `main_vision_completo.py` usando Streamlit.
- **CSS:** Seguir el estilo "NEON" definido en `estilos_neon.css`.
- **Integridad:** Prohibido eliminar o sobreescribir funciones de cálculo heurístico sin autorización; la IA debe ser un "Decisor Final", no el reemplazo del cálculo matemático.

## 4. Workflow de Backtesting
- Siempre registrar picks en la tabla `backtesting` de la base de datos tras cada análisis.