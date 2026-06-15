# Design: Arquitectura de Optimización de Tokens

## Visión de Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                    CAPA DE PRESENTACIÓN                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Streamlit │  │     CLI     │  │     API     │         │
│  │   Dashboard │  │  Interface  │  │   REST/WS   │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
                               │
┌─────────────────────────────────────────────────────────────┐
│                 CAPA DE OPTIMIZACIÓN                         │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Optimización Manager                    │    │
│  │  • Cache Coordinator     • Token Counter            │    │
│  │  • Template Renderer     • Efficiency Analyzer      │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                               │
┌─────────────────────────────────────────────────────────────┐
│                 CAPA DE AGENTES ESPECIALIZADOS              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   MLB Agent │  │   UFC Agent │  │ Futbol Agent│         │
│  │             │  │             │  │             │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│  ┌─────────────┐                                           │
│  │   NBA Agent │  (Contexto mantenido 24h por agente)      │
│  │             │                                           │
│  └─────────────┘                                           │
└─────────────────────────────────────────────────────────────┘
                               │
┌─────────────────────────────────────────────────────────────┐
│                 CAPA DE DATOS Y CACHÉ                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Cache     │  │  Precomputed│  │    Live     │         │
│  │  Manager    │  │   Predictions│  │   Data      │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                Database Layer                        │    │
│  │  • SQLite (existing) • JSON Files • Memory Cache    │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Componentes Principales

### 1. Optimización Manager
**Responsabilidad:** Coordinar toda la optimización de tokens

**Estructura:**
```python
class OptimizationManager:
    def __init__(self):
        self.cache_coordinator = CacheCoordinator()
        self.token_counter = TokenCounter()
        self.template_renderer = TemplateRenderer()
        self.efficiency_analyzer = EfficiencyAnalyzer()
        self.agent_dispatcher = AgentDispatcher()
    
    def process_query(self, query: str, context: dict) -> dict:
        """Procesa consulta optimizando tokens"""
        # 1. Identificar tipo de consulta
        query_type = self._classify_query(query)
        
        # 2. Verificar caché
        cached_response = self.cache_coordinator.get_cached(query_type, context)
        if cached_response:
            return self._format_cached_response(cached_response)
        
        # 3. Dispatchear a agente especializado
        agent = self.agent_dispatcher.get_agent(query_type)
        raw_response = agent.process(query, context)
        
        # 4. Optimizar respuesta
        optimized_response = self._optimize_response(raw_response, query_type)
        
        # 5. Cachear si es apropiado
        if self._should_cache(query_type, raw_response):
            self.cache_coordinator.cache_response(query_type, context, optimized_response)
        
        # 6. Registrar métricas
        self._log_metrics(query, optimized_response)
        
        return optimized_response
```

### 2. Agentes Especializados por Deporte
**Patrón:** Cada agente mantiene contexto específico

**MLB Agent:**
```python
class MLBAgent:
    def __init__(self):
        self.context = {
            'loaded_datasets': ['hr_stats', 'pitcher_stats', 'team_stats'],
            'cached_predictions': {},  # game_pk -> prediction
            'last_update': None,
            'active_picks': []  # Picks de hoy cacheados
        }
    
    def process(self, query: str, user_context: dict) -> dict:
        # Mantener picks de hoy en memoria
        if not self.context['active_picks'] or self._needs_refresh():
            self.context['active_picks'] = self._fetch_todays_picks()
        
        # Procesar consultas comunes desde caché
        if query in ["picks mlb hoy", "mlb picks today", "apuestas mlb"]:
            return self._get_cached_picks_response()
        
        # Consulta específica, usar motor normal
        return self._process_specific_query(query, user_context)
```

**UFC Agent:**
```python
class UFCAgent:
    def __init__(self):
        self.context = {
            'current_event': None,
            'fighters_stats': {},  # nombre -> stats
            'cached_analysis': {},  # fight_id -> analysis
            'prediction_models': ['heuristic', 'gemini', 'premium']
        }
```

**Futbol Agent:**
```python
class FutbolAgent:
    def __init__(self):
        self.context = {
            'hierarchical_model': HierarchicalModel(),
            'league_data': {},  # liga -> partidos
            'cached_predictions': {},  # match_id -> predictions
            'template_responses': self._load_templates()
        }
```

### 3. Sistema de Caché Inteligente
**Estrategias TTL por tipo de dato:**

