# Protocolo de Auditoría y ROI (MLB)

## 1. Verificación de Resultados
- Al auditar, no solo valides el ganador (Moneyline). 
- DEBES verificar el **Run Line** (Handicap). Si el pick fue +1.5 y el equipo perdió por 1 carrera, el estado es GANADA.
- Para picks de **Home Run (HR)**, consulta el boxscore oficial de MLB API. Un pick de HR solo es GANADA si el `personId` del jugador tiene `homeRuns > 0`.

## 2. Cálculo de ROI y Cuotas
- Registra siempre la cuota real en el momento del análisis.
- Si la cuota no está disponible, usa 1.90 (-110) para Handicaps/OU y 3.50 (+250) para HR como valores conservadores.

## 3. Ajuste de Confianza
- Si un equipo tiene un Win Rate < 40% en los últimos 10 picks de la tabla `backtesting`, debe ser marcado automáticamente como **EQUIPO TRAMPA**.
- Los picks de HR deben ser penalizados en estadios con `factor_hr < 0.90` (como Oracle Park).