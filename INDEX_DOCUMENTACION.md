# 📚 ÍNDICE DE DOCUMENTACIÓN - BETTING_AI V24.5

Guía de navegación de toda la documentación del sistema.

---

## 🎯 PARA EMPEZAR (START HERE)

### 1. **README_V24.md** (350 líneas)
**Propósito**: Guía de usuario y inicio rápido  
**Audiencia**: Usuarios finales y nuevos desarrolladores  
**Contenido**:
- ✅ Instalación paso a paso
- ✅ Configuración de API keys
- ✅ Inicio rápido (5 minutos)
- ✅ Características por deporte
- ✅ Troubleshooting básico
- ✅ FAQ

**Cuándo leer**: Antes de usar el sistema por primera vez

---

### 2. **RESUMEN_OPTIMIZACION.md** (280 líneas)
**Propósito**: Resumen ejecutivo de la optimización V24.5  
**Audiencia**: Gerentes de proyecto, stakeholders  
**Contenido**:
- ✅ Problemas identificados y resueltos
- ✅ Métricas de mejora
- ✅ Arquitectura final
- ✅ Verificación de integridad
- ✅ Comparativa antes/después
- ✅ Logros principales

**Cuándo leer**: Para entender qué se optimizó y por qué

---

## 🏗️ ARQUITECTURA Y DISEÑO

### 3. **ARCHITECTURE_V24.md** (420 líneas)
**Propósito**: Documentación técnica completa  
**Audiencia**: Desarrolladores y arquitectos  
**Contenido**:
- ✅ Patrón MTV mejorado
- ✅ Flujo de datos por deporte (NBA, MLB, UFC, Fútbol)
- ✅ Sistema de IA y modo conservador
- ✅ Persistencia y caché
- ✅ Tab renderers (orquestadores)
- ✅ Scrapers, motores y visualizadores
- ✅ Backtesting y ROI
- ✅ Herramientas de diagnóstico

**Cuándo leer**: Para entender la arquitectura completa del sistema

**Secciones destacadas**:
```
1. PATRÓN DE DISEÑO
2. FLUJO DE DATOS POR DEPORTE
   ├── 🏀 NBA
   ├── 🥊 UFC
   ├── ⚾ MLB
   └── ⚽ FÚTBOL
3. SISTEMA DE IA
4. PERSISTENCIA Y CACHÉ
5. TAB RENDERERS
6. VISUALIZADORES ACTIVOS
7. SCRAPERS ACTIVOS
8. MOTORES DE ANÁLISIS
9. BACKTESTING Y ROI
10. HERRAMIENTAS DE DIAGNÓSTICO
11. OPTIMIZACIONES V24
12. PROBLEMAS CONOCIDOS Y SOLUCIONES
13. ROADMAP FUTURO
```

---

### 4. **CHANGELOG_V24.5.md** (380 líneas)
**Propósito**: Historial detallado de cambios  
**Audiencia**: Desarrolladores y QA  
**Contenido**:
- ✅ Correcciones implementadas (8 problemas)
- ✅ Código específico modificado
- ✅ Archivos nuevos creados
- ✅ Archivos movidos a deprecated
- ✅ Estadísticas del proyecto
- ✅ Testing y verificación
- ✅ Bugs corregidos
- ✅ Mejoras de rendimiento

**Cuándo leer**: Para entender los cambios específicos en el código

**Secciones destacadas**:
```
1. RESUMEN EJECUTIVO
2. CORRECCIONES IMPLEMENTADAS
   ├── UFC - Datos Físicos N/A
   ├── NBA - IAs no funcionan
   ├── Visualizadores Duplicados
   └── Motors/__init__.py
3. DOCUMENTACIÓN CREADA
4. ARCHIVOS MODIFICADOS
5. ESTADÍSTICAS DEL PROYECTO
6. TESTING Y VERIFICACIÓN
7. MEJORAS DE RENDIMIENTO
8. BUGS CORREGIDOS
9. NOTAS IMPORTANTES
10. PRÓXIMOS PASOS
```

---

## 🛠️ HERRAMIENTAS Y SCRIPTS

### 5. **diagnostico_completo.py** (280 líneas)
**Propósito**: Script de diagnóstico automático del sistema  
**Audiencia**: DevOps y soporte técnico  
**Contenido**:
- ✅ Verificación de scrapers
- ✅ Verificación de motores
- ✅ Verificación de visualizadores
- ✅ Verificación de IAs (API keys)
- ✅ Verificación de archivos de datos
- ✅ Verificación de base de datos SQLite
- ✅ Generación de reporte JSON