```python
CACHE_CONFIG = {
    'mlb_picks': {
        'ttl': 300,  # 5 minutos
        'strategy': 'time_based',
        'invalidation_triggers': ['lineup_change', 'pitcher_change']
    },
    'ufc_analysis': {
        'ttl': 600,  # 10 minutos
        'strategy': 'event_based',
        'invalidation_triggers': ['odds_change', 'weight_in']
    },
    'futbol_predictions': {
        'ttl': 900,  # 15 minutos
        'strategy': 'accuracy_based',
        'invalidation_triggers': ['lineup_release', 'weather_change']
    },
    'general_stats': {
        'ttl': 1800,  # 30 minutos
        'strategy': 'time_based'
    }
}
```

**Implementación:**
```python
class CacheCoordinator:
    def __init__(self):
        self.cache_store = {}  # key -> (data, timestamp, metadata)
        self.config = CACHE_CONFIG
        
    def get_cached(self, query_type: str, context: dict) -> Optional[dict]:
        cache_key = self._generate_key(query_type, context)
        
        if cache_key in self.cache_store:
            data, timestamp, metadata = self.cache_store[cache_key]
            
            # Verificar TTL
            ttl = self.config.get(query_type, {}).get('ttl', 300)
            if time.time() - timestamp < ttl:
                return data
        
        return None
    
    def cache_response(self, query_type: str, context: dict, response: dict):
        cache_key = self._generate_key(query_type, context)
        metadata = {
            'query_type': query_type,
            'tokens_saved': self._calculate_tokens_saved(response),
            'created_at': time.time()
        }
        self.cache_store[cache_key] = (response, time.time(), metadata)
        
        # Limpieza automática
        self._cleanup_old_entries()
```

### 4. Sistema de Plantillas Optimizadas
**Estructura de plantilla:**
```json
{
  "mlb_pick_template": {
    "format": "compact",
    "fields": ["pick", "confidence", "stake", "reason_short"],
    "emoji_mapping": {
      "high_confidence": "🔥",
      "medium_confidence": "✅", 
      "low_confidence": "📊"
    },
    "max_tokens": 150
  },
  "ufc_fight_template": {
    "format": "comparison",
    "fields": ["fighter1", "fighter2", "heuristic_pick", "ai_pick", "edge"],
    "max_tokens": 200
  },
  "futbol_summary_template": {
    "format": "hierarchical",
    "fields": ["best_pick", "secondary_picks", "confidence", "expected_value"],
    "max_tokens": 180
  }
}
```

**Renderer:**
```python
class TemplateRenderer:
    def render(self, template_name: str, data: dict) -> str:
        template = self.templates[template_name]
        
        if template['format'] == 'compact':
            return self._render_compact(template, data)
        elif template['format'] == 'comparison':
            return self._render_comparison(template, data)
        elif template['format'] == 'hierarchical':
            return self._render_hierarchical(template, data)
    
    def _render_compact(self, template, data):
        # Ejemplo: "🔥 NYY ML @ 65% | 2u (Power: 120)"
        emoji = template['emoji_mapping'].get(
            'high_confidence' if data['confidence'] > 70 else 
            'medium_confidence' if data['confidence'] > 50 else 
            'low_confidence'
        )
        return f"{emoji} {data['pick']} @ {data['confidence']}% | {data['stake']} ({data['reason_short'][:30]})"
```

### 5. Sistema de Monitoreo de Tokens
**Métricas clave:**
```python
class TokenMonitor:
    def track_query(self, original_query: str, optimized_response: dict):
        metrics = {
            'query_length': len(original_query),
            'response_tokens': self._count_tokens(optimized_response),
            'cache_hit': optimized_response.get('from_cache', False),
            'processing_time': optimized_response.get('processing_time', 0),
            'efficiency_score': self._calculate_efficiency(original_query, optimized_response)
        }
        
        self._store_metrics(metrics)
        self._check_alerts(metrics)
    
    def _calculate_efficiency(self, query, response):
        # Eficiencia = información / tokens
        info_score = self._calculate_information_score(response)
        token_count = self._count_tokens(response)
        return info_score / max(token_count, 1)
```

## Flujos de Datos

### Flujo 1: Consulta Cacheada
```
Usuario: "picks mlb hoy"
   ↓
OptimizationManager.classify_query() → "mlb_picks"
   ↓
CacheCoordinator.get_cached("mlb_picks") → HIT
   ↓
TemplateRenderer.render("mlb_pick_template", cached_data)
   ↓
Respuesta optimizada (≤150 tokens, <0.5s)
```

### Flujo 2: Consulta Nueva con Optimización
```
Usuario: "Análisis detallado NYY vs BOS"
   ↓
OptimizationManager.classify_query() → "mlb_specific"
   ↓
CacheCoordinator.get_cached() → MISS
   ↓
AgentDispatcher.get_agent("mlb") → MLBAgent
   ↓
MLBAgent.process() → Raw analysis
   ↓
TemplateRenderer.render("mlb_detailed_template", analysis)
   ↓
CacheCoordinator.cache_response() para futuras consultas similares
   ↓
Respuesta optimizada (≤300 tokens, <2s)
```

