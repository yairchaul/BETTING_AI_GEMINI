# Implementation Plan: backtesting-real-mlb

## Overview

Plan de implementación incremental en **Python** (lenguaje del codebase existente). El orden sigue la prioridad solicitada: PRIMERO el scraper de recolección de resultados reales de los últimos 15 días, luego el Auditor, el Calculador de efectividad, el Selector con aprendizaje y, por último, la integración con la tabla `backtesting` y el caché `data/backtesting_cache/`.

Reglas transversales respetadas: módulos canónicos dentro de `motors/` y `scrapers/` (nunca en la raíz); se preserva la lógica heurística existente (decisor final, no reemplazo); cada pick conserva un ID único vinculado a la tabla `backtesting`. Las pruebas basadas en propiedades usan `hypothesis` y cubren las 10 Correctness Properties del diseño. Las pruebas unitarias del scraper usan fixtures de boxscore (sin red).

## Tasks

- [x] 1. Definir modelos de datos compartidos y tipos
  - Crear `motors/mlb_backtest_models.py` con los dataclasses `HomeRunRecord`, `StrikeoutRecord`, `GameResult`, `BacktestPick`, `Metrics` y los enums `Classification` y `PickType`
  - Implementar validación de `GameResult` (`total_runs == away_score + home_score`, `winner` es el de mayor marcador, `game_pk` único)
  - Añadir `hypothesis` a las dependencias de desarrollo (requirements-dev o equivalente)
  - _Requirements: 1.2, 2.1, 3.1_

- [x] 2. Extender el scraper de resultados reales (PRIMERA PRIORIDAD)
  - [x] 2.1 Implementar `fetch_boxscore` sobre la MLB Stats API oficial
    - En `scrapers/mlb_resultados_scraper.py`, añadir `fetch_boxscore(game_pk) -> GameResult | None` reutilizando helpers de `motors/mlb_stats_api.py`
    - Parsear `teams.home/away.players{personId: {batting.homeRuns, pitching.strikeOuts}}` para construir `home_runs[]` (HR por `personId`) y `strikeouts[]` (K por pitcher)
    - Parseo defensivo del JSON externo (nunca asumir presencia de claves); devolver `None` sin lanzar si el boxscore no está disponible
    - Preservar las firmas públicas existentes (`scrape_ultimos_dias`, `guardar_json`, `generar_reporte`, `_actualizar_equipos_trampa`)
    - _Requirements: 1.2, 1.3, 1.4, 1.6_

  - [x] 2.2 Implementar `collect_last_n_days` con idempotencia y respaldo ESPN
    - Añadir `collect_last_n_days(dias=None) -> list[GameResult]`: recorrer schedule de los últimos N días (mínimo 15), procesar solo juegos `Final`, omitir duplicados por `game_pk`
    - Hacer que `scrape_ultimos_dias` delegue en `collect_last_n_days` sin cambiar su firma
    - Implementar reintentos con backoff (3 intentos) y degradar a `_scrape_espn_fallback` (marcador-solo) marcando el partido como parcial para reintentar en la siguiente corrida
    - Persistir de forma idempotente en `data/resultados_reales_15dias.json` (fusión por `game_pk`)
    - _Requirements: 1.1, 1.5, 1.6, 1.7_

  - [ ]* 2.3 Escribir pruebas unitarias del scraper con fixtures de boxscore (sin red)
    - Crear `tests/fixtures/` con boxscores JSON reales de ejemplo (con y sin HR, con K por pitcher)
    - Probar `fetch_boxscore` (parse de HR por `personId`, K por pitcher, marcador, ganador, `total_runs`), juego no-`Final` omitido, y degradación a marcador-solo cuando el boxscore falla
    - _Requirements: 1.2, 1.3, 1.4, 1.6, 1.7_

  - [ ]* 2.4 Escribir property test de idempotencia del scraper
    - **Property 1: Idempotencia del scraper** (sin duplicados por `game_pk` al recolectar/guardar dos veces)
    - **Validates: Requirements 1.1**

  - [ ]* 2.5 Escribir property test de conservación del marcador
    - **Property 2: Conservación del marcador** (`total_runs == away_score + home_score`, `winner` = equipo con mayor marcador)
    - **Validates: Requirements 1.2**

