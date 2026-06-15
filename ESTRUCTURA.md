# 🎯 BETTING_AI — Estructura del Programa

Guía para entender el proyecto y continuar el trabajo (sirve para ti, para DeepSeek o cualquier IA).

> **Stack:** Python + **Streamlit** (interfaz web) + **SQLite/JSON** (datos). **NO es React** — toda la UI se hace con `st.*` y `st.markdown(..., unsafe_allow_html=True)`.
> **Punto de entrada:** `main_vision_completo.py` → se ejecuta con `streamlit run main_vision_completo.py`.
> **Deploy:** GitHub `yairchaul/BETTING_AI_GEMINI`, rama `main` → Streamlit Cloud. Secretos (GEMINI/GROQ/DEEPSEEK keys) van en el dashboard de Streamlit, NO en el repo.

---

## 🗺️ Mapa rápido (dónde está cada cosa)

| Carpeta | Qué contiene | Regla |
|---|---|---|
| **`motors/`** | Motores de análisis (la lógica de picks) | ✅ Versión REAL que usa el app |
| **`analyzers/`** | Analizadores (UFC, fútbol con IA) | ✅ Real |
| **`scrapers/`** | Obtención de datos (ESPN, MLB API, odds) | ✅ Real |
| **`visualizers/`** | Render de cada pestaña (tarjetas, tablas) | ✅ Real |
| **`utils/`** | Utilidades (IA, DB, fuzzy matching, clima) | ✅ Real |
| **`data/`** | Datos/caché/JSON (no es código) | ⚠️ No versionar caché |
| raíz del proyecto | Scripts sueltos + **duplicados legacy** | ⚠️ Editar SOLO los de paquetes, no los de la raíz |

**Regla de oro:** cuando edites un archivo de UI o motor, hazlo en **`visualizers/`, `motors/`, `scrapers/`, `utils/` o `analyzers/`**, nunca en la copia de la raíz (el app importa la de paquete).

---

## 🧩 Flujo principal (`main_vision_completo.py`)

`main()` arma 6 pestañas:

1. **🏀 NBA** → `visualizers/nba_tab_renderer.py` + motor `motors/motor_nba_pro_v17.py` (`analizar_nba_pro_v17`) + props `motors/nba_props.py`.
2. **🥊 UFC** → `visualizers/ufc_tab_renderer.py` + `analyzers/ufc_analyzer.py` (`UFCAnalyzer.analizar_combate`). La **IA (Gemini) corre automática** y muestra aviso de contexto.
3. **⚽ FÚTBOL** → `visualizers/futbol_tab_renderer.py` + `motors/futbol_analyzer_jerarquico.py`.
4. **⚾ MLB** → `visualizers/mlb_tab_renderer.py` + `visualizers/visual_mlb.py` + motor `motors/motor_mlb_pro.py` (`analizar_mlb_pro_v20`).
5. **📊 Backtesting** → backtests reales por deporte + dashboard **🧠 Aprendizaje**.
6. **🎰 PARLAYS** → `visualizers/parlay_builder.py` (combina lo mejor de todos los deportes).

---

## ⚙️ Motores por deporte (la inteligencia)

### ⚾ MLB — `motors/motor_mlb_pro.py` → `analizar_mlb_pro_v20(partido)`
- **Factor #1 = duelo de abridores.** `motors/mlb_pitchers_live.py` baja abridores probables + ERA/WHIP/K9 frescos de la **API oficial de MLB** (statsapi), con *shrinkage* para muestras chicas.
- El pitcheo puede **voltear el pick** contra el récord (capeado ±30); récord pesa ×18.
- Decisión consciente del mercado: al fadear al favorito enruta a MONEYLINE.
- Devuelve: pick, confianza, O/U, hándicap, candidatos a HR, props de ponches/bases.

### 🏀 NBA — `motors/motor_nba_pro_v17.py` → `analizar_nba_pro_v17(partido)`
- Récord + racha + ventaja local → ML, hándicap, O/U y "mejor mercado" con EV.
- Props de jugador: `motors/nba_props.py` (`obtener_props_partido`) — Puntos/Rebotes/Asistencias/Triples/Doble-doble.

