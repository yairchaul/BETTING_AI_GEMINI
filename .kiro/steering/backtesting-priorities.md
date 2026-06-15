# Steering: Prioridades de Backtesting y Jerarquías Basadas en Datos

## JERARQUÍA DE DECISIONES MLB (Basada en Backtesting Real)

### 1. HOME RUN PREDICTIONS (Prioridad Máxima)
**Criterios de Evaluación:**
- HR totales últimos 15 días del bateador
- HR/9 del pitcher rival
- Factor estadio (HR factor > 1.15)
- Temperatura > 75°F y viento favorable
- Día de la semana (Viernes/Sábado = +15% probabilidad)

**Backtesting Metrics Target:**
- Precisión mínima: 25% (HR son eventos raros)
- ROI esperado: +150% (cuotas altas)
- Stake recomendado: 1-2u máximo

### 2. OVER/UNDER (Segunda Prioridad)
**Criterios de Evaluación:**
- Promedio carreras últimas 10 juegos de ambos equipos
- ERA reciente de pitchers
- Factor clima (viento out > 12mph = OVER)
- Umpire tendencia (check umpire_stats.json)
- Bullpen últimas 48 horas

**Backtesting Metrics Target:**
- Precisión mínima: 55%
- ROI esperado: +10-20%
- Stake recomendado: 2-3u

### 3. MONEYLINE (Tercera Prioridad)
**Criterios de Evaluación:**
- Diferencias de stats del motor heurístico
- Power factor (HR predictions del equipo)
- Pitcher vulnerable (ERA reciente > 5.0)
- Home/away splits últimos 30 días
- Situación bullpen

**Backtesting Metrics Target:**
- Precisión mínima: 60%
- ROI esperado: +5-15%
- Stake recomendado: 3u para alta confianza, 2u para media

### 4. HANDICAP (Cuarta Prioridad - Protección)
**Criterios de Evaluación:**
- Sólo cuando Moneyline confianza 55-65%
- Equipos con dif stats < 15%
- Pitchers con ERA similar
- Situaciones de bajo scoring esperado

**Backtesting Metrics Target:**
- Precisión mínima: 65%
- ROI esperado: +5-10%
- Stake recomendado: 2u

## REGLAS DE BACKTESTING AUTOMÁTICO

### Recolección Diaria Obligatoria
```
1. 00:00 AM - Scrape resultados del día anterior
2. 01:00 AM - Cruzar con predicciones de ayer
3. 02:00 AM - Actualizar métricas de efectividad
4. 03:00 AM - Ajustar pesos de motores si necesario
```

### Métricas de Evaluación por Equipo
Para cada equipo, trackear:
- Win rate últimos 10 picks
- ROI últimos 20 picks
- Tendencia (mejorando/empeorando)
- Clasificación: ÉLITE, CONFIANZA, RIESGO, EVITAR

### Sistema de Clasificación de Equipos
```
ÉLITE: Win rate > 65%, ROI > +20%
CONFIANZA: Win rate 55-65%, ROI positivo
RIESGO: Win rate 45-55%, ROI negativo
EVITAR: Win rate < 45%, ROI < -15%
```

## INTEGRACIÓN CON SISTEMA DE OPTIMIZACIÓN

### Caché Inteligente de Backtesting
```
data/backtesting_cache/
├── team_performance.json      # Métricas por equipo
├── pick_type_performance.json # Métricas por tipo de pick
├── daily_results/            # Resultados diarios
└── learning_updates.json     # Ajustes automáticos
```

### Actualización Automática de Jerarquías
Cuando backtesting muestre:
- HR precision < 20% por 7 días → bajar prioridad
- O/U precision > 60% por 10 días → subir prioridad
- Equipo clasificado EVITAR → excluir de picks

## REGLAS DE STAKE DINÁMICO

### Basado en Confianza y Backtesting
```
Confianza > 75% + Equipo ÉLITE = 4u
Confianza 65-75% + Equipo CONFIANZA = 3u
Confianza 55-65% = 2u
Confianza < 55% = 1u o EVITAR
```

### Ajuste por ROI Histórico
- ROI equipo > +30% = +0.5u adicional
- ROI equipo < -10% = -1u reducción
- 3 pérdidas consecutivas = stake a 1u hasta recuperación

## SISTEMA DE ALERTAS

### Alertas de Performance
- Equipo cae a categoría EVITAR → notificación
- Tipo de pick con precision < 45% por 5 días → revisión
- ROI general < 0% por semana → análisis completo

### Alertas de Oportunidad
- Equipo sube a ÉLITE → notificación
- Tipo de pick con precision > 70% por 5 días → aumentar exposición
- Desajuste odds > 15% vs predicción → VALUE ALERT

## WORKFLOW DE TOMA DE DECISIONES

### Flujo Completo
```
1. SCRAPING → Datos actualizados
2. BACKTESTING CHECK → Verificar métricas recientes
3. PREDICCIÓN → Generar picks con jerarquía
4. STAKE CALCULATION → Basado en confianza + histórico
5. VALIDATION → Cross-check con IA (Gemini/Groq)
6. EXECUTION → Registrar en bitácora
7. TRACKING → Seguimiento para next day backtesting
```

### Integración con IA para Validación
- Gemini: Validar picks de alta confianza (≥70%)
- Groq: Análisis rápido de todos los picks
- Sistema de votación: 2 de 3 (Heurístico, Gemini, Groq) para picks críticos

## MANTENIMIENTO Y MONITOREO

### Reportes Automáticos Diarios
```
- Efectividad por deporte
- ROI por tipo de pick
- Top 5 equipos más confiables
- Bottom 5 equipos a evitar
- Ajustes automáticos aplicados
```

### Auditoría Semanal
Cada domingo:
- Revisar todas las métricas
- Ajustar jerarquías si necesario
- Limpiar caché de datos antiguos
- Generar reporte de performance semanal