### Flujo 3: Consulta Jerárquica Completa
```
Usuario: "Mejores apuestas fútbol hoy"
   ↓
OptimizationManager → "futbol_hierarchical"
   ↓
FutbolAgent.process_hierarchical()
   ↓
   • Cargar datos de ligas (cache)
   • Ejecutar modelo jerárquico
   • Ordenar por expected value
   ↓
TemplateRenderer.render("futbol_hierarchical_template", results)
   ↓
Respuesta con top 3 picks (≤250 tokens, <3s)
```

## Estrategias de Optimización Específicas

### 1. Compresión de Texto
```python
def compress_text(text: str, target_tokens: int) -> str:
    """Compresión inteligente manteniendo significado"""
    # Remover redundancias
    text = re.sub(r'\s+', ' ', text)
    
    # Acortar frases comunes
    replacements = {
        'probabilidad de': 'prob',
        'confianza de': 'conf',
        'recomendación': 'rec',
        'stake recomendado': 'stake'
    }
    
    for long, short in replacements.items():
        text = text.replace(long, short)
    
    # Usar emojis para conceptos comunes
    emoji_map = {
        'alta confianza': '🔥',
        'valor oculto': '💎',
        'evitar': '❌',
        'considerar': '🟡'
    }
    
    return text
```

### 2. Caché de Respuestas Completas
```python
class FullResponseCache:
    def __init__(self):
        self.responses = {}  # hash(query+context) -> response
        
    def get(self, query: str, context: dict) -> Optional[str]:
        key = self._hash_query(query, context)
        return self.responses.get(key)
    
    def store(self, query: str, context: dict, response: str):
        key = self._hash_query(query, context)
        self.responses[key] = response
        
        # LRU eviction
        if len(self.responses) > 1000:
            oldest_key = min(self.responses.keys(), 
                           key=lambda k: self.responses[k]['timestamp'])
            del self.responses[oldest_key]
```

### 3. Sistema de Precomputación
```python
class PrecomputationEngine:
    def __init__(self):
        self.schedule = {
            'hourly': ['mlb_picks', 'ufc_odds'],
            'daily': ['futbol_predictions', 'nba_props'],
            'weekly': ['team_stats', 'player_trends']
        }
    
    def run_scheduled_precomputation(self):
        for frequency, computations in self.schedule.items():
            if self._should_run(frequency):
                for computation in computations:
                    self._precompute(computation)
    
    def _precompute(self, computation_type: str):
        if computation_type == 'mlb_picks':
            # Precomputar todos los picks de hoy
            picks = self._compute_all_mlb_picks()
            self._store_precomputed('mlb_picks_today', picks)
```

## Integración con Sistema Existente

### Hook en main_vision_completo.py
```python
# En main_vision_completo.py
from optimization.manager import OptimizationManager

optimizer = OptimizationManager()

# Reemplazar llamadas directas a motores
def get_mlb_analysis_optimized(game_pk):
    query = f"mlb_analysis_{game_pk}"
    context = {'game_pk': game_pk}
    return optimizer.process_query(query, context)

def get_ufc_predictions_optimized(event_id):
    query = f"ufc_predictions_{event_id}"
    context = {'event_id': event_id}
    return optimizer.process_query(query, context)
```

### Migración Gradual
1. **Fase 1:** Agregar optimizador como wrapper transparente
2. **Fase 2:** Medir eficiencia por componente
3. **Fase 3:** Migrar componentes más usados primero
4. **Fase 4:** Sistema completo optimizado

## Consideraciones de Performance

### Límites de Memoria
- Cada agente: ≤50MB contexto
- Caché total: ≤500MB
- Respuestas en memoria: ≤1000 entries

### Límites de CPU
- Procesamiento consulta: ≤100ms promedio
- Precomputación: background, ≤10% CPU
- Actualización caché: async, no bloqueante

### Límites de Red
- Llamadas API externas: ≤10/s
- Tamaño respuestas: ≤10KB
- Latencia caché: ≤5ms

## Plan de Implementación

### Sprint 1: Núcleo de Optimización
- OptimizationManager básico
- Sistema de caché simple
- 2 agentes (MLB, UFC)

### Sprint 2: Sistema Completo
- Todos los agentes especializados
- Sistema de plantillas
- Monitoreo básico

### Sprint 3: Optimizaciones Avanzadas
- Precomputación automática
- Ajuste dinámico de TTL
- Dashboard de métricas

### Sprint 4: Integración y Tuning
- Migración completa
- A/B testing
- Optimización final