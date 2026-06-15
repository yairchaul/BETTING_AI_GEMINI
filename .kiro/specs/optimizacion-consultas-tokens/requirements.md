# Requirements Document

## Introduction

El sistema BETTING_AI V24 actualmente consume un número significativo de tokens en consultas frecuentes a APIs de IA (Gemini, Groq, DeepSeek) para análisis de datos deportivos. Este spec define los requisitos para un sistema de optimización de consultas que reduzca significativamente el consumo de tokens manteniendo la calidad y actualidad de los análisis.

El sistema actual incluye múltiples componentes:
- Scrapers para ESPN, Caliente.mx, MLB.com, UFC Stats
- Motores de análisis para MLB, NBA, UFC, Fútbol
- Dashboard Streamlit: main_vision_completo.py
- Bases de datos SQLite y archivos JSON cacheados
- APIs de IA: Gemini, Groq, DeepSeek

## Glossary

- **Token**: Unidad de medida de consumo de API de IA que representa procesamiento de texto
- **Caché_Inteligente**: Sistema que almacena resultados de consultas para reutilización
- **Motor_Analítico**: Componente del sistema que procesa datos deportivos para generar predicciones
- **Scraper**: Componente que recolecta datos de fuentes externas
- **Consulta_Frecuente**: Tipo de análisis solicitado regularmente por los usuarios
- **Hooks**: Eventos programáticos que activan acciones automáticas
- **Streamlit_Dashboard**: Interfaz principal de usuario en main_vision_completo.py
- **SQLite_DB**: Base de datos local para almacenamiento persistente
- **JSON_Cache**: Archivos JSON para caché temporal de datos
- **Metrics_Tracker**: Sistema para medir reducción de consumo de tokens

## Requirements

### Requirement 1: Sistema de Caché Inteligente

**User Story:** Como administrador del sistema, quiero implementar un sistema de caché inteligente, para que las consultas frecuentes no consuman tokens innecesariamente en APIs de IA

#### Acceptance Criteria

1. WHEN una consulta analítica es solicitada, THE Caché_Inteligente SHALL verificar si existe un resultado válido en caché
2. WHERE el resultado en caché tiene menos de 1 hora de antigüedad para datos en vivo, THE Caché_Inteligente SHALL retornar el resultado almacenado
3. WHERE el resultado en caché tiene menos de 24 horas de antigüedad para datos históricos, THE Caché_Inteligente SHALL retornar el resultado almacenado
4. IF el resultado en caché está vencido, THEN THE Caché_Inteligente SHALL ejecutar la consulta nueva y actualizar el caché
5. THE Caché_Inteligente SHALL usar almacenamiento jerárquico: memoria RAM para consultas frecuentes, SQLite para persistencia, JSON para fallback
6. WHEN se detecta una actualización de datos en scrapers, THE Caché_Inteligente SHALL invalidar cachés relacionados

### Requirement 2: Hooks para Eventos Clave

**User Story:** Como desarrollador, quiero implementar hooks para eventos clave del sistema, para que las optimizaciones se activen automáticamente cuando sea necesario

#### Acceptance Criteria

1. WHEN un scraper completa una actualización de datos, THE Hooks_System SHALL disparar la invalidación de cachés afectados
2. WHEN un motor analítico completa un análisis, THE Hooks_System SHALL almacenar el resultado en caché inteligente
3. WHERE un análisis es marcado como "alta_confianza", THE Hooks_System SHALL extender su tiempo de caché a 48 horas
4. IF se detecta un error en consulta a API de IA, THEN THE Hooks_System SHALL activar el modo "conservador_tokens"
5. WHEN el dashboard Streamlit inicia, THE Hooks_System SHALL cargar cachés frecuentes en memoria
6. THE Hooks_System SHALL registrar métricas de uso de caché para monitoreo

### Requirement 3: Estrategias para Consultas Eficientes

**User Story:** Como usuario del dashboard, quiero que las consultas sean eficientes, para obtener análisis rápidos sin sacrificar calidad

#### Acceptance Criteria

1. THE Consulta_Eficiente SHALL usar templates predefinidos para cada tipo de análisis (MLB, NBA, UFC, Fútbol)
2. WHERE el análisis es similar a uno anterior, THE Consulta_Eficiente SHALL usar resultados parciales del caché
3. WHEN se solicitan múltiples análisis del mismo deporte, THE Consulta_Eficiente SHALL agrupar consultas para minimizar tokens
4. THE Consulta_Eficiente SHALL priorizar el motor de IA con mejor relación calidad/tokens según histórico
5. IF una consulta excede 500 tokens estimados, THEN THE Consulta_Eficiente SHALL usar estrategias de resumen
6. WHILE el sistema está en modo "conservador_tokens", THE Consulta_Eficiente SHALL usar caché más agresivamente

### Requirement 4: Métricas para Medir Reducción de Tokens

**User Story:** Como administrador, quiero medir la reducción de consumo de tokens, para evaluar la efectividad de las optimizaciones

#### Acceptance Criteria

1. THE Metrics_Tracker SHALL registrar tokens consumidos por cada consulta a API de IA
2. THE Metrics_Tracker SHALL calcular ahorro de tokens por uso de caché
3. WHEN una consulta usa caché, THE Metrics_Tracker SHALL incrementar el contador "consultas_cacheadas"
4. THE Metrics_Tracker SHALL generar reportes diarios de consumo de tokens por deporte
5. THE Metrics_Tracker SHALL alertar cuando el consumo de tokens exceda umbrales configurados
6. THE Metrics_Tracker SHALL comparar consumo actual vs histórico para mostrar tendencias