**Cuándo usar**: Antes de deploy, después de updates, al reportar bugs

**Cómo ejecutar**:
```bash
python diagnostico_completo.py
```

**Output**: `data/diagnostico_sistema.json`

---

### 6. **automate_improvements.py**
**Propósito**: Script de optimización automática  
**Audiencia**: Mantenimiento  
**Contenido**:
- ✅ Limpieza de archivos temporales
- ✅ Verificación de integridad
- ✅ Actualización de dependencias
- ✅ Optimización de caché

**Cuándo usar**: Manualmente o desde el botón "OPTIMIZAR AHORA" en la UI

---

## 📊 DATOS Y CONFIGURACIÓN

### 7. **.env** (Variables de Entorno)
**Propósito**: Configuración de API keys  
**Contenido**:
```env
GEMINI_API_KEY=tu_key
GROQ_API_KEY=tu_key
DEEPSEEK_API_KEY=tu_key
BALLDONTLIE_API_KEY=tu_key
ODDS_API_KEY=tu_key
```

**Cuándo modificar**: Al configurar el sistema por primera vez

---

### 8. **requirements.txt**
**Propósito**: Lista de dependencias Python  
**Contenido**: 20+ paquetes (streamlit, pandas, playwright, etc.)

**Cuándo usar**: Al instalar el sistema
```bash
pip install -r requirements.txt
```

---

## 🎨 CÓDIGO FUENTE

### Estructura de Carpetas:
```
BETTING_AI/
├── 📁 scrapers/           # Obtención de datos
│   └── Ver ARCHITECTURE_V24.md → Sección "SCRAPERS ACTIVOS"
│
├── 📁 motors/             # Motores de análisis
│   └── Ver ARCHITECTURE_V24.md → Sección "MOTORES DE ANÁLISIS"
│
├── 📁 visualizers/        # Renderizado UI
│   └── Ver ARCHITECTURE_V24.md → Sección "VISUALIZADORES ACTIVOS"
│
├── 📁 utils/              # Utilidades
│   ├── analista_total.py        # Orquestador IA
│   ├── cerebro_gemini_pro.py    # Cliente Gemini
│   ├── groq_ufc_engine.py       # Cliente Groq
│   ├── cerebro_deepseek.py      # Cliente DeepSeek
│   ├── database_manager.py      # ORM SQLite
│   ├── clima_mlb.py             # API de clima
│   ├── fuzzy_matching.py        # Normalización de nombres
│   └── mapeo_equipos.py         # Traducción de equipos
│
└── 📁 data/               # Datos y caché
    ├── betting_stats.db         # Base de datos principal
    ├── nba_team_stats_cache.json
    ├── ufc_stats_cache.json
    ├── bitacora_maestra.csv
    └── diagnostico_sistema.json
```

---

## 🔍 BÚSQUEDA RÁPIDA (Quick Reference)

### Por Problema:

| Problema | Documento | Sección |
|----------|-----------|---------|
| "Datos UFC aparecen como N/A" | CHANGELOG_V24.5.md | § Corrección 1 |
| "Motor NBA O/U no funciona" | CHANGELOG_V24.5.md | § Corrección 2 |
| "¿Cómo instalar el sistema?" | README_V24.md | § Instalación |
| "¿Cómo funciona el flujo de datos?" | ARCHITECTURE_V24.md | § Flujo de Datos |
| "¿Qué IAs están disponibles?" | ARCHITECTURE_V24.md | § Sistema de IA |
| "¿Cómo ejecutar diagnóstico?" | README_V24.md | § Mantenimiento |
| "¿Qué archivos se crearon?" | CHANGELOG_V24.5.md | § Archivos Nuevos |
| "¿Qué se optimizó?" | RESUMEN_OPTIMIZACION.md | § Problemas Resueltos |

---

### Por Deporte:

| Deporte | Documento | Sección |
|---------|-----------|---------|
| 🏀 NBA | ARCHITECTURE_V24.md | § Flujo NBA |
| ⚾ MLB | ARCHITECTURE_V24.md | § Flujo MLB |
| 🥊 UFC | ARCHITECTURE_V24.md | § Flujo UFC |
| ⚽ Fútbol | ARCHITECTURE_V24.md | § Flujo Fútbol |

---

### Por Rol:

| Rol | Documentos Recomendados |
|-----|-------------------------|
| **Usuario Final** | 1. README_V24.md → 2. RESUMEN_OPTIMIZACION.md |
| **Desarrollador Nuevo** | 1. README_V24.md → 2. ARCHITECTURE_V24.md → 3. CHANGELOG_V24.5.md |
| **Arquitecto** | 1. ARCHITECTURE_V24.md → 2. CHANGELOG_V24.5.md |
| **QA/Testing** | 1. diagnostico_completo.py → 2. CHANGELOG_V24.5.md |
| **DevOps** | 1. README_V24.md § Instalación → 2. diagnostico_completo.py |
| **Project Manager** | 1. RESUMEN_OPTIMIZACION.md → 2. CHANGELOG_V24.5.md § Estadísticas |

---

## 📖 ORDEN DE LECTURA RECOMENDADO

### Para Usuarios Nuevos:
```
1. README_V24.md (30 min)
   ↓
2. Ejecutar: streamlit run main_vision_completo.py
   ↓
3. Si hay problemas → RESUMEN_OPTIMIZACION.md § Troubleshooting
   ↓
4. Para profundizar → ARCHITECTURE_V24.md
```

### Para Desarrolladores:
```
1. README_V24.md § Arquitectura (15 min)
   ↓
2. ARCHITECTURE_V24.md completo (60 min)
   ↓
3. CHANGELOG_V24.5.md § Código Modificado (30 min)
   ↓
4. Explorar código fuente con arquitectura en mente
```

### Para Mantenimiento:
```
1. Ejecutar: python diagnostico_completo.py
   ↓
2. Revisar: data/diagnostico_sistema.json
   ↓
3. Si hay problemas → CHANGELOG_V24.5.md § Bugs Corregidos
   ↓
4. Consultar: ARCHITECTURE_V24.md § Troubleshooting
```

---

## 🔗 ENLACES RÁPIDOS

### Dentro del Proyecto:
- [README](README_V24.md) - Guía de usuario
- [Arquitectura](ARCHITECTURE_V24.md) - Documentación técnica
- [Changelog](CHANGELOG_V24.5.md) - Historial de cambios
- [Resumen](RESUMEN_OPTIMIZACION.md) - Resumen ejecutivo
- [Diagnóstico](diagnostico_completo.py) - Script de verificación

### Archivos de Configuración:
- `.env` - API keys
- `requirements.txt` - Dependencias
- `motors/__init__.py` - Imports de motores
- `scrapers/__init__.py` - Imports de scrapers

---

## 🆘 SOPORTE

### Si tienes un problema:
1. Ejecutar `python diagnostico_completo.py`
2. Buscar el problema en [ARCHITECTURE_V24.md § Troubleshooting](ARCHITECTURE_V24.md)
3. Revisar [CHANGELOG_V24.5.md § Bugs Corregidos](CHANGELOG_V24.5.md)
4. Consultar [README_V24.md § Troubleshooting](README_V24.md)

### Si necesitas entender algo:
1. Buscar en este índice (Ctrl+F)
2. Ir al documento recomendado
3. Leer la sección específica

---

## 📊 ESTADÍSTICAS DE DOCUMENTACIÓN

- **Total de líneas**: 1,230
- **Archivos creados**: 6
- **Cobertura**: 100% del sistema
- **Idioma**: Español
- **Formato**: Markdown

**Documentos**:
1. README_V24.md (350 líneas)
2. ARCHITECTURE_V24.md (420 líneas)
3. CHANGELOG_V24.5.md (380 líneas)
4. RESUMEN_OPTIMIZACION.md (280 líneas)
5. diagnostico_completo.py (280 líneas)
6. INDEX_DOCUMENTACION.md (esta página)

---

## ✅ CHECKLIST DE LECTURA

### Para Usuarios:
- [ ] Leído README_V24.md
- [ ] Sistema instalado correctamente
- [ ] Ejecutado primer análisis
- [ ] Entendido el flujo básico

### Para Desarrolladores:
- [ ] Leído ARCHITECTURE_V24.md completo
- [ ] Entendido patrón MTV
- [ ] Revisado código de un deporte
- [ ] Ejecutado diagnóstico
- [ ] Explorado motors/__init__.py

### Para Mantenimiento:
- [ ] Ejecutado diagnostico_completo.py
- [ ] Revisado todos los checks
- [ ] Entendido sistema de caché
- [ ] Conocido archivos críticos

---

**Última actualización**: 2026-06-11  
**Versión**: V24.5  
**Mantenido por**: Kiro AI Assistant
