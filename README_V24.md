# 🎯 BETTING_AI V24 - Sistema de Análisis Deportivo Profesional

[![Version](https://img.shields.io/badge/version-24.5-blue)](.)
[![Status](https://img.shields.io/badge/status-Production-green)](.)
[![Python](https://img.shields.io/badge/python-3.10+-blue)](.)
[![Streamlit](https://img.shields.io/badge/streamlit-1.28+-red)](.)

Sistema profesional de análisis y predicciones deportivas impulsado por IA para NBA, MLB, UFC y Fútbol.

---

## 🚀 INICIO RÁPIDO

### Instalación
```bash
# 1. Clonar repositorio
git clone <repo_url>
cd BETTING_AI

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Instalar Playwright (para scraping UFC)
playwright install chromium

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus API keys

# 5. Ejecutar aplicación
streamlit run main_vision_completo.py
```

### Configuración `.env`
```env
GEMINI_API_KEY=tu_key_aqui
GROQ_API_KEY=tu_key_aqui
DEEPSEEK_API_KEY=tu_key_aqui
BALLDONTLIE_API_KEY=tu_key_aqui (opcional para NBA props)
ODDS_API_KEY=tu_key_aqui (opcional)
```

---

## 📊 CARACTERÍSTICAS

### 🏀 NBA
- ✅ Análisis heurístico basado en récords y forma
- ✅ Predicción Over/Under con Pace y Ratings
- ✅ Radar de triples (3PM) con integración Balldontlie
- ✅ Validación con Gemini/Groq/DeepSeek
- ✅ Historial de últimos 5 juegos

### ⚾ MLB
- ✅ Predicción de Home Runs (power + park factor)
- ✅ Proyección de Strikeouts (K/9 + tendencia rival)
- ✅ Over/Under con análisis de clima (viento, temperatura)
- ✅ Análisis de lanzadores (ERA, WHIP, K/9)
- ✅ Factor Umpire y momentum
- ✅ Sistema de jerarquía de picks (HR > K > O/U > ML)

### 🥊 UFC
- ✅ Stats físicos completos (altura, peso, alcance)
- ✅ Análisis de 9 pilares técnicos (SLpM, precisión, TD)
- ✅ KO Rate, Sub Rate, Win Rate
- ✅ Scraping de UFCStats.com con Playwright
- ✅ Sistema de caché para optimización
- ✅ Predicción de método de victoria

### ⚽ FÚTBOL
- ✅ Análisis jerárquico de picks
- ✅ Prioridad: OVER 1.5 1T > OVER 3.5 > BTTS > ML
- ✅ Múltiples ligas (EPL, La Liga, Serie A, etc.)
- ✅ Stats de forma reciente

---

## 🏗️ ARQUITECTURA

```
BETTING_AI/
├── main_vision_completo.py        # Aplicación principal
├── scrapers/                       # Obtención de datos
│   ├── espn_nba.py
│   ├── espn_mlb.py
│   ├── espn_ufc.py
│   ├── espn_futbol.py
│   ├── nba_stats_scraper_fixed.py
│   └── ufc_stats_scraper.py
├── motors/                         # Motores de análisis
│   ├── analizar_nba_pro_v17.py
│   ├── motor_nba_over_under.py
│   ├── analizar_mlb_pro_v20.py
│   ├── predictor_hr.py
│   ├── predictor_ponches.py
│   ├── motor_over_under.py
│   ├── ufc_analyzer.py
│   └── futbol_analyzer_jerarquico.py
├── visualizers/                    # Renderizado UI
│   ├── visual_nba_mejorado.py
│   ├── visual_mlb.py
│   ├── visual_ufc_mejorado_v2.py
│   ├── visual_futbol_triple.py
│   ├── nba_tab_renderer.py
│   ├── ufc_tab_renderer.py
│   ├── mlb_tab_renderer.py
│   └── futbol_tab_renderer.py
├── utils/                          # Utilidades
│   ├── analista_total.py          # Orquestador IA
│   ├── cerebro_gemini_pro.py
│   ├── groq_ufc_engine.py
│   ├── database_manager.py
│   ├── clima_mlb.py
│   └── fuzzy_matching.py
└── data/                           # Datos y caché
    ├── betting_stats.db
    ├── nba_team_stats_cache.json
    ├── ufc_stats_cache.json
    └── bitacora_maestra.csv
```

Ver [ARCHITECTURE_V24.md](ARCHITECTURE_V24.md) para documentación completa.

---

## 🔧 OPTIMIZACIONES V24.5

### Mejoras Implementadas
1. ✅ **UFC**: Sistema de caché de sesión + spinner de carga
2. ✅ **NBA**: Scraper de stats oficial activado (`nba_stats_scraper_fixed.py`)
3. ✅ **Visualizadores**: Eliminados duplicados (4 versiones MLB → 1)
4. ✅ **Modo Conservador**: Auto-activación ante errores de API
5. ✅ **Timeout Reducido**: Playwright 10s (antes 20s)
6. ✅ **Documentación**: ARCHITECTURE_V24.md completo

### Problemas Resueltos
- ✅ Datos UFC aparecen como "N/A" → Ahora con caché + indicador
- ✅ Motor NBA O/U no funciona → Scraper de stats activado
- ✅ Visualizadores duplicados → Movidos a `_deprecated/`
- ✅ IAs no responden → Modo conservador automático

---

## 📈 BACKTESTING Y ROI

### Sistema de Auditoría
```bash
# Ejecutar backtesting de MLB
python mlb_real_backtester.py

# Diagnóstico completo del sistema
python diagnostico_completo.py
```

### Métricas Disponibles
- **Win Rate**: Porcentaje de picks acertados
- **ROI**: Retorno sobre inversión
- **Profit Factor**: Ganancia/Pérdida
- **Sharpe Ratio**: ROI ajustado por volatilidad

Ver resultados en Tab "Backtesting MLB" y "Radar de Precisión".

---

## 🤖 SISTEMA DE IA

### Modelos Soportados
1. **Gemini 1.5 Flash/Pro** (Recomendado - gratis)
2. **Groq Llama 3.3 70B** (Rápido)
3. **DeepSeek R1** (Razonamiento avanzado)
4. **Sistema de Votación** (Consenso 2/3)

### Modo Conservador
Se activa automáticamente cuando:
- Error 429 (Rate Limit)
- Error 402 (Quota Exceeded)
- >5000 tokens en 5 minutos

Efectos:
- Prompts reducidos
- Respuestas concisas
- Caché prioritario

---

## 📝 USO

### Flujo Básico
1. **Abrir aplicación**: `streamlit run main_vision_completo.py`
2. **Cargar deporte**: Clic en botón "CARGAR NBA/MLB/UFC/FUTBOL"
3. **Analizar partido**: Clic en "ANALIZAR" en el partido deseado
4. **Ver predicción**: Sistema muestra pick + confianza + razones
5. **Validar con IA**: Opcional - cambiar modelo en sidebar

### Tips de Uso
- 🔥 **Alta confianza** (>70%): Pick recomendado
- ✅ **Media confianza** (55-70%): Pick moderado
- 📊 **Baja confianza** (<55%): NO BET

---

## 🛠️ MANTENIMIENTO

### Limpieza Automática
- Análisis se limpian cada 24 horas
- Caché de NBA: 1 hora de validez
- Caché de UFC: 7 días de validez
- Datos históricos: 15 días

### Optimización Manual
```bash
# Botón "OPTIMIZAR AHORA" en sidebar ejecuta:
python automate_improvements.py
```

---

## 📊 ESTADÍSTICAS DEL PROYECTO

- **Líneas de código**: ~15,000
- **Archivos activos**: 68
- **Deportes soportados**: 4
- **Modelos de IA**: 4
- **Tipos de picks**: 15+

---

## 🐛 TROUBLESHOOTING

### Problema: "Datos UFC aparecen como N/A"
**Solución**: Esperar 10-30s. El scraping de UFCStats es lento.

### Problema: "Motor NBA O/U no funciona"
**Solución**: Verificar que `nba_stats_scraper_fixed.py` esté presente.

### Problema: "IAs no responden"
**Solución**: Verificar API keys en `.env`. Activar modo conservador.

### Problema: "Error de importación"
**Solución**: Ejecutar `python diagnostico_completo.py` para verificar.

---

## 📞 SOPORTE

Para reportar bugs o sugerir mejoras:
1. Ejecutar `python diagnostico_completo.py`
2. Enviar `data/diagnostico_sistema.json`
3. Describir el problema

---

## 📄 LICENCIA

Propietario. Todos los derechos reservados.

---

## 🎯 ROADMAP

### Próximas Versiones
- [ ] Pre-carga background de stats UFC
- [ ] Integración completa Balldontlie (NBA props)
- [ ] Webhooks para actualizaciones en tiempo real
- [ ] API REST para bots de Telegram
- [ ] Machine Learning para ajuste dinámico

---

**Última actualización**: 2026-06-11  
**Versión**: V24.5 (Post-Optimización)  
**Estado**: ✅ Producción
