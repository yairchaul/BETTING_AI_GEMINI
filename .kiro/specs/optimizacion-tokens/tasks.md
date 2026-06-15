# Tasks: Implementación Sistema de Optimización de Tokens

## Task 1: Crear Estructura Base del Sistema
**ID:** OPT-001
**Status:** TODO
**Estimación:** 2 días
**Dependencias:** None

### Descripción
Crear la estructura de directorios y archivos base para el sistema de optimización.

### Subtasks
- [ ] Crear directorio `optimization/` con estructura:
  - `optimization/__init__.py`
  - `optimization/manager.py` (OptimizationManager)
  - `optimization/cache.py` (CacheCoordinator)
  - `optimization/templates.py` (TemplateRenderer)
  - `optimization/metrics.py` (TokenMonitor)
  - `optimization/agents/` (agentes especializados)
- [ ] Configurar imports y dependencias en `requirements.txt`
- [ ] Crear archivo de configuración `optimization/config.py`

### Criterios de Aceptación
- Estructura de directorios creada
- Imports funcionando sin errores
- Archivos base con clases esqueleto

## Task 2: Implementar Optimization Manager
**ID:** OPT-002
**Status:** TODO
**Estimación:** 1 día
**Dependencias:** OPT-001

### Descripción
Implementar la clase principal que coordina toda la optimización.

### Subtasks
- [ ] Implementar `OptimizationManager.__init__()` con componentes
- [ ] Implementar `classify_query()` para identificar tipo de consulta
- [ ] Implementar `process_query()` con flujo completo
- [ ] Implementar sistema de logging para debugging
- [ ] Crear tests básicos para el manager

### Código Clave
```python
class OptimizationManager:
    def __init__(self):
        self.cache = CacheCoordinator()
        self.templates = TemplateRenderer()
        self.metrics = TokenMonitor()
        self.agents = {
            'mlb': MLBAgent(),
            'ufc': UFCAgent(),
            'futbol': FutbolAgent(),
            'nba': NBAAgent()
        }
    
    def classify_query(self, query: str) -> str:
        # Lógica de clasificación
        pass
```

### Criterios de Aceptación
- Manager procesa consultas básicas
- Sistema de logging funcionando
- Tests pasan al 100%

## Task 3: Implementar Sistema de Caché
**ID:** OPT-003
**Status:** TODO
**Estimación:** 1.5 días
**Dependencias:** OPT-001

### Descripción
Implementar caché inteligente con TTLs específicos por tipo de dato.

### Subtasks
- [ ] Implementar `CacheCoordinator` con store en memoria
- [ ] Implementar estrategias TTL de `CACHE_CONFIG`
- [ ] Implementar generación de keys basada en query + context
- [ ] Implementar sistema de limpieza automática (LRU)
- [ ] Implementar invalidación basada en triggers
- [ ] Crear tests para hit/miss del caché

### Código Clave
```python
CACHE_CONFIG = {
    'mlb_picks': {'ttl': 300},
    'ufc_analysis': {'ttl': 600},
    'futbol_predictions': {'ttl': 900}
}

class CacheCoordinator:
    def get_cached(self, query_type: str, context: dict):
        key = self._generate_key(query_type, context)
        # Lógica de caché
```

### Criterios de Aceptación
- Hit rate >80% en consultas repetidas
- TTLs respetados correctamente
- Limpieza automática funcionando

## Task 4: Implementar Agente MLB Optimizado
**ID:** OPT-004
**Status:** TODO
**Estimación:** 2 días
**Dependencias:** OPT-002

### Descripción
Implementar agente especializado para MLB con caché de picks y respuestas optimizadas.

### Subtasks
- [ ] Crear `optimization/agents/mlb_agent.py`
- [ ] Implementar contexto mantenido (picks de hoy, stats cacheados)
- [ ] Integrar con `motor_mlb_pro.py` existente
- [ ] Implementar caché de picks de hoy (5 minutos TTL)
- [ ] Implementar respuestas precompiladas para consultas comunes
- [ ] Crear plantillas específicas para MLB

