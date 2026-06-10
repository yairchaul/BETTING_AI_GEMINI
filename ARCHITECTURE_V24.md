# 🏗️ ARQUITECTURA BETTING_AI V24 - DOCUMENTACIÓN COMPLETA

## 📐 PATRÓN DE DISEÑO

```
┌──────────────────────────────────────────────────────────────────┐
│                    MTV MEJORADO (Model-Transform-View)            │
│                                                                    │
│  SCRAPERS (Model) → MOTORS (Transform) → VISUALIZERS (View)      │
│         ↓                  ↓                     ↓                │
│    Datos Crudos      Análisis Lógico      Renderizado HTML       │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🔄 FLUJO DE DATOS POR DEPORTE

### 🏀 NBA
```
1. main.py → Botón "CARGAR NBA"
2. ESPN_NBA.get_games() → [partidos con odds, récords, logos]
3. (BACKGROUND) nba_stats_scraper → Estadísticas avanzadas (Pace, Off/Def Rating)
4. nba_tab_renderer.render_nba_tab() → Itera partidos
5. Usuario presiona "ANALIZAR"
6. analizar_nba_pro_v17() → Análisis heurístico
7. MotorNBAOverUnder.predict_over_under() → Proyección O/U
8. AnalistaTotal.analizar_nba() → Validación IA (Gemini/Groq/DeepSeek)
9. visual_nba_mejorado.render() → Muestra resultados
10. database_manager.guardar_backtesting() → Persiste para ROI
```

**DATOS CLAVE**:
- ESPN API: Odds en tiempo real, récords, lineup probable
- NBA Stats API: PACE, OFF_RATING, DEF_RATING, NET_RATING
- Caché de sesión: 1 hora de validez

---

### 🥊 UFC
```
1. main.py → Botón "CARGAR UFC"
2. ESPN_UFC.get_events() → [combates con nombres, récords básicos, odds]
3. ufc_tab_renderer.render_ufc_tab() → Pre-carga stats físicos
4. (LAZY LOAD) UFCStatsScraper.get_fighter_stats() → Playwright scraping
   ├── Altura, Peso, Alcance, Postura
   ├── SLpM, Precisión, TD Avg/Def
   └── KO Rate, Sub Rate, Win Rate
5. Datos fusionados: ESPN (odds) + UFCStats (físicos) → p1_data, p2_data
6. Usuario presiona "ANALIZAR"
7. UFCAnalyzer.analizar_combate() → Score de 9 pilares
8. AnalistaTotal.analizar_ufc() → Validación IA
9. visual_ufc_mejorado_v2.render() → Muestra resultados
10. Caché de sesión: Guarda datos enriquecidos por combate
```

**OPTIMIZACIONES V24**:
- ✅ Caché de sesión para evitar re-scraping
- ✅ Indicador de carga con spinner
- ✅ Timeout reducido a 10s (antes 20s)
- ✅ Cacheo de errores para evitar reintentos

---

### ⚾ MLB
```
1. main.py → Botón "CARGAR MLB"
2. ESPN_MLB.get_games() → [partidos con lanzadores, odds, equipos]
3. Normalización: traducir_equipo() → Estandariza nombres
4. motor_mlb_pro_v20() → Análisis heurístico base
5. HRAnalyzerUnificado → Candidatos de Home Run
6. PredictorPonches → Proyecciones de strikeouts
7. MotorOverUnder + ClimaMLB → Proyección O/U con clima
8. MotorDecisionInteligente → Jerarquía de picks
9. AnalistaTotal.analizar_mlb() → Validación IA
10. visual_mlb.render() → Renderizado completo
11. mlb_real_backtester → Auditoría de resultados
```

**MOTORES ESPECIALIZADOS**:
- `predictor_hr.py`: Power factor, park factor, pitcher vulnerability
- `predictor_ponches.py`: K/9, strikeout tendency, tendencia rival
- `motor_over_under.py`: Clima (viento, temperatura), Umpire factor
- `motor_momentum.py`: Rachas de 5 juegos, últimas 10 apuestas

---

### ⚽ FÚTBOL
```
1. main.py → Selección de liga + "Cargar Liga"
2. ESPN_FUTBOL.get_games(liga) → [partidos con odds, forma]
3. analizar_futbol_jerarquico() → Análisis por jerarquía
   Prioridad: OVER 1.5 1T > OVER 3.5 > BTTS > OVER 2.5 > ML
4. AnalistaTotal.analizar_futbol() → Validación IA
5. visual_futbol_triple.render() → Muestra picks jerárquicos
```

---

## 🤖 SISTEMA DE IA

### Orquestador: `AnalistaTotal`
```python
class AnalistaTotal:
    - gemini_client: CerebroGeminiPro (gemini-1.5-flash/pro)
    - groq_client: GroqUFCEngine (llama-3.3-70b-versatile)
    - deepseek_client: CerebroDeepSeek (deepseek-reasoner)
    - new_ai_client: CerebroNewAI (experimental)
    - Modo conservador: Respuestas <150 tokens
    - Sistema de votación: Consenso de 2/3 IAs
