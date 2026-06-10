# MAPA DE ARQUITECTURA - BETTING AI NEON EDITION
# Generado: 2026-03-25 11:01

## 1. Punto de entrada
- main_vision_completo.py : Interfaz Streamlit con tabs NBA/UFC/Fútbol/MLB

## 2. Capa de análisis
- analizador_nba_mejorado.py : Motor NBA (Poisson + Monte Carlo + EV)
- analizador_mlb_pro.py : Motor MLB
- analizador_ufc_heurístico.py : Motor UFC base
- analizador_ufc_ko_pro.py : Análisis de KO
- analizador_futbol_heurístico_mejorado.py : Motor fútbol

## 3. Capa de integración
- integrador_v17.py : Conector principal
- motor_nba_pro_v17.py : Motor V17 con BD
- cerebro_gemini_pro.py : API Gemini

## 4. Capa de datos
- espn_nba.py : Scraper NBA (odds reales)
- espn_mlb.py : Scraper MLB
- espn_ufc.py : Lee UFC desde SQLite
- espn_futbol.py : Scraper fútbol
- database_manager.py : Gestor SQLite

## 5. Visuales
- visual_nba_mejorado.py : Render NBA
- visual_ufc_mejorado.py : Render UFC
- visual_futbol_triple.py : Render fútbol
- visual_mlb.py : Render MLB
- render_unificado.py : Tarjetas comunes

## 6. Utilidades
- bet_tracker.py : Parlay y bitácora
- selector_mejor_opcion.py : Selecciona mejor apuesta
- calculador_probabilidades_futbol.py : Cálculos fútbol

## 7. Datos
- data/betting_stats.db : SQLite con históricos
- eventos_ufc.json : Carteleras UFC
- .env : API keys (GEMINI_API_KEY)