### Código Clave
```python
class MLBAgent:
    def __init__(self):
        self.context = {
            'todays_picks': None,
            'last_fetch': None,
            'cached_analyses': {}
        }
    
    def get_todays_picks(self):
        if self._needs_refresh():
            self._fetch_and_cache_picks()
        return self.context['todays_picks']
```

### Criterios de Aceptación
- Picks de hoy cacheados correctamente
- Reducción de 60% en tokens para "picks mlb hoy"
- Integración transparente con sistema existente

## Task 5: Implementar Agente UFC Optimizado
**ID:** OPT-005
**Status:** TODO
**Estimación:** 1.5 días
**Dependencias:** OPT-004

### Descripción
Implementar agente especializado para UFC con análisis precomputados.

### Subtasks
- [ ] Crear `optimization/agents/ufc_agent.py`
- [ ] Implementar caché de stats de peleadores
- [ ] Integrar con `ufc_stats_scraper.py`
- [ ] Implementar análisis precomputado por evento
- [ ] Crear plantillas compactas para visualización UFC
- [ ] Implementar sistema de actualización cuando cambian odds

### Criterios de Aceptación
- Stats de peleadores cacheados 30 minutos
- Análisis por evento precomputado
- Respuestas UFC ≤200 tokens

## Task 6: Implementar Agente Fútbol Optimizado
**ID:** OPT-006
**Status:** TODO
**Estimación:** 2 días
**Dependencias:** OPT-005

### Descripción
Implementar agente especializado para fútbol con modelo jerárquico optimizado.

### Subtasks
- [ ] Crear `optimization/agents/futbol_agent.py`
- [ ] Integrar con `espn_futbol_completo.py` (nuevo scraper)
- [ ] Implementar caché de predicciones jerárquicas
- [ ] Implementar precomputación de mejores picks por liga
- [ ] Crear plantillas jerárquicas compactas
- [ ] Implementar invalidación cuando cambian lineups

### Criterios de Aceptación
- Predicciones jerárquicas cacheadas 15 minutos
- Consulta completa ≤800 tokens
- Top 3 picks precomputados por liga

## Task 7: Implementar Sistema de Plantillas
**ID:** OPT-007
**Status:** TODO
**Estimación:** 1 día
**Dependencias:** OPT-003

### Descripción
Implementar sistema de plantillas para respuestas optimizadas.

### Subtasks
- [ ] Crear `optimization/templates.py`
- [ ] Implementar plantillas JSON para cada tipo de respuesta
- [ ] Implementar `TemplateRenderer` con soporte para múltiples formatos
- [ ] Implementar compresión inteligente de texto
- [ ] Crear sistema de emojis para conceptos comunes
- [ ] Implementar límites de tokens por plantilla

### Código Clave
```python
TEMPLATES = {
    'mlb_pick': {
        'format': 'compact',
        'max_tokens': 150,
        'fields': ['pick', 'confidence', 'stake', 'reason_short']
    }
}

class TemplateRenderer:
    def render(self, template_name: str, data: dict) -> str:
        # Renderizado optimizado
```

### Criterios de Aceptación
- Plantillas reducen tokens 40% vs texto libre
- Renderizado en <100ms
- Legibilidad mantenida (score >80%)

## Task 8: Implementar Monitoreo de Métricas
**ID:** OPT-008
**Status:** TODO
**Estimación:** 1 día
**Dependencias:** OPT-007

### Descripción
Implementar sistema de monitoreo de tokens y eficiencia.

### Subtasks
- [ ] Crear `optimization/metrics.py`
- [ ] Implementar `TokenMonitor` para tracking por consulta
- [ ] Implementar cálculo de eficiencia (información/tokens)
- [ ] Implementar sistema de alertas cuando eficiencia < objetivo
- [ ] Crear dashboard básico de métricas
- [ ] Implementar logging persistente de métricas

