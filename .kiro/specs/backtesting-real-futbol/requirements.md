# Requirements Document

## Introduction

`backtesting-real-futbol` cierra el bucle de aprendizaje de BETTING_AI para fútbol, replicando la arquitectura ya validada de `backtesting-real-mlb`. Hoy los motores heurísticos `motors/futbol_analyzer_jerarquico.py` y `motors/motor_fut_pro.py` generan picks (OVER 1.5 1T, OVER 2.5, OVER 3.5, BTTS, MONEYLINE 1X2, HANDICAP y opcionalmente ANYTIME GOALSCORER), pero el sistema no mide de forma fiable qué tipo de pick ni qué equipo rinde mejor, por lo que las heurísticas se siguen aplicando ciegas. Esta feature define cuatro capas encadenadas alineadas con la versión MLB:

1. **Recolección de resultados reales** desde una fuente oficial/estructurada (api-football u otra API JSON; ESPN soccer queda como respaldo de marcador) en una ventana mínima de 15 días, con marcador final, marcador al medio tiempo, ganador 1X2 (incluye empate), goles totales, BTTS, lista de goleadores y `venue`.
2. **Auditoría** que cruza cada predicción histórica de la tabla `backtesting` con `deporte = 'FUTBOL'` contra el resultado real y la marca `GANADA`/`PERDIDA` con su cuota.
3. **Cálculo de efectividad** que produce win rate, ROI y clasificación (ÉLITE/CONFIANZA/RIESGO/EVITAR) por tipo de pick y por equipo, aplicando la regla `Equipo_Trampa` (win rate menor al 40% en los últimos 10 picks).
4. **Selección con aprendizaje** que, por partido, ajusta la confianza heurística con el histórico real sin sobrescribir el cálculo heurístico, respeta la jerarquía de fútbol como desempate y habilita un fallback de Handicap progresivo cuando todos los candidatos quedan excluidos.

La prioridad funcional es estar listos para la **Copa Mundial de la FIFA**, por lo que el scraper debe cubrir competiciones de selecciones (Mundial, Eurocopa, Copa América, Nations League) y las grandes ligas europeas y americanas. Estos requisitos respetan los steering del proyecto: módulos canónicos viven bajo `motors/` y `scrapers/` (nunca en la raíz); las heurísticas no se sobrescriben (la capa de aprendizaje es decisor final); cada pick tiene un `id` único vinculado a la tabla `backtesting`; la normalización de equipos usa coincidencia exacta primero y fuzzy `WRatio` con umbral 85% (banda 70-84% queda "Sujeto a revisión"); el caché de fútbol vive en `data/backtesting_cache/futbol/` para no colisionar con MLB.

## Glossary

- **Scraper_Resultados_Futbol**: Componente `FutbolResultadosScraper` (módulo canónico bajo `scrapers/`) que recolecta resultados Final desde una fuente oficial estructurada y los persiste de forma idempotente.
- **Auditor_Backtesting_Futbol**: Componente `FutbolBacktestAuditor` (bajo `motors/`) que cruza cada pick de fútbol PENDIENTE contra el resultado real y asigna estado terminal y cuota.
- **Calculador_Efectividad_Futbol**: Componente `FutbolEffectivenessCalculator` (bajo `motors/`) que computa win rate, ROI y clasificación por tipo de pick y por equipo de fútbol.
- **Selector_Aprendizaje_Futbol**: Componente `FutbolLearningPickSelector` (bajo `motors/`) que elige el pick final por partido ajustando la confianza heurística con el histórico real, sin alterar a `futbol_analyzer_jerarquico` ni a `motor_fut_pro`.
- **Normalizador_Futbol**: Lógica de resolución de nombres reutilizada o extendida (`utils/fuzzy_matching` + `utils/mapeo_equipos` y, si aplica, `utils/fuzzy_matching_futbol.py`) que aplica coincidencia exacta y, si falla, fuzzy `WRatio` con umbral 85%.
- **MatchResult**: Registro de resultado real de un partido con `match_id`, `fecha`, `liga`, `home`, `away`, `home_score`, `away_score`, `home_score_ht`, `away_score_ht`, `total_goals_ft`, `total_goals_ht`, `both_teams_scored`, `result_1x2`, `goalscorers` (opcional), `venue` y `status`.
- **BacktestPick**: Predicción registrada en la tabla `backtesting` con `id` único, `cuota`, `estado` y `deporte = 'FUTBOL'`.
- **match_id**: Identificador único del partido en la fuente de datos (event id de ESPN o fixture id de api-football), usado como clave de idempotencia.
- **OVER_1_5_1T**: Tipo de pick que gana cuando `total_goals_ht` es mayor o igual a 2 (más de 1 gol en el primer tiempo).
- **OVER_2_5**: Tipo de pick que gana cuando `total_goals_ft` es mayor o igual a 3.
- **OVER_3_5**: Tipo de pick que gana cuando `total_goals_ft` es mayor o igual a 4.
- **BTTS**: Both Teams To Score; tipo de pick que gana cuando `home_score >= 1` y `away_score >= 1`.
- **MONEYLINE_1X2**: Tipo de pick con tres resultados posibles `1` (gana home), `X` (empate) o `2` (gana away).
- **HANDICAP**: Tipo de pick de handicap asiático o europeo aplicado al marcador final del equipo señalado.
- **ANYTIME_GOALSCORER**: Tipo de pick (opcional) que gana cuando el `player_id` o `player_name` del jugador aparece en `goalscorers` con `goals` mayor que 0.
- **result_1x2**: Resultado del partido como cadena `"1"`, `"X"` o `"2"` derivada del marcador final.
- **status**: Estado del partido en la fuente; valores que se consideran auditables son `"Final"`, `"AET"` (después del tiempo extra) y `"Pen"` (después de penales). Cualquier otro estado se omite.
- **Equipo_Trampa**: Equipo de fútbol con win rate menor al 40% en los últimos 10 picks de la tabla `backtesting` con `deporte = 'FUTBOL'`.
- **win_rate**: Porcentaje de aciertos sobre el total de picks auditados, en el rango 0 a 100.
- **ROI**: Retorno sobre la inversión expresado en porcentaje, calculado como `profit / total * 100`.
- **Jerarquia_Futbol**: Orden base de tipos de pick aplicado como desempate por el Selector: `OVER_1_5_1T > OVER_3_5 > BTTS > OVER_2_5 > MONEYLINE > HANDICAP`.

