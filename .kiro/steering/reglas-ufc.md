# Reglas Específicas: UFC

## 1. Adquisición de Datos
- **Scraper de Stats:** `scrapers/ufc_stats_scraper.py`.
- **Analizador Local:** `analyzers/ufc_analyzer.py`.

## 2. Jerarquía de Combate
- **Prioridad 1:** Diferencia de Edad > 10 años (Favor al joven).
- **Prioridad 2:** Diferencia de SLpM (Golpes por minuto) > 2.0.
- **Prioridad 3:** Ventaja de Alcance (Reach) > 10cm.
- **Prohibición:** NUNCA marcar como "EVITAR" solo por margen estrecho; sugerir "Llega a Decisión: SÍ".