### Criterios de Aceptación
- Métricas registradas por cada consulta
- Alertas funcionando para eficiencia < 60%
- Dashboard muestra métricas clave

## Task 9: Integrar con Sistema Existente
**ID:** OPT-009
**Status:** TODO
**Estimación:** 1.5 días
**Dependencias:** OPT-008

### Descripción
Integrar el sistema de optimización con `main_vision_completo.py` y componentes existentes.

### Subtasks
- [ ] Crear wrapper functions en `main_vision_completo.py`
- [ ] Reemplazar llamadas directas a motores con versiones optimizadas
- [ ] Implementar migración gradual (feature flag)
- [ ] Crear sistema de fallback al motor original
- [ ] Implementar health checks del sistema optimizado
- [ ] Crear tests de integración

### Código Clave
```python
# En main_vision_completo.py
from optimization.manager import optimization_manager

def get_mlb_analysis_optimized(game_pk):
    return optimization_manager.process_query(
        f"mlb_analysis_{game_pk}",
        {'game_pk': game_pk}
    )
```

### Criterios de Aceptación
- Integración 100% compatible
- Fallback funcionando en caso de error
- Performance igual o mejor que sistema original

## Task 10: Crear Agent Hooks Optimizados
**ID:** OPT-010
**Status:** TODO
**Estimación:** 1 día
**Dependencias:** OPT-009

### Descripción
Crear agent hooks específicos para eventos comunes y reducir tokens.

### Subtasks
- [ ] Crear hook para consultas MLB frecuentes
- [ ] Crear hook para consultas UFC frecuentes
- [ ] Crear hook para consultas fútbol frecuentes
- [ ] Implementar sistema de respuestas precompiladas en hooks
- [ ] Configurar triggers basados en patrones de consulta
- [ ] Crear hooks para actualización automática de caché

### Archivos de Hooks
```
.kiro/hooks/mlb-frequent-queries.json
.kiro/hooks/ufc-frequent-queries.json  
.kiro/hooks/futbol-frequent-queries.json
.kiro/hooks/cache-auto-update.json
```

### Criterios de Aceptación
- Hooks responden en <1 segundo
- Reducción de 70% en tokens para consultas hookeadas
- Sistema de triggers funcionando correctamente

## Task 11: Implementar Sistema de Precomputación
**ID:** OPT-011
**Status:** TODO
**Estimación:** 1.5 días
**Dependencias:** OPT-010

### Descripción
Implementar sistema que precomputa datos frecuentes en background.

### Subtasks
- [ ] Crear `optimization/precomputer.py`
- [ ] Implementar schedule de precomputación (hourly/daily)
- [ ] Precomputar picks MLB para hoy cada hora
- [ ] Precomputar análisis UFC para próximo evento
- [ ] Precomputar predicciones fútbol por liga
- [ ] Implementar sistema de priorización basado en uso

### Criterios de Aceptación
- Precomputación ejecutándose en background
- Datos actualizados según schedule
- Reducción de tiempo respuesta en 50%

## Task 12: Crear Dashboard de Métricas
**ID:** OPT-012
**Status:** TODO
**Estimación:** 1 día
**Dependencias:** OPT-011

### Descripción
Crear dashboard Streamlit para monitorear eficiencia del sistema.

### Subtasks
- [ ] Crear `optimization/dashboard.py`
- [ ] Implementar métricas en tiempo real
- [ ] Mostrar gráficos de eficiencia por deporte
- [ ] Implementar historial de consultas
- [ ] Mostrar ahorro total de tokens
- [ ] Implementar controles para tuning del sistema

### Criterios de Aceptación
- Dashboard actualizable en tiempo real
- Métricas claras y accionables
- Controles para ajustar parámetros del sistema

## Task 13: Optimizaciones Avanzadas
**ID:** OPT-013
**Status:** TODO
**Estimación:** 2 días
**Dependencias:** OPT-012

