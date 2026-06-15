# Requirements Document

## Introduction

`backtesting-real-mlb` cierra el bucle de aprendizaje de BETTING_AI para MLB. El sistema ya genera picks (Home Run, Moneyline, Over/Under, Strikeouts) con motores heurísticos, pero no mide de forma fiable qué tan bien acierta cada tipo de pick ni cada equipo. Esta feature define cuatro capas encadenadas derivadas del diseño aprobado:

1. **Recolección de resultados reales** desde la MLB Stats API oficial (boxscores) en una ventana mínima de 15 días, con marcador, ganador, total de carreras, Home Runs por `personId` y strikeouts por pitcher.
2. **Auditoría** que cruza cada predicción histórica de la tabla `backtesting` contra el resultado real y la marca `GANADA`/`PERDIDA` con su cuota.
3. **Cálculo de efectividad** que produce win rate, ROI y clasificación (ÉLITE/CONFIANZA/RIESGO/EVITAR) por tipo de pick y por equipo.
4. **Selección con aprendizaje** que, por partido, ajusta la confianza heurística con el histórico real sin sobrescribir el cálculo heurístico.

Estos requisitos respetan las reglas de steering del proyecto: se preserva la lógica heurística (decisor final, no reemplazo), cada pick tiene un ID único vinculado a la tabla `backtesting`, y la normalización de nombres usa coincidencia exacta primero y fuzzy `WRatio` con umbral 85%.

## Glossary

- **Scraper_Resultados**: Componente `MLBResultadosScraper` (extendido) que recolecta resultados Final desde la MLB Stats API oficial y los persiste de forma idempotente.
- **Auditor_Backtesting**: Componente `MLBBacktestAuditor` que cruza cada pick PENDIENTE contra el resultado real y asigna estado terminal y cuota.
- **Calculador_Efectividad**: Componente `EffectivenessCalculator` que computa win rate, ROI y clasificación por tipo de pick y por equipo.
- **Selector_Aprendizaje**: Componente `LearningPickSelector` que elige el pick final por partido ajustando la confianza heurística con el histórico real.
- **Normalizador**: Lógica reutilizada (`utils/fuzzy_matching` + `utils/mapeo_equipos`) que resuelve nombres por coincidencia exacta y, si falla, por fuzzy `WRatio` con umbral 85%.
- **GameResult**: Registro de resultado real de un partido (marcador, ganador, total de carreras, HR por `personId`, K por pitcher, `venue`, `game_pk`).
- **BacktestPick**: Predicción registrada en la tabla `backtesting` con `id` único, `cuota` y `estado`.
- **personId**: Identificador oficial de jugador de la MLB Stats API.
- **game_pk**: Clave única de partido de la MLB Stats API, usada como clave de idempotencia.
- **factor_hr**: Factor de Home Run del estadio (`venue`); valores menores a 0.90 indican estadios desfavorables a HR.
- **Equipo_Trampa**: Equipo con win rate menor al 40% en los últimos 10 picks de la tabla `backtesting`.
- **Run_Line**: Handicap de carreras (por ejemplo `+1.5` / `-1.5`) usado para evaluar picks de handicap.
- **win_rate**: Porcentaje de aciertos sobre el total de picks auditados, en el rango 0 a 100.
- **ROI**: Retorno sobre la inversión expresado en porcentaje, calculado como `profit / total * 100`.

## Requirements

### Requirement 1: Recolección de resultados reales

**User Story:** Como operador del sistema de backtesting, quiero recolectar los resultados reales de los partidos de MLB de los últimos días desde la fuente oficial, para auditar las predicciones contra datos verificables.

#### Acceptance Criteria

1. WHEN el Scraper_Resultados ejecuta la recolección dos veces consecutivas sobre la misma ventana de días, THE Scraper_Resultados SHALL producir un conjunto de GameResult sin entradas duplicadas por game_pk.
2. WHEN el Scraper_Resultados construye un GameResult a partir de un boxscore, THE Scraper_Resultados SHALL asignar `total_runs` igual a `away_score + home_score` y `winner` igual al equipo con mayor marcador.
3. WHEN el Scraper_Resultados procesa el boxscore de un partido Final, THE Scraper_Resultados SHALL registrar cada Home Run conectado con su `personId`, `fullName` y `equipo` desde la MLB Stats API oficial.
4. WHEN el Scraper_Resultados procesa el boxscore de un partido Final, THE Scraper_Resultados SHALL registrar los strikeouts de cada pitcher con su `personId` desde la MLB Stats API oficial.
5. WHEN el Scraper_Resultados inicia una recolección, THE Scraper_Resultados SHALL cubrir una ventana de al menos 15 días previos.
6. IF un partido no se encuentra en estado `Final`, THEN THE Scraper_Resultados SHALL omitir ese partido de la recolección.
7. IF la MLB Stats API no responde tras 3 reintentos con backoff para un partido, THEN THE Scraper_Resultados SHALL degradar a marcador-solo mediante el respaldo ESPN y marcar el partido como parcial para reintentar su boxscore en la siguiente corrida.

### Requirement 2: Auditoría de predicciones contra resultados reales

**User Story:** Como analista de apuestas, quiero que cada predicción histórica pendiente se audite contra el resultado real, para conocer con exactitud qué picks ganaron o perdieron y con qué cuota.

#### Acceptance Criteria