```

### Modo Conservador (Auto-activación)
```python
# Se activa automáticamente cuando:
- Error 429 (Rate Limit Exceeded)
- Error 402 (Quota Exceeded)
- Timeout de API >30s
- >5000 tokens en 5 minutos

# Efecto:
- Prompts reducidos a <200 caracteres
- Caché de sesión activo
- Respuestas JSON sin explicaciones extensas
```

---

## 💾 PERSISTENCIA Y CACHÉ

### SQLite Database: `data/betting_stats.db`
```sql
TABLE backtesting:
    - id, fecha, deporte, pick, cuota, estado (GANADA/PERDIDA/PENDIENTE)
    
TABLE peleadores_ufc_cache:
    - id, nombre, datos_json, ultima_actualizacion

TABLE eventos_ufc:
    - id, nombre, fecha, cartelera, ultima_actualizacion
```

### Archivos JSON:
```
data/
├── resultados_finales_corregidos.json   # MLB partidos del día
├── pitchers_hoy_selenium.json           # Lanzadores con K/9, ERA
├── resultados_reales_15dias.json        # Auditoría MLB
├── nba_team_stats_cache.json            # Stats avanzadas NBA (24h)
├── ufc_stats_cache.json                 # Datos físicos UFC (7d)
├── aprendizaje_semanal.json             # Lecciones del sistema
├── bitacora_maestra.csv                 # Historial de todos los picks
└── pesos_motores.json                   # Pesos de motores (backtesting)
```

---

## 🎯 TAB RENDERERS (Orquestadores)

**Propósito**: Conectar scrapers → motors → visualizers sin lógica de negocio.

```python
# visualizers/nba_tab_renderer.py
def render_nba_tab():
    for partido in st.session_state.nba_partidos:
        accion = visual_nba.render(partido, analisis)
        if accion == "analizar":
            resultado = analizar_nba(partido)
            ia_result = analista_total.analizar_nba(partido, resultado)
            db.guardar_backtesting(...)

# visualizers/ufc_tab_renderer.py
def render_ufc_tab():
    for combate in st.session_state.ufc_combates:
        p1_data, p2_data = enriquecer_con_stats(combate)
        accion = visual_ufc.render(combate, p1_data, p2_data)
        if accion == "analizar":
            resultado = ufc_analyzer.analizar_combate(p1_data, p2_data)
            ia_result = analista_total.analizar_ufc(...)

# visualizers/mlb_tab_renderer.py
def render_mlb_tab():
    for partido in st.session_state.mlb_partidos:
        # Motor completo: HR + K + O/U + Decisión
        resultado = motor_mlb_completo(partido)
        ia_result = analista_total.analizar_mlb(...)

# visualizers/futbol_tab_renderer.py
def render_futbol_tab():
    for liga, partidos in st.session_state.futbol_partidos.items():
        resultado_jerarquico = analizar_futbol_jerarquico(partido)
        ia_result = analista_total.analizar_futbol(...)
```

---

## 🗂️ VISUALIZADORES ACTIVOS (Post-limpieza)

```
visualizers/
├── visual_nba_mejorado.py          ✅ ACTIVO - NBA principal
├── visual_mlb.py                   ✅ ACTIVO - MLB unificado
├── visual_ufc_mejorado_v2.py       ✅ ACTIVO - UFC con stats completos
├── visual_futbol_triple.py         ✅ ACTIVO - Fútbol jerárquico
├── nba_tab_renderer.py             ✅ Orquestador NBA
├── ufc_tab_renderer.py             ✅ Orquestador UFC
├── mlb_tab_renderer.py             ✅ Orquestador MLB
├── futbol_tab_renderer.py          ✅ Orquestador Fútbol
└── _deprecated/                    📦 Backup de versiones antiguas
    ├── visual_mlb_base.py
    ├── visual_mlb_pro.py
    ├── visual_mlb_integrado.py
    └── visual_ufc_mejorado.py