- [x] 3. Checkpoint - Validar el scraper
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Implementar el Auditor de backtesting
  - [x] 4.1 Crear `MLBBacktestAuditor` con clasificación y emparejamiento
    - Crear `motors/mlb_backtest_auditor.py` consolidando la lógica de `mlb_real_backtester.py` y `auditor_hr.py`
    - Implementar `classify_pick(pick_text) -> PickType` y `match_game(pick, results)` usando `utils/fuzzy_matching` + `utils/mapeo_equipos` (exacto → fuzzy umbral 85%) sobre fecha y equipos
    - _Requirements: 2.7, 2.8_

  - [x] 4.2 Implementar `evaluate` por tipo de pick
    - Reglas por tipo: MONEYLINE (winner normalizado), OVER_UNDER (comparar `total_runs` vs línea), HANDICAP (Run Line: equipo + handicap vs rival), HOME_RUN (`personId` con `home_runs > 0`), STRIKEOUTS (K del pitcher vs línea)
    - Omitir auditoría de Strikeouts si `k9 == 0` o pitcher `TBD`, conservando `PENDIENTE`
    - Marcar "Sujeto a revisión" y dejar `PENDIENTE` cuando el fuzzy score esté entre 70% y 84%
    - _Requirements: 2.1, 2.4, 2.5, 2.6, 2.8, 2.9_

  - [x] 4.3 Implementar `audit_pending` con asignación de cuota y estado terminal
    - Leer picks MLB `PENDIENTE` vía `DatabaseManager`, evaluar y persistir `estado` + `cuota`
    - Asignar cuota por defecto cuando falte: 3.50 para HR, 1.90 para Handicap/OU/ML
    - Transicionar estado únicamente desde `PENDIENTE`; nunca revertir un estado terminal
    - _Requirements: 2.2, 2.3_

  - [ ]* 4.4 Escribir property test de verificación de HR por personId
    - **Property 3: HR verificado por personId** (GANADA si y solo si existe `personId` con `home_runs > 0`)
    - **Validates: Requirements 2.1**

  - [ ]* 4.5 Escribir property test de cuota nunca nula
    - **Property 4: Cuota nunca nula** (tras auditar, toda cuota está definida; default 1.90/3.50 según tipo)
    - **Validates: Requirements 2.2**

  - [ ]* 4.6 Escribir property test de estado terminal monótono
    - **Property 5: Estado terminal monótono** (GANADA/PERDIDA nunca vuelve a PENDIENTE; solo transiciona desde PENDIENTE)
    - **Validates: Requirements 2.3**

  - [ ]* 4.7 Escribir pruebas unitarias de `evaluate` y `match_game`
    - Casos: ML acierto/fallo, OU sobre/bajo línea, Handicap (+1.5 perdiendo por 1 = GANADA), HR con/sin `home_runs>0`, K sobre/bajo línea, fuzzy ESPN español vs nombre estándar, y rango fuzzy 70-84% que deja PENDIENTE
    - _Requirements: 2.4, 2.5, 2.6, 2.7, 2.8, 2.9_

- [x] 5. Checkpoint - Validar el Auditor
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implementar el Calculador de efectividad
  - [x] 6.1 Crear `EffectivenessCalculator` con cómputo de métricas
    - Crear `motors/mlb_effectiveness.py` con `compute_by_pick_type` y `compute_by_team`
    - Calcular `win_rate = hits/total * 100`, `profit += (cuota-1)` en GANADA y `-1` en PERDIDA, `roi = profit/total * 100`, y `last_10` (más reciente primero)
    - _Requirements: 3.1, 3.2_

  - [x] 6.2 Implementar `classify` y detección de Equipo_Trampa
    - Fronteras de steering: ÉLITE (WR>65% y ROI>+20%), CONFIANZA (WR 55-65% y ROI+), RIESGO (WR 45-55%), EVITAR (WR<45% o ROI<-15%)
    - Marcar Equipo_Trampa cuando WR<40% en los últimos 10 picks
    - _Requirements: 3.3, 3.4, 3.5, 3.6, 3.7, 3.8_

  - [ ]* 6.3 Escribir property test de cota de win rate
    - **Property 6: Cota de win rate** (`0 <= win_rate <= 100` y `hits <= total`)
    - **Validates: Requirements 3.1**

  - [ ]* 6.4 Escribir property test de clasificación total y excluyente
    - **Property 7: Clasificación total y excluyente** (toda `Metrics` con `total>0` recibe exactamente una clasificación)
    - **Validates: Requirements 3.2**

  - [ ]* 6.5 Escribir pruebas unitarias de `classify` en las fronteras
    - Probar 64.9 vs 65.1 WR, ROI +19 vs +21, y los límites 45/55%
    - _Requirements: 3.4, 3.5, 3.6, 3.7_

