# BETTING_AI_GEMINI

Sistema de análisis de apuestas deportivas con inteligencia artificial.

## 🚀 Deportes soportados
- ⚾ **MLB** - Análisis de Strikeouts, Home Runs, Moneyline, Over/Under
- 🏀 **NBA** - Análisis de partidos, hándicap, over/under, triples
- 🥊 **UFC** - Análisis de peleadores, estadísticas, predicciones
- ⚽ **Fútbol** - Análisis de partidos, predicciones, mercados

## 🛠️ Tecnologías
- Python 3.11+
- Streamlit (Interfaz web)
- Groq / Gemini / DeepSeek (IA)
- SQLite (Base de datos local)

## 📁 Estructura
BETTING_AI/
├── main_vision_completo.py # Interfaz principal
├── motors/ # Motores de análisis
├── scrapers/ # Extracción de datos
├── visualizers/ # Visualización
├── data/ # Datos locales
└── utils/ # Utilidades

## 🚀 Instalación
1. Clonar repositorio
2. Crear entorno virtual: `python -m venv venv`
3. Activar: `venv\Scripts\activate`
4. Instalar dependencias: `pip install -r requirements.txt`
5. Crear archivo `.env` con tus API Keys
6. Ejecutar: `streamlit run main_vision_completo.py`

## 🔑 API Keys necesarias
- GROQ_API_KEY (https://console.groq.com/keys)
- GEMINI_API_KEY (https://aistudio.google.com/apikey)
- DEEPSEEK_API_KEY (https://platform.deepseek.com/)
- OPENROUTER_API_KEY (https://openrouter.ai/keys)

## 📊 Funcionalidades
- Análisis heurístico (reglas matemáticas)
- Análisis con IA (Groq/Gemini/DeepSeek)
- Backtesting histórico
- Radar de triples (NBA)
- Radar de Home Runs (MLB)