### Descripción
Implementar optimizaciones avanzadas basadas en datos de uso.

### Subtasks
- [ ] Implementar A/B testing de diferentes plantillas
- [ ] Implementar ajuste dinámico de TTLs basado en precisión
- [ ] Implementar compresión avanzada de contexto
- [ ] Crear sistema de aprendizaje de patrones de consulta
- [ ] Implementar prefetching basado en historial de usuario
- [ ] Optimizar tamaño de respuestas basado en dispositivo

### Criterios de Aceptación
- Sistema auto-optimizante basado en métricas
- Mejora continua de eficiencia
- Adaptación a patrones de uso específicos

## Task 14: Testing y Validación
**ID:** OPT-014
**Status:** TODO
**Estimación:** 1.5 días
**Dependencias:** OPT-013

### Descripción
Testing exhaustivo y validación del sistema completo.

### Subtasks
- [ ] Crear tests de unidad para todos los componentes
- [ ] Crear tests de integración end-to-end
- [ ] Implementar tests de carga y performance
- [ ] Validar precisión vs sistema original
- [ ] Medir ahorro real de tokens en producción
- [ ] Crear documentación de uso y troubleshooting

### Criterios de Aceptación
- Cobertura de tests >90%
- Performance mejorada en todos los escenarios
- Precisión mantenida >95% vs sistema original

## Task 15: Despliegue y Monitoreo
**ID:** OPT-015
**Status:** TODO
**Estimación:** 1 día
**Dependencias:** OPT-014

### Descripción
Desplegar sistema en producción y configurar monitoreo continuo.

### Subtasks
- [ ] Crear script de despliegue incremental
- [ ] Configurar monitoreo de métricas clave
- [ ] Implementar sistema de rollback automático
- [ ] Crear alertas para problemas de performance
- [ ] Documentar procedimientos de operación
- [ ] Crear plan de mantenimiento continuo

### Criterios de Aceptación
- Sistema desplegado en producción
- Monitoreo 24/7 funcionando
- Plan de mantenimiento documentado

## Métricas de Éxito por Task

| Task | Objetivo Tokens | Objetivo Tiempo | Objetivo Precisión |
|------|----------------|-----------------|-------------------|
| OPT-004 | ≤150 por pick | <0.5s cache | >95% |
| OPT-005 | ≤200 por fight | <1s | >90% |
| OPT-006 | ≤800 por liga | <3s | >85% |
| OPT-007 | -40% vs texto libre | <100ms | Legibilidad >80% |
| OPT-010 | -70% consultas hook | <1s | 100% |

## Dependencias y Orden de Ejecución

```
OPT-001 → OPT-002 → OPT-003 → OPT-007 → OPT-008
     ↓        ↓         ↓         ↓         ↓
     OPT-004  OPT-005  OPT-006  OPT-009  OPT-010
        ↓        ↓         ↓         ↓         ↓
        OPT-011 → OPT-012 → OPT-013 → OPT-014 → OPT-015
```

## Riesgos y Mitigación por Task

| Task | Riesgo Principal | Mitigación |
|------|------------------|------------|
| OPT-004 | Pérdida picks actuales | Sistema de fallback a motor original |
| OPT-006 | Complejidad modelo jerárquico | Implementación incremental |
| OPT-009 | Breaking changes en integración | Feature flag + migración gradual |
| OPT-011 | Overhead de precomputación | Ejecución en background con baja prioridad |
| OPT-013 | Over-optimización | Monitoreo continuo de precisión |

## Recursos Requeridos

### Desarrollo
- 1 desarrollador full-time (2-3 semanas)
- Acceso a sistemas existentes
- Entorno de testing con datos reales

### Infraestructura
- Memoria adicional: ~500MB
- CPU: marginal increase
- Almacenamiento: ~100MB para caché persistente

### Monitoreo
- Dashboard Streamlit integrado
- Logging detallado de métricas
- Alertas por email/telegram