### Requirement 5: Tipos de Consultas Frecuentes Específicas

**User Story:** Como analista deportivo, quiero optimizaciones específicas para cada tipo de consulta frecuente, para maximizar eficiencia por deporte

#### Acceptance Criteria

1. WHERE el tipo de consulta es "NBA", THE Optimizador_Deporte SHALL usar plantillas específicas para análisis de puntos y handicaps
2. WHERE el tipo de consulta es "MLB", THE Optimizador_Deporte SHALL optimizar consultas de pitchers, odds, stats y HR predictions
3. WHERE el tipo de consulta es "UFC", THE Optimizador_Deporte SHALL aplicar jerarquía de combate con prioridad 1: diferencia de edad > 10 años
4. WHERE el tipo de consulta es "Fútbol", THE Optimizador_Deporte SHALL priorizar OVER 1.5 1T > OVER 3.5 > BTTS
5. THE Optimizador_Deporte SHALL reconocer patrones de uso por horarios y frecuencia
6. WHEN se detecta hora pico de consultas, THE Optimizador_Deporte SHALL pre-cargar análisis frecuentes

### Requirement 6: Integración con Sistema Existente

**User Story:** Como integrador, quiero que el sistema de optimización se integre sin problemas, para mantener la funcionalidad actual del BETTING_AI V24

#### Acceptance Criteria

1. THE Integrador SHALL mantener compatibilidad con main_vision_completo.py sin cambios en la interfaz de usuario
2. THE Integrador SHALL usar resultados_finales_corregidos.json como fuente de verdad para MLB
3. WHERE existen datos en st.session_state, THE Integrador SHALL priorizar caché en memoria de Streamlit
4. THE Integrador SHALL respetar las reglas específicas de cada deporte definidas en steering files
5. WHEN se usa Gemini como modelo primario, THE Integrador SHALL aplicar optimizaciones específicas para su API
6. THE Integrador SHALL registrar todos los picks en la tabla backtesting como lo hace el sistema actual

### Requirement 7: Sistema de Invalidación Inteligente

**User Story:** Como usuario, quiero que el caché se invalide inteligentemente, para que los análisis siempre reflejen datos actualizados

#### Acceptance Criteria

1. WHEN scrapers de ESPN actualizan datos, THE Invalidador SHALL limpiar cachés de ese deporte
2. WHEN MLB.com reporta nuevos resultados, THE Invalidador SHALL invalidar análisis de pitchers afectados
3. WHERE datos tienen timestamp de más de 1 hora para eventos en vivo, THE Invalidador SHALL marcar como "requiere_actualización"
4. IF se detecta inconsistencia entre fuentes de datos, THEN THE Invalidador SHALL forzar nueva consulta
5. THE Invalidador SHALL usar TTL (Time-To-Live) configurable por tipo de dato
6. WHEN usuario fuerza actualización manual, THE Invalidador SHALL respetar la solicitud sobre TTL

### Requirement 8: Monitorización y Alertas

**User Story:** Como operador, quiero monitorizar el sistema de optimización, para detectar problemas y oportunidades de mejora

#### Acceptance Criteria

1. THE Monitor SHALL mostrar tasa de acierto de caché (hit rate) en tiempo real
2. THE Monitor SHALL alertar cuando tasa de caché caiga por debajo del 60%
3. WHEN consumo de tokens aumenta repentinamente, THE Monitor SHALL investigar posibles fugas
4. THE Monitor SHALL generar reportes de ahorro estimado en costos de API
5. WHERE se detectan consultas ineficientes recurrentes, THE Monitor SHALL sugerir optimizaciones
6. THE Monitor SHALL integrarse con el sistema de logging existente de BETTING_AI

### Requirement 9: Serializador y Parser para Resultados de Caché

**User Story:** Como desarrollador, necesito un sistema de serialización eficiente, para almacenar y recuperar resultados de análisis de manera confiable

#### Acceptance Criteria

1. THE Serializador SHALL convertir objetos de análisis a formato JSON optimizado
2. THE Parser SHALL reconstruir objetos de análisis desde JSON almacenado
3. FOR ALL resultados de análisis válidos, serializar luego parsear SHALL producir objetos equivalentes (propiedad round-trip)
4. WHEN se serializa un resultado, THE Serializador SHALL incluir metadata de timestamp y tipo de análisis
5. THE Parser SHALL validar integridad de datos antes de reconstruir objetos
6. WHERE el formato JSON está corrupto, THE Parser SHALL retornar error descriptivo

### Requirement 10: Backtesting de Estrategias de Optimización

**User Story:** Como investigador, quiero evaluar diferentes estrategias de optimización, para seleccionar la más efectiva

#### Acceptance Criteria

1. THE Backtester SHALL simular diferentes configuraciones de TTL para caché
2. THE Backtester SHALL comparar calidad de análisis con vs sin caché
3. WHEN se prueba una nueva estrategia, THE Backtester SHALL medir impacto en consumo de tokens
4. THE Backtester SHALL identificar umbrales óptimos para invalidación de caché
5. WHERE una estrategia reduce tokens pero afecta calidad, THE Backtester SHALL alertar del trade-off
6. THE Backtester SHALL generar recomendaciones basadas en datos históricos de uso