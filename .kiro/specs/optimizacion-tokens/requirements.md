# Spec: Optimización de Tokens en BETTING_AI

## Propósito
Crear un sistema optimizado para reducir el consumo de tokens en consultas recurrentes mediante:
1. Caché inteligente de datos frecuentemente consultados
2. Respuestas precompiladas para preguntas comunes
3. Agentes especializados por deporte
4. Sistema de resúmenes automáticos

## Requisitos de Negocio

### RQ-01: Reducción de Tokens en Consultas Recurrentes
**Descripción:** El usuario frecuentemente consulta:
- "¿Qué picks de MLB hay hoy?"
- "Análisis UFC del evento X"
- "Predicciones de fútbol para la liga Y"
- "Resultados de ayer"

**Solución propuesta:**
- Sistema de caché por 5 minutos para datos de picks
- Respuestas precompiladas con plantillas
- Agente especializado por deporte que mantiene contexto

**Criterios de éxito:**
- Reducción del 60% en tokens para consultas idénticas
- Respuesta en <2 segundos para datos cacheados
- Precisión mantenida >95%

### RQ-02: Consultas Jerárquicas Optimizadas
**Descripción:** El modelo jerárquico de fútbol consulta múltiples fuentes:
- Estadísticas de equipo
- Cuotas de apuestas
- Datos históricos
- Factores ambientales

**Solución propuesta:**
- Cachear respuestas completas del modelo jerárquico
- Sistema de actualización incremental
- Base de datos de predicciones precomputadas

**Criterios de éxito:**
- Una consulta jerárquica completa usa ≤800 tokens
- Actualización automática cuando cambian datos críticos
- Precisión de predicción >85%

### RQ-03: Agentes Especializados por Deporte
**Descripción:** Cada deporte (MLB, UFC, Fútbol, NBA) tiene:
- Datasets específicos
- Modelos de predicción diferentes
- Métricas de éxito distintas

**Solución propuesta:**
- 4 agentes especializados (uno por deporte)
- Contexto mantenido por 24 horas por agente
- Datasets pre-cargados en memoria

**Criterios de éxito:**
- Cada agente mantiene ≤500 tokens de contexto permanente
- Cambio entre agentes en <1 segundo
- Precisión deporte-específica >90%

### RQ-04: Sistema de Resúmenes Automáticos
**Descripción:** El usuario quiere resúmenes rápidos:
- "Resumen picks MLB"
- "Top 3 apuestas UFC"
- "Mejores valores fútbol"

**Solución propuesta:**
- Plantillas de resumen por deporte
- Sistema de puntuación de "valor"
- Ranking automático de mejores picks

**Criterios de éxito:**
- Resumen completo en ≤300 tokens
- Generación en <3 segundos
- Inclusión de picks más valiosos (edge > 5%)

## Requisitos Técnicos

### RQ-05: Sistema de Caché Inteligente
**Descripción:** Cachear datos basado en:
- Frecuencia de consulta
- Volatilidad de los datos
- Tiempo desde última actualización

**Solución propuesta:**
- Caché en memoria Redis/archivos JSON
- Estrategias TTL por tipo de dato:
  - Picks: 5 minutos
  - Cuotas: 1 minuto
  - Estadísticas: 30 minutos
  - Resultados: 24 horas

**Criterios de éxito:**
- Hit rate del caché >80%
- Reducción de llamadas API externas >70%
- Sincronización automática con fuentes

### RQ-06: Plantillas de Respuesta Optimizadas
**Descripción:** Respuestas estructuradas que:
- Maximizan información por token
- Usan emojis y formato conciso
- Incluyen solo datos críticos

**Solución propuesta:**
- Sistema de plantillas Mustache/JSON
- Variables dinámicas por deporte
- Compresión automática de texto redundante

**Criterios de éxito:**
- 40% más información por token vs texto libre
- Legibilidad mantenida (score >80%)
- Tiempo de render <100ms

### RQ-07: Sistema de Monitoreo de Tokens
**Descripción:** Monitorear y optimizar:
- Tokens por consulta
- Tokens por respuesta
- Eficiencia general

**Solución propuesta:**
- Dashboard de métricas de tokens
- Alertas cuando eficiencia < objetivo
- Sugerencias automáticas de optimización

**Criterios de éxito:**
- Reducción promedio de 50% en tokens/consulta
- Sistema auto-optimizante basado en métricas
- Reportes diarios de eficiencia

## Requisitos de Integración

### RQ-08: Integración con Sistema Existente
**Descripción:** El sistema debe integrarse con:
- `main_vision_completo.py`
- Motores de análisis (MLB, UFC, Fútbol)
- Scrapers existentes
- Base de datos SQLite

**Solución propuesta:**
- API intermedia de optimización
- Sistema de proxy para consultas
- Migración gradual de componentes

**Criterios de éxito:**
- Compatibilidad 100% con sistema existente
- Sin degradación de performance
- Migración transparente para usuario

### RQ-09: Sistema de Fallback Robusto
**Descripción:** Cuando falla la optimización:
- Usar sistema original
- Reportar error automáticamente
- Recuperación automática

**Solución propuesta:**
- Circuit breaker pattern
- Sistema de health checks
- Logging detallado de fallos

**Criterios de éxito:**
- Disponibilidad >99.9%
- Tiempo de recuperación <10 segundos
- Sin pérdida de datos en fallos

## Métricas de Éxito

| Métrica | Objetivo | Límite de Alerta |
|---------|----------|------------------|
| Tokens/consulta promedio | ≤500 | >800 |
| Tiempo respuesta promedio | ≤2s | >5s |
| Hit rate caché | ≥80% | <60% |
| Precisión predicciones | ≥85% | <80% |
| Disponibilidad sistema | ≥99.9% | <99% |

## Prioridades

1. **Alta:** RQ-01, RQ-02 (consultas MLB y fútbol)
2. **Media:** RQ-03, RQ-05 (agentes y caché)
3. **Baja:** RQ-06, RQ-07 (plantillas y monitoreo)

## Stakeholders

- **Usuario final:** Operador del sistema BETTING_AI
- **Desarrollador:** Mantenedor del código
- **Analista:** Usuario de predicciones

## Riesgos y Mitigación

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Pérdida de precisión por optimización | Media | Alto | Sistema A/B testing |
| Aumento de complejidad | Alta | Medio | Migración incremental |
| Problemas de sincronización caché | Media | Medio | Estrategias TTL cortas |
| Sobre-optimización (pérdida contexto) | Baja | Alto | Monitoreo continuo de calidad |

## Fases de Implementación

**Fase 1 (Semanas 1-2):** Sistema de caché básico + agentes especializados MLB/UFC
**Fase 2 (Semanas 3-4):** Modelo jerárquico optimizado + sistema de resúmenes
**Fase 3 (Semanas 5-6):** Sistema completo + dashboard de métricas
**Fase 4 (Semanas 7-8):** Optimizaciones avanzadas + auto-tuning