```

---

## 🔧 SCRAPERS ACTIVOS

```
scrapers/
├── espn_nba.py                   ✅ ESPN API + Balldontlie integration
├── espn_mlb.py                   ✅ ESPN API + Selenium (lanzadores)
├── espn_ufc.py                   ✅ ESPN API (carteleras, odds)
├── espn_futbol.py                ✅ ESPN API (múltiples ligas)
├── nba_stats_scraper_fixed.py    ✅ NBA Official Stats API
├── ufc_stats_scraper.py          ✅ UFCStats.com (Playwright)
├── mlb_resultados_scraper.py     ✅ MLB API (resultados reales)
└── backtest_collector.py         ✅ Auditoría multi-deporte
```

---

## ⚙️ MOTORES DE ANÁLISIS

```
motors/
├── analizar_nba_pro_v17.py          # Heurístico NBA (récords, form)
├── motor_nba_over_under.py          # Proyección O/U con Pace + Ratings
├── analizar_mlb_pro_v20.py          # Heurístico MLB base
├── predictor_hr.py                  # Home Runs (power, park, pitcher)
├── predictor_ponches.py             # Strikeouts (K/9, tendencia)
├── motor_over_under.py              # O/U MLB (clima, umpire)
├── motor_momentum.py                # Rachas y tendencias
├── motor_decision_inteligente.py    # Jerarquía de picks MLB
├── ufc_analyzer.py                  # 9 pilares UFC (físico + técnico)
├── futbol_analyzer_jerarquico.py    # Prioridades fútbol
└── motor_memoria.py                 # Aprendizaje de errores
```

---

## 📊 BACKTESTING Y ROI

### Flujo de Auditoría:
```
1. mlb_real_backtester.py → Compara predicciones vs resultados reales
2. Calcula Win Rate por tipo de pick (ML, Handicap, O/U, HR, K)
3. Ajusta pesos en pesos_motores.json
4. Identifica "Equipos Trampa" (WR < 40%)
5. Genera aprendizaje_backtest.json
6. Dashboard en Tab6 muestra métricas
```

### Métricas Clave:
- **Win Rate Global**: % de picks acertados
- **ROI**: (Ganancia - Pérdida) / Total Apostado * 100
- **Sharpe Ratio**: ROI ajustado por volatilidad
- **Profit Factor**: Ganancia Total / Pérdida Total

---

## 🛠️ HERRAMIENTAS DE DIAGNÓSTICO

```
utils/
├── api_validator.py              # Test de conectividad IA
├── ufc_data_validator.py         # Validación de flujo UFC
├── compare_engines.py            # Gemini vs Groq vs DeepSeek
├── fuzzy_matching.py             # Normalización de nombres
└── database_manager.py           # ORM simplificado SQLite
```

---

## 🚀 OPTIMIZACIONES V24

1. **Caché de Sesión NBA**: Evita llamadas repetidas a ESPN API (60 min)
2. **Caché de Disco UFC**: Guarda stats físicos por 7 días
3. **Lazy Loading**: Props de NBA y stats de UFC se cargan bajo demanda
4. **Modo Conservador Automático**: Ahorra tokens ante errores de cuota
5. **Sistema de Alertas**: Notifica si consumo >5000 tokens/5min
6. **Pre-carga Inteligente**: Tab renderers pre-cargan datos críticos
7. **Timeout Reducido**: Playwright 10s (antes 20s)
8. **Eliminación de Duplicados**: -1500 líneas de código redundante

---

## 📝 NOTAS IMPORTANTES

### Dependencias Críticas:
- `playwright`: Para scraping de UFCStats (requiere `playwright install chromium`)
- `balldontlie`: API de stats de jugadores NBA (requiere key)
- `streamlit`: Framework de UI
- `google-generativeai`: Gemini API
- `groq`: Groq API

### Variables de Entorno (.env):
```
GEMINI_API_KEY=AIza...
GROQ_API_KEY=gsk_...
DEEPSEEK_API_KEY=sk-...
BALLDONTLIE_API_KEY=c0da...
ODDS_API_KEY=98cc...
```

---

## 🐛 PROBLEMAS CONOCIDOS Y SOLUCIONES

### ❌ "Datos UFC aparecen como N/A"
**Causa**: Playwright tarda 10-30s por peleador
**Solución V24**: Caché de sesión + spinner de carga

### ❌ "Motor NBA O/U no funciona"
**Causa**: Faltaba nba_stats_scraper activo
**Solución V24**: Creado `nba_stats_scraper_fixed.py`

### ❌ "IAs no responden"
**Causa**: Cuota excedida o rate limit
**Solución V24**: Modo conservador automático

### ❌ "Duplicados de MLB"
**Causa**: 4 versiones del mismo visualizador
**Solución V24**: Movidos a `_deprecated/`

---

## 📈 ROADMAP FUTURO

- [ ] Pre-carga de stats UFC en thread background
- [ ] Integración completa con Balldontlie (props de NBA)
- [ ] Sistema de webhooks para actualizaciones en tiempo real
- [ ] Dashboard de ROI en tiempo real con Plotly
- [ ] API REST para integración con bots de Telegram
- [ ] Machine Learning para ajuste dinámico de pesos

---

**Última actualización**: 2026-06-11  
**Versión**: V24.5 (Post-Optimización)
