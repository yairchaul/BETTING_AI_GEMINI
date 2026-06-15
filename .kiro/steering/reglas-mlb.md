# Reglas Específicas para MLB

## 1. Cálculo de Strikeouts (K)
Fórmula: (K/9 / 9) * 6 * (tasa_K_rival / 22.0)

- K/9: del pitcher (desde scraper_results.json)
- tasa_K_rival: promedio de K% de los bateadores del equipo rival
- Línea base: K/9 ≥ 11.0 → 6.5 | K/9 ≥ 9.5 → 5.5 | K/9 ≥ 8.0 → 4.5 | else → 3.5

## 2. Cálculo de Home Runs (HR)
- Puntuación = HR_totales * 1.2
- 💎 DIAMANTE: puntuación ≥ 17 | 🥇 ORO: ≥ 14 | ⚪ PROBABLE: ≥ 5

## 3. Evaluación Final
- Prioridad: STRIKEOUTS > HOME_RUN > MONEYLINE
- El pick final es el de mayor confianza