## Requirements

### Requirement 1: Recolección de resultados reales de fútbol

**User Story:** Como operador del sistema de backtesting, quiero recolectar los resultados reales de los partidos de fútbol de los últimos días desde una fuente oficial estructurada, para auditar las predicciones contra datos verificables incluyendo medio tiempo, BTTS y goleadores.

#### Acceptance Criteria

1. WHEN el Scraper_Resultados_Futbol ejecuta la recolección dos veces consecutivas sobre la misma ventana de días, THE Scraper_Resultados_Futbol SHALL producir un conjunto de MatchResult sin entradas duplicadas por `match_id`.
2. WHEN el Scraper_Resultados_Futbol inicia una recolección, THE Scraper_Resultados_Futbol SHALL cubrir una ventana de al menos 15 días previos.
3. WHEN el Scraper_Resultados_Futbol construye un MatchResult, THE Scraper_Resultados_Futbol SHALL asignar `total_goals_ft` igual a `home_score + away_score` y `total_goals_ht` igual a `home_score_ht + away_score_ht`.
4. WHEN el Scraper_Resultados_Futbol construye un MatchResult, THE Scraper_Resultados_Futbol SHALL derivar `result_1x2` igual a `"1"` si `home_score > away_score`, igual a `"2"` si `away_score > home_score` e igual a `"X"` en caso contrario.
5. WHEN el Scraper_Resultados_Futbol construye un MatchResult, THE Scraper_Resultados_Futbol SHALL asignar `both_teams_scored` igual a `True` si `home_score >= 1` y `away_score >= 1`, e igual a `False` en cualquier otro caso.
6. WHEN el Scraper_Resultados_Futbol obtiene marcadores de medio tiempo y la bandera BTTS, THE Scraper_Resultados_Futbol SHALL leerlos desde una API JSON estructurada y no desde HTML scrapeado.
7. WHERE la fuente de datos provee la lista de goleadores, THE Scraper_Resultados_Futbol SHALL registrar para cada gol un objeto con `player_id`, `player_name`, `equipo` y `goals`.
8. IF el `status` de un partido no es `"Final"`, `"AET"` o `"Pen"`, THEN THE Scraper_Resultados_Futbol SHALL omitir ese partido de la recolección.
9. WHEN el Scraper_Resultados_Futbol persiste los resultados, THE Scraper_Resultados_Futbol SHALL escribirlos en `data/backtesting_cache/futbol/` y no en el caché de MLB.
10. IF la fuente principal de datos no responde tras 3 reintentos con backoff para un partido, THEN THE Scraper_Resultados_Futbol SHALL degradar a marcador-solo mediante el respaldo ESPN soccer y marcar el partido como parcial para reintentar half-time, BTTS y goleadores en la siguiente corrida.

### Requirement 2: Auditoría de predicciones de fútbol contra resultados reales