1. WHEN el Auditor_Backtesting evalúa un pick de Home Run, THE Auditor_Backtesting SHALL marcarlo como `GANADA` si y solo si existe un `personId` del bateador en el boxscore con `home_runs` mayor que 0, y `PERDIDA` en caso contrario.
2. WHEN el Auditor_Backtesting marca el estado de un pick y la cuota real no está disponible, THE Auditor_Backtesting SHALL asignar una cuota por defecto de 3.50 para picks de Home Run y de 1.90 para picks de Handicap, Over/Under y Moneyline.
3. WHILE un pick tiene estado `GANADA` o `PERDIDA`, THE Auditor_Backtesting SHALL mantener ese estado terminal y transicionar el estado únicamente desde `PENDIENTE`.
4. WHEN el Auditor_Backtesting evalúa un pick de Handicap, THE Auditor_Backtesting SHALL aplicar la regla de Run_Line marcando `GANADA` cuando el marcador del equipo más el handicap supera el marcador del rival.
5. WHEN el Auditor_Backtesting evalúa un pick de Moneyline, THE Auditor_Backtesting SHALL marcarlo como `GANADA` si el pick corresponde al `winner` normalizado del partido, y `PERDIDA` en caso contrario.
6. WHEN el Auditor_Backtesting evalúa un pick de Over/Under, THE Auditor_Backtesting SHALL comparar `total_runs` contra la línea del pick y marcar `GANADA` cuando se cumple el sentido (over o under) indicado.
7. WHEN el Auditor_Backtesting empareja un pick con un partido, THE Auditor_Backtesting SHALL usar el Normalizador con coincidencia exacta y fuzzy de umbral 85% sobre fecha y equipos.
8. IF la coincidencia fuzzy de un nombre obtiene un score entre 70% y 84%, THEN THE Auditor_Backtesting SHALL marcar el dato como "Sujeto a revisión" y dejar el pick en estado `PENDIENTE`.
9. IF un pick de Strikeouts tiene `k9` igual a 0 o el pitcher es `TBD`, THEN THE Auditor_Backtesting SHALL omitir la auditoría de ese pick y conservar su estado `PENDIENTE`.

### Requirement 3: Cálculo de efectividad y clasificación

**User Story:** Como analista de apuestas, quiero métricas de efectividad por tipo de pick y por equipo, para identificar qué mercados y equipos rinden mejor.

#### Acceptance Criteria

1. WHEN el Calculador_Efectividad computa métricas por tipo de pick y por equipo, THE Calculador_Efectividad SHALL producir un `win_rate` dentro del rango 0 a 100 y un número de aciertos menor o igual al total de picks.
2. WHEN el Calculador_Efectividad computa el retorno, THE Calculador_Efectividad SHALL calcular el ROI como `profit / total * 100`, acumulando `(cuota - 1)` por cada pick `GANADA` y `-1` por cada pick `PERDIDA`.
3. WHEN el Calculador_Efectividad clasifica una métrica con total mayor que 0, THE Calculador_Efectividad SHALL asignar exactamente una clasificación entre ÉLITE, CONFIANZA, RIESGO y EVITAR.
4. WHERE el win rate es mayor que 65% y el ROI mayor que +20%, THE Calculador_Efectividad SHALL clasificar la métrica como ÉLITE.
5. WHERE el win rate está entre 55% y 65% y el ROI es positivo, THE Calculador_Efectividad SHALL clasificar la métrica como CONFIANZA.
6. WHERE el win rate está entre 45% y 55%, THE Calculador_Efectividad SHALL clasificar la métrica como RIESGO.
7. WHERE el win rate es menor que 45% o el ROI menor que -15%, THE Calculador_Efectividad SHALL clasificar la métrica como EVITAR.
8. WHEN el Calculador_Efectividad evalúa un equipo con win rate menor al 40% en los últimos 10 picks, THE Calculador_Efectividad SHALL marcar ese equipo como Equipo_Trampa.
9. WHEN el Calculador_Efectividad finaliza el cómputo, THE Calculador_Efectividad SHALL persistir las métricas en `data/backtesting_cache/pick_type_performance.json` y `data/backtesting_cache/team_performance.json`.

### Requirement 4: Selección de pick con aprendizaje

**User Story:** Como apostador, quiero que el sistema elija el pick final por partido ajustando la confianza con el histórico real, para apostar a los mercados con mayor probabilidad de acierto sin perder la base heurística.

#### Acceptance Criteria

1. WHEN el Selector_Aprendizaje calcula la confianza ajustada de un candidato, THE Selector_Aprendizaje SHALL derivar `confianza_ajustada` sin modificar la `confianza_base` ni las salidas de los motores heurísticos.
2. WHEN el Selector_Aprendizaje selecciona el pick final de un partido, THE Selector_Aprendizaje SHALL excluir todo candidato cuyo equipo esté clasificado como EVITAR o marcado como Equipo_Trampa.
3. WHEN el Selector_Aprendizaje evalúa un candidato de Home Run en un estadio con `factor_hr` menor que 0.90, THE Selector_Aprendizaje SHALL asignar una `confianza_ajustada` estrictamente menor que la que tendría sin la penalización de estadio.
4. WHEN el Selector_Aprendizaje ordena los candidatos válidos, THE Selector_Aprendizaje SHALL aplicar la jerarquía base MLB (STRIKEOUTS, luego HOME_RUN, luego MONEYLINE) como desempate, ajustable por la efectividad histórica.
5. IF todos los candidatos de un partido quedan excluidos, THEN THE Selector_Aprendizaje SHALL devolver un Handicap progresivo de protección de capital.
6. WHEN el Selector_Aprendizaje produce el pick final, THE Selector_Aprendizaje SHALL asignar un `id` único vinculado a la tabla `backtesting` y un stake derivado de la confianza ajustada y la clasificación del equipo.
