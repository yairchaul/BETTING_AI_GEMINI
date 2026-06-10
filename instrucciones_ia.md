# REGLAS CRÍTICAS DEL PROYECTO BETTING_AI (VERSIÓN FINAL)

## 1. CODIFICACIÓN
- **PROHIBIDO** usar UTF-8 con BOM (U+FEFF). Guardar siempre en UTF-8 puro sin firma.
- **PROHIBIDO** usar rutas con backslashes simples `\` en cadenas de texto. Usar siempre:
  - Barras dobles: `C:\\Users\\Yair\\...` 
  - Barras invertidas: `C:/Users/Yair/...`
  - Strings raw: `r"C:\Users\Yair\..."`
- Al leer archivos, usar `encoding='utf-8'` explícitamente.

## 2. ESTRUCTURA
- Motores/Lógica: `/motors`
- Scrapers: `/scrapers`
- Visualizadores: `/visualizers`
- Utilidades: `/utils`
- Datos: `/data`

## 3. IMPORTACIONES
- Desde la raíz: use `from motors import X`
- Desde subcarpetas: use `from motors.module import X`

## 4. INTERFAZ (UI)
- No simplificar códigos. Mantener siempre: Radar de Triples (NBA), Candidatos HR (MLB), Datos Físicos completos (UFC)
- Botones centrados: use `st.columns([1, 2, 1])`
- Los análisis de IA (Gemini/Groq) y Heurístico deben MOSTRARSE AMBOS en la UI, no reemplazarse.

## 5. RESILIENCIA
- Mantener bloques try-except en `motors/__init__.py` para que un fallo en un motor no rompa todo el sistema.

## 6. INDENTACIÓN
- Usar estrictamente 4 espacios. No mezclar niveles en bloques de pestañas (tabs).

## 7. RE-RUNS
- Al finalizar un análisis (IA o Heurístico), usar `st.rerun()` para actualizar la UI inmediatamente.

## 8. REGISTRO COMPLETO DE PREDICCIONES
- Todo pick generado debe registrarse en `predicciones_log.json` incluyendo:
  - **MLB**: Moneyline, Home Runs, Strikeouts, Over/Under
  - **NBA**: Moneyline, Hándicap, Over/Under, Triples de jugadores
  - **UFC**: Ganador, Método de finalización
  - **Fútbol**: Moneyline, Over/Under, BTTS
- Cada registro debe incluir: fecha, deporte, pick, confianza, stake, fuente (HEURISTICA/GEMINI/GROQ)

## 9. DATOS 100% DINÁMICOS - NADA ESTÁTICO
- **PROHIBIDO** usar valores por defecto para pitchers o bateadores.
- Si un pitcher no tiene datos, el sistema DEBE:
  1. Intentar extraerlos vía API de MLB (`statsapi`)
  2. Si falla, buscar en `data/scraper_results.json`
  3. Si no existe, PEDIR AL USUARIO la URL del sitio para scrapear
  4. Como ÚLTIMO RECURSO, mostrar advertencia y saltar el análisis

## 10. SCRAPER AUTOMÁTICO FALLBACK
- Cuando falten datos, ejecutar `python run_all_scrapers.py --force`
- Si un sitio cambia su estructura, guardar log y pedir ayuda al usuario

## 11. CONEXIÓN CRUZADA DE MOTORES (CRÍTICO)
- **Los mismos datos deben alimentar todos los análisis**:
  - Los pitchers extraídos para Strikeouts son los MISMOS que enfrentan a los bateadores de HR
  - Los bateadores candidatos a HR son los MISMOS que juegan ese día en el lineup
- Verificar siempre la correlación:
  - `predictor_ponches.py` usa los mismos pitchers que `motor_mlb_pro.py`
  - `predictor_hr.py` usa los mismos bateadores que el lineup del día
  - Si un motor actualiza datos, los demás deben sincronizarse

## 12. FACTORES CLIMÁTICOS Y DE ESTADIO (IMPACTO GLOBAL)
- **El clima y el estadio afectan a TODAS las predicciones**:
  - **Home Runs**: Viento hacia afuera (+15% HR), estadios ofensivos (Coors, Yankee, Great American) multiplican probabilidad
  - **Over/Under**: Viento (+0.5 carreras), temperatura (>85°F suma carreras, <50°F resta)
  - **Moneyline (ganador directo)**: Clima extremo (lluvia, viento cruzado) favorece a equipos con mejor bullpen o pitchers terrestres
  - **Strikeouts**: Viento en contra puede reducir ponches, calor extremo fatiga a los pitchers
- El factor climático debe calcularse UNA VEZ y aplicarse a TODOS los mercados

## 13. ANÁLISIS DE CONTEXTO ADICIONAL (IA)
- Gemini/Groq DEBEN buscar antes de cada análisis:
  - Lesiones de jugadores estrella (IL, día de descanso)
  - Ausencias confirmadas en redes sociales/equipos
  - Clima extremo (lluvia, viento fuerte)
  - Cambios de última hora en alineaciones
- Integrar esta información en el razonamiento final

## 14. FUZZY MATCHING (OBLIGATORIO)
- Antes de asignar un jugador a un equipo, usar `utils.fuzzy_matching.normalizar_equipo()`
- No confiar en nombres exactos de ESPN (pueden venir en español o inglés)
- Mantener diccionario de equivalencias en `utils/mapeo_equipos.py`

## 15. CONFIANZA Y STAKES
- Confianza < 55% → NO APOSTAR (solo mostrar análisis)
- Confianza 55-65% → Stake 1 unidad (apuesta moderada)
- Confianza 65-75% → Stake 2 unidades (apuesta fuerte)
- Confianza > 75% → Stake 3 unidades (PICK ÉLITE - destacar en UI)

## 16. CORRELACIÓN HR → O/U → ML
- Si HR% > 50% en un equipo → OVER +0.5 carreras y Moneyline +5%
- Si ambos equipos tienen HR% > 45% → OVER forzoso
- Si HR% > 60% → Aumentar confianza del Moneyline +10%

## 17. PERSISTENCIA DE ANÁLISIS
- Guardar resultados de IA en `st.session_state.gemini_results` y `st.session_state.groq_results`
- Clave única por partido: `f"gemini_{deporte}_{idx}"`
- No repetir llamadas a IA si ya existe análisis en la sesión actual

## 18. UI - COMPARATIVA IA vs HEURÍSTICA
- Mostrar en casillas separadas y lado a lado:
  - 🤖 GEMINI: [su análisis]
  - ⚡ GROQ: [su análisis]
  - 📊 HEURÍSTICO: [su análisis]
- Usar columnas: `col1, col2, col3 = st.columns(3)`

## 19. RADAR DE PRECISIÓN (UI)
- Mostrar tabla de ROI por jerarquía (ÉLITE, ALTA, MEDIA, BAJA)
- Incluir gráfico de profit acumulado
- Botón "Volver arriba" con `window.scrollTo({top: 0, behavior: 'smooth'})`

## 20. LOGGING Y DEBUG
- Usar `logging.info()` para eventos normales, `logging.error()` para errores
- Guardar logs en `logs/betting_ai.log`
- Registrar cuando un motor no puede obtener datos dinámicos

## 21. SEGURIDAD DE API KEYS
- Usar `.env` para desarrollo y `st.secrets` para producción
- Validar claves antes de inicializar clientes de IA

## 22. PERFORMANCE
- Usar `@st.cache_data` para funciones de scraping (TTL=300 segundos)
- Limitar a 5 candidatos por equipo en HR y Triples
- Cachear resultados de API de MLB por 5 minutos

## 23. VERIFICACIÓN DE CONEXIONES ENTRE MÓDULOS
- Al crear o modificar un módulo, verificar:
  - Sus importaciones con otros módulos
  - Que los datos que necesita existen
  - Que las funciones que exporta son utilizadas correctamente
- Ejecutar `python test_conexiones.py` después de cada cambio importante

## 24. PREVENCIÓN DE ERRORES DE RUTAS (WINDOWS)
- **NUNCA** usar backslashes simples `\` en cadenas de texto. Usar:
  - `os.path.join()` para construir rutas
  - Strings raw: `r"C:\Users\..."` 
  - Barras normales: `"C:/Users/..."`
- Al leer archivos, usar `encoding='utf-8'`
- Al guardar archivos, usar `encoding='utf-8'` y NUNCA `utf-8-sig` (evita BOM)