**User Story:** Como analista de apuestas de fútbol, quiero que cada predicción histórica pendiente se audite contra el resultado real, para conocer con exactitud qué picks ganaron o perdieron por tipo de mercado y con qué cuota.

#### Acceptance Criteria

1. WHEN el Auditor_Backtesting_Futbol evalúa un pick de tipo OVER_1_5_1T, THE Auditor_Backtesting_Futbol SHALL marcarlo como `GANADA` si y solo si `total_goals_ht` del MatchResult es mayor o igual a 2, y `PERDIDA` en caso contrario.
2. WHEN el Auditor_Backtesting_Futbol evalúa un pick de tipo OVER_2_5, THE Auditor_Backtesting_Futbol SHALL marcarlo como `GANADA` si y solo si `total_goals_ft` es mayor o igual a 3, y `PERDIDA` en caso contrario.
3. WHEN el Auditor_Backtesting_Futbol evalúa un pick de tipo OVER_3_5, THE Auditor_Backtesting_Futbol SHALL marcarlo como `GANADA` si y solo si `total_goals_ft` es mayor o igual a 4, y `PERDIDA` en caso contrario.
4. WHEN el Auditor_Backtesting_Futbol evalúa un pick de tipo BTTS, THE Auditor_Backtesting_Futbol SHALL marcarlo como `GANADA` si y solo si `both_teams_scored` es `True`, y `PERDIDA` en caso contrario.
5. WHEN el Auditor_Backtesting_Futbol evalúa un pick de tipo MONEYLINE_1X2, THE Auditor_Backtesting_Futbol SHALL marcarlo como `GANADA` si y solo si la selección del pick (`1`, `X` o `2`) coincide con `result_1x2` del MatchResult.
6. WHEN el Auditor_Backtesting_Futbol evalúa un pick de tipo HANDICAP, THE Auditor_Backtesting_Futbol SHALL marcarlo como `GANADA` cuando el marcador del equipo señalado más el handicap del pick supera el marcador del rival, y `PERDIDA` cuando es estrictamente menor.
7. WHERE el pick es de tipo ANYTIME_GOALSCORER, THE Auditor_Backtesting_Futbol SHALL marcarlo como `GANADA` si existe en `goalscorers` un registro cuyo `player_id` o `player_name` normalizado coincide con el del pick y cuyo `goals` es mayor que 0.
8. WHEN el Auditor_Backtesting_Futbol marca el estado de un pick y la cuota real no está disponible, THE Auditor_Backtesting_Futbol SHALL asignar la cuota por defecto correspondiente: 1.85 para OVER_1_5_1T, 1.85 para OVER_2_5, 2.20 para OVER_3_5, 1.95 para BTTS, 2.50 para MONEYLINE_1X2, 1.90 para HANDICAP y 3.50 para ANYTIME_GOALSCORER.
9. WHILE un pick tiene estado `GANADA` o `PERDIDA`, THE Auditor_Backtesting_Futbol SHALL mantener ese estado terminal y transicionar el estado únicamente desde `PENDIENTE`.
10. WHEN el Auditor_Backtesting_Futbol empareja un pick con un partido, THE Auditor_Backtesting_Futbol SHALL usar el Normalizador_Futbol con coincidencia exacta y fuzzy de umbral 85% sobre fecha y nombres de equipos.
11. IF la coincidencia fuzzy de un nombre de equipo obtiene un score entre 70% y 84%, THEN THE Auditor_Backtesting_Futbol SHALL marcar el dato como "Sujeto a revisión" y dejar el pick en estado `PENDIENTE`.
12. IF un pick de OVER_1_5_1T no tiene `total_goals_ht` disponible en el MatchResult, THEN THE Auditor_Backtesting_Futbol SHALL omitir la auditoría de ese pick y conservar su estado `PENDIENTE`.

### Requirement 3: Cálculo de efectividad y clasificación para fútbol

**User Story:** Como analista de apuestas de fútbol, quiero métricas de efectividad por tipo de pick y por equipo de fútbol, para identificar qué mercados y selecciones rinden mejor de cara al Mundial.

#### Acceptance Criteria

1. WHEN el Calculador_Efectividad_Futbol computa métricas por tipo de pick y por equipo, THE Calculador_Efectividad_Futbol SHALL producir un `win_rate` dentro del rango 0 a 100 y un número de aciertos menor o igual al total de picks.
2. WHEN el Calculador_Efectividad_Futbol computa el retorno, THE Calculador_Efectividad_Futbol SHALL calcular el ROI como `profit / total * 100`, acumulando `(cuota - 1)` por cada pick `GANADA` y `-1` por cada pick `PERDIDA`.
3. WHEN el Calculador_Efectividad_Futbol clasifica una métrica con total mayor que 0, THE Calculador_Efectividad_Futbol SHALL asignar exactamente una clasificación entre ÉLITE, CONFIANZA, RIESGO y EVITAR.
4. WHERE el win rate es mayor que 65% y el ROI mayor que +20%, THE Calculador_Efectividad_Futbol SHALL clasificar la métrica como ÉLITE.
5. WHERE el win rate está entre 55% y 65% y el ROI es positivo, THE Calculador_Efectividad_Futbol SHALL clasificar la métrica como CONFIANZA.
6. WHERE el win rate está entre 45% y 55%, THE Calculador_Efectividad_Futbol SHALL clasificar la métrica como RIESGO.
7. WHERE el win rate es menor que 45% o el ROI menor que -15%, THE Calculador_Efectividad_Futbol SHALL clasificar la métrica como EVITAR.
8. WHEN el Calculador_Efectividad_Futbol evalúa un equipo de fútbol con win rate menor al 40% en los últimos 10 picks, THE Calculador_Efectividad_Futbol SHALL marcar ese equipo como Equipo_Trampa.
9. WHEN el Calculador_Efectividad_Futbol consulta la tabla `backtesting`, THE Calculador_Efectividad_Futbol SHALL filtrar exclusivamente registros con `deporte = 'FUTBOL'` para no mezclar métricas con MLB ni otros deportes.
10. WHEN el Calculador_Efectividad_Futbol finaliza el cómputo, THE Calculador_Efectividad_Futbol SHALL persistir las métricas en `data/backtesting_cache/futbol/pick_type_performance.json` y `data/backtesting_cache/futbol/team_performance.json`.

### Requirement 4: Selección de pick de fútbol con aprendizaje

**User Story:** Como apostador de fútbol, quiero que el sistema elija el pick final por partido ajustando la confianza con el histórico real y respetando la jerarquía de fútbol, para apostar a los mercados con mayor probabilidad de acierto sin perder la base heurística.

#### Acceptance Criteria

1. WHEN el Selector_Aprendizaje_Futbol calcula la confianza ajustada de un candidato, THE Selector_Aprendizaje_Futbol SHALL derivar `confianza_ajustada` sin modificar la `confianza_base` ni las salidas de los motores heurísticos `futbol_analyzer_jerarquico` y `motor_fut_pro`.
2. WHEN el Selector_Aprendizaje_Futbol selecciona el pick final de un partido, THE Selector_Aprendizaje_Futbol SHALL excluir todo candidato cuyo equipo esté clasificado como EVITAR o marcado como Equipo_Trampa.
3. WHEN el Selector_Aprendizaje_Futbol evalúa un candidato cuyo tipo de pick está clasificado como EVITAR en `pick_type_performance.json`, THE Selector_Aprendizaje_Futbol SHALL excluir ese candidato del conjunto de selección final.
4. WHEN el Selector_Aprendizaje_Futbol ordena los candidatos válidos, THE Selector_Aprendizaje_Futbol SHALL aplicar la Jerarquia_Futbol (OVER_1_5_1T, luego OVER_3_5, luego BTTS, luego OVER_2_5, luego MONEYLINE, luego HANDICAP) como desempate cuando la `confianza_ajustada` es igual entre dos candidatos.
5. WHEN el Selector_Aprendizaje_Futbol ajusta la confianza de un candidato, THE Selector_Aprendizaje_Futbol SHALL aumentar `confianza_ajustada` para tipos de pick clasificados como ÉLITE o CONFIANZA y disminuirla para tipos clasificados como RIESGO, sin reordenar las salidas heurísticas originales.
6. IF todos los candidatos de un partido quedan excluidos, THEN THE Selector_Aprendizaje_Futbol SHALL devolver un Handicap progresivo de protección de capital (por ejemplo `+1.5` y, si aún no aplica, `+2.5`) basado en el rival.
7. WHEN el Selector_Aprendizaje_Futbol produce el pick final, THE Selector_Aprendizaje_Futbol SHALL asignar un `id` único vinculado a la tabla `backtesting`, persistir el registro con `deporte = 'FUTBOL'` y un stake derivado de la confianza ajustada y la clasificación del equipo.
8. WHEN el Selector_Aprendizaje_Futbol calcula el stake del pick final, THE Selector_Aprendizaje_Futbol SHALL aplicar la matriz de stake dinámico del steering: 4u si `confianza_ajustada` mayor que 75% y equipo ÉLITE, 3u si entre 65% y 75% y equipo CONFIANZA, 2u si entre 55% y 65%, y 1u si menor que 55%.