### 🥊 UFC — `analyzers/ufc_analyzer.py` → `UFCAnalyzer.analizar_combate(p1, p2)`
- Score por peleador (KO rate, ranking, edad, racha, defensa, volumen).
- **Método** (KO/TKO vs Sumisión vs Decisión) según debilidades del rival.
- **Distancia** ("termina antes" si alto poder de KO).
- Penalización por **cambio de división de peso** (caso Pereira).

### ⚽ FÚTBOL — `motors/futbol_analyzer_jerarquico.py` → `analizar_futbol_jerarquico(local, visit, ...)`
- Reglas jerárquicas (Over 1.5 HT, Over 3.5, BTTS, Over más cercano a 55%, ML, Under elim).
- Sin historial en DB (Mundial) → fallback por ranking FIFA con mercados de alta prob + **picks combinados** (gana + Over).

---

## 🤖 IA (analizador dinámico) — `utils/analista_total.py`
- `AnalistaTotal` orquesta **Gemini / Groq / DeepSeek / Claude** (según `selected_ia_model` en el sidebar; "Heurístico" = sin IA).
- Prompts por deporte que piden contexto: racha/momentum, cambio de peso, lesiones, y permiten **contradecir al heurístico**; devuelve campo `alerta`.
- Clientes en `utils/cerebro_*.py` y `utils/generic_ai_client.py`.

---

## 🧠 Ciclo de aprendizaje (memoria → reflexión → evolución)
- **`motors/pick_memory.py`** — registra cada pick (`data/pick_history.json`, esquema en `data/history_schema.json`). Campos: deporte, mercado, cuota, confianza, estado, resultado_real, parlay_id…
- **`motors/box_score_resolver.py`** — resuelve picks pendientes contra box scores reales (MLB Stats API / ESPN summary).
- **Dashboard 🧠 Aprendizaje** (pestaña Backtesting) — win-rate y ROI global / por deporte / por mercado; botones de auto-resolver.
- **Fase 3**: el selector de parlays pondera cada pick por su rendimiento histórico (`factor_confianza`).

---

## 🎰 Parlays — `visualizers/parlay_builder.py`
- `_recolectar_picks(dia_filtro)` corre todos los motores y arma un pool (con filtro **Hoy/Mañana/Todos**).
- Genera parlays: **SEGURO, VALOR, BOMBA, GIGANTE, MÁXIMO PAGO** (este prefiere combinados gana+Over).
- Momio **americano (+2700)** y ganancia por $100. `_no_iniciado()` descarta juegos terminados/en vivo.

---

## 📡 Scrapers clave (`scrapers/`)
- `espn_mlb.py`, `espn_nba.py`, `espn_ufc.py`, `espn_futbol.py` — carteleras/records/odds de ESPN.
- `mlb_pitchers_live.py` (en `motors/`) — abridores + stats oficiales MLB.
- `odds_scraper.py` / Caliente.mx — momios MLB. `odds_ufc.json` — momios UFC.
- `ufc_stats_scraper.py` — stats de peleadores (usa normalización de nombres).

---

## 🔤 Nombres (ñ/acentos/abreviaturas) — `utils/fuzzy_matching.py`
- `normalizar()` (NFD, ñ→n, minúsculas), `generar_alias()` (completo / inicial+apellido / apellido), `es_mismo_nombre()` (igualdad/alias/fuzzy). Resuelve "Gastón Bolaños", "L. Messi".

---

## 🚀 Deploy (importante)
- El código vive en la rama **`main`** del remoto (limpia, sin secretos).
- Para subir cambios: se **sincroniza el working tree a `main`** (los secretos se redactan automáticamente; los archivos que no compilan se omiten). El `main` local diverge a propósito (tiene historial con un secreto viejo que NO se puede pushear).
- En Streamlit Cloud: repo `yairchaul/BETTING_AI_GEMINI`, rama `main`, archivo `main_vision_completo.py`, secretos en el dashboard.

---

## ▶️ Cómo correrlo localmente
```bash
streamlit run main_vision_completo.py
```
Requiere `.env` con `GEMINI_API_KEY`, `GROQ_API_KEY` (y opcional `DEEPSEEK_API_KEY`, `OPENAI_API_KEY`). Tests: `pytest tests/`.
