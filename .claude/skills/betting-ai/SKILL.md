---
name: betting-ai
description: Conocimiento y flujo de trabajo del proyecto BETTING_AI (app de picks deportivos en Streamlit). Úsala al correr, desplegar, depurar o mejorar los motores de MLB/UFC/NBA/Fútbol, el selector de parlays o el ciclo de aprendizaje de este proyecto.
---

# BETTING_AI — Skill del proyecto

App Streamlit (Python/SQLite) que genera picks de **MLB, UFC, NBA y Fútbol** y arma **parlays** cross-deporte, con IA (Gemini/Groq) opcional y un ciclo de aprendizaje basado en historial de picks.

## Cómo correr (local)
- Entry: **`main_vision_completo.py`**. Comando: `.venv/Scripts/python.exe -m streamlit run main_vision_completo.py --server.port 8501`.
- Config en `.claude/launch.json`. Requiere `GEMINI_API_KEY` y `GROQ_API_KEY` en **`.env`** (el app se detiene si faltan).
- Las API keys se leen con `get_api_key()`: **primero `.env`/os.environ, luego `st.secrets`** (en local no hay secrets.toml).

## Deploy
- Remoto: `github.com/yairchaul/BETTING_AI_GEMINI`, rama **`main`** = desplegable (Streamlit Cloud apunta ahí, entry `main_vision_completo.py`). La rama local ya rastrea `origin/main`: **`git add` → `git commit` → `git push`** funciona directo.
- En Streamlit Cloud, las keys van en el dashboard de Secrets (NO en el repo). `.streamlit/secrets.toml` NO se versiona.

## Arquitectura — motores REALES vs duplicados legacy
La app usa los paquetes; los `*.py` de la RAÍZ suelen ser duplicados legacy (ignóralos al editar). **Edita siempre en los paquetes:**
- MLB money line: `motors/motor_mlb_pro.py` (`analizar_mlb_pro_v20`). El **abridor del día manda** (vía `motors/mlb_pitchers_live.py`, API oficial statsapi.mlb.com con shrinkage); puede voltear el pick contra el récord.
- UFC: `analyzers/ufc_analyzer.py` (`UFCAnalyzer.analizar_combate`): KO→termina antes, striker vs sumisión, penalización por cambio de peso. IA primaria en `visualizers/ufc_tab_renderer.py`.
- NBA: `motors/motor_nba_pro_v17.py` (ML + hándicap + O/U). Props: `motors/nba_props.py`.
- Fútbol: `motors/futbol_analyzer_jerarquico.py` (reglas + fallback FIFA + picks combinados gana+Over).
- Parlays/selector: `visualizers/parlay_builder.py` (filtro por día, parlay "máximo pago", momio americano).
- IA: `utils/analista_total.py` (`AnalistaTotal`, multi-proveedor Gemini/Groq/DeepSeek/Claude; campo `alerta` de contexto).

## Ciclo de aprendizaje
- `motors/pick_memory.py` registra cada pick en `data/pick_history.json` (esquema en `data/history_schema.json`).
- Se resuelven contra resultados reales: `motors/box_score_resolver.py` (`resolver_todo()` para MLB/NBA) y auto-resolver fútbol. **Los picks de HOY quedan PENDIENTES hasta que los juegos terminan** — el win-rate/ROI por deporte y mercado aparece después.
- `pick_memory.factor_confianza(deporte, mercado)` realimenta el selector de parlays (penaliza mercados que fallan).
- Dashboard "🧠 Aprendizaje" en la pestaña Backtesting.

## Gotchas (errores ya resueltos — no reintroducir)
- **Windows/cp1252:** los `print()` con emoji crashean. `main_vision_completo.py` fuerza `sys.stdout/stderr.reconfigure(utf-8)` al arrancar. En tests usa `PYTHONUTF8=1`.
- **Secreto en historial:** la rama local `feat/*` antigua tenía una API key commiteada; `main` ya está limpia. No re-commitear secretos (hay redacción en el flujo de deploy).
- **`.kiro/settings`** la bloquea el IDE Kiro → sparse-checkout la excluye (`.git/info/sparse-checkout`).
- Nombres con ñ/acentos/abreviados: usar `utils/fuzzy_matching.py` (`normalizar`, `generar_alias`, `es_mismo_nombre`).

## Verificar tras cambios
`python -m py_compile <archivos>` y `python -m pytest tests/ -q` (116+ tests). Para ver la UI: `preview_start` con la config `BETTING_AI (Streamlit)`.