- [x] 7. Implementar el Selector con aprendizaje
  - [x] 7.1 Crear `LearningPickSelector` con confianza ajustada
    - Crear `motors/mlb_learning_selector.py` como capa por encima de `MotorDecisionInteligente` (no lo reemplaza, no recalcula heurística)
    - Implementar `adjusted_confidence(pick_type, equipo, base_confidence)` con factor en `[0.5, 1.3]` derivado de la clasificación, sin mutar `base_confidence`; resultado en `[0, 99]`
    - Aplicar penalización de estadio (factor adicional) cuando `factor_hr(venue) < 0.90` para HR
    - _Requirements: 4.1, 4.3_

  - [x] 7.2 Implementar `select_best_pick` con exclusiones, jerarquía y stake
    - Partir de los candidatos de `MotorDecisionInteligente.decidir_pick`; excluir equipos EVITAR/Equipo_Trampa
    - Aplicar jerarquía base MLB (STRIKEOUTS > HOME_RUN > MONEYLINE) como desempate, ajustable por histórico
    - Si todos quedan excluidos, devolver Handicap progresivo de protección (logica-dinamica)
    - Asignar `id` único vinculado a `backtesting` y stake derivado de confianza ajustada + clasificación del equipo
    - _Requirements: 4.2, 4.4, 4.5, 4.6_

  - [ ]* 7.3 Escribir property test de no sobrescritura heurística
    - **Property 8: No sobrescritura heurística** (`confianza_ajustada` se deriva sin mutar `confianza_base` ni salidas heurísticas)
    - **Validates: Requirements 4.1**

  - [ ]* 7.4 Escribir property test de exclusión de equipos EVITAR/TRAMPA
    - **Property 9: Exclusión de equipos EVITAR/TRAMPA** (el pick final nunca es de un equipo EVITAR o TRAMPA)
    - **Validates: Requirements 4.2**

  - [ ]* 7.5 Escribir property test de penalización de estadio
    - **Property 10: Penalización de estadio** (con `factor_hr < 0.90`, la confianza ajustada de HR es estrictamente menor que sin penalización)
    - **Validates: Requirements 4.3**

  - [ ]* 7.6 Escribir pruebas unitarias del selector
    - Casos: desempate por jerarquía, fallback de Handicap progresivo cuando todo se excluye, stake por confianza + clasificación
    - _Requirements: 4.4, 4.5, 4.6_

- [x] 8. Checkpoint - Validar efectividad y selección
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Integrar persistencia con la tabla `backtesting` y el caché
  - [x] 9.1 Implementar persistencia del Auditor en SQLite
    - Crear tabla opcional `backtesting_audit` (sin romper el esquema existente) y escribir `estado`/`cuota` en `backtesting` vía `DatabaseManager`
    - _Requirements: 2.2, 2.3_

  - [x] 9.2 Implementar persistencia de efectividad en el caché
    - Añadir `persist()` que escribe `data/backtesting_cache/pick_type_performance.json` y `team_performance.json` (crear el directorio si no existe)
    - _Requirements: 3.9_

  - [ ]* 9.3 Escribir test de integración end-to-end con DB SQLite temporal
    - Insertar picks PENDIENTE de los 4 tipos → recolectar (fixtures) → auditar → calcular efectividad → seleccionar pick; afirmar estados, cuotas y exclusión de equipos EVITAR
    - _Requirements: 2.3, 3.9, 4.2, 4.6_

- [x] 10. Crear la suite de pruebas ejecutable
  - Crear `tests/test_backtesting_real_mlb.py` (o `conftest.py` + módulos) que agrupe unit, property e integración
  - Asegurar ejecución sin red (fixtures) y dejar documentado el comando de ejecución (`pytest tests/ --run` equivalente, sin watch)
  - _Requirements: 1.1, 1.2, 2.1, 2.2, 2.3, 3.1, 3.2, 4.1, 4.2, 4.3_

- [x] 11. Checkpoint final - Asegurar que toda la suite pasa
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Las tareas marcadas con `*` son opcionales (pruebas) y pueden omitirse para un MVP más rápido, aunque las property tests cubren las 10 Correctness Properties del diseño.
- Cada tarea referencia cláusulas de requisitos específicas para trazabilidad.
- Los checkpoints aseguran validación incremental siguiendo la prioridad solicitada (scraper primero).
- Las pruebas del scraper usan fixtures de boxscore (sin llamadas de red); las property tests usan `hypothesis`.
- Se preservan los módulos canónicos en `motors/` y `scrapers/`, la lógica heurística existente y el ID único por pick.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1"] },
    { "id": 1, "tasks": ["2.1"] },
    { "id": 2, "tasks": ["2.2"] },
    { "id": 3, "tasks": ["2.3", "2.4", "2.5", "4.1"] },
    { "id": 4, "tasks": ["4.2"] },
    { "id": 5, "tasks": ["4.3", "4.4", "4.7", "6.1"] },
    { "id": 6, "tasks": ["4.5", "4.6", "6.2", "7.1"] },
    { "id": 7, "tasks": ["6.3", "6.4", "6.5", "7.2"] },
    { "id": 8, "tasks": ["7.3", "7.4", "7.5", "7.6", "9.1", "9.2"] },
    { "id": 9, "tasks": ["9.3", "10"] }
  ]
}
```
