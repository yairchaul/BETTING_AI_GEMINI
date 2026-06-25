# -*- coding: utf-8 -*-
"""
BETTING_AI NEON - V24 (Unificado y Funcional)
NBA, MLB, UFC, Futbol con análisis heurístico y caché de datos.
"""

import streamlit as st
from datetime import datetime
import pandas as pd
import os
import time
import threading
import logging
import sqlite3
import json
from dotenv import load_dotenv

# --- Add project root to sys.path to fix ModuleNotFoundError ---
import sys
# Consola UTF-8: evita que los print() con emoji (⚡❌🔥…) crasheen en Windows (cp1252).
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
# --- End of fix ---

# --- Ensure package directories have __init__.py to prevent ModuleNotFoundError ---
for folder in ["scrapers", "utils", "motors", "visualizers", "analyzers"]:
    dir_path = os.path.join(PROJECT_ROOT, folder)
    init_path = os.path.join(dir_path, "__init__.py")
    if os.path.isdir(dir_path) and not os.path.exists(init_path):
        with open(init_path, "w", encoding="utf-8") as f:
            f.write("# -*- coding: utf-8 -*-\n")
# --- End of fix ---

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cargar variables de entorno de forma global
load_dotenv()

from espn_nba import ESPN_NBA
from espn_mlb import ESPN_MLB_Mejorado as ESPN_MLB
from espn_ufc import ESPN_UFC
from espn_futbol import ESPN_FUTBOL
from bet_tracker import BetTracker
from visual_nba_mejorado import VisualNBAMejorado
try:
    from visualizers.visual_ufc_mejorado_v2 import VisualUFCMejoradoV2
except ImportError:
    VisualUFCMejoradoV2 = None
from visual_ufc_final import VisualUFCFinal
from visual_futbol_triple import VisualFutbolTriple
from radar_triples_nba import radar_triples
from visualizers.visual_mlb import VisualMLB
try:
    from visualizers.parlay_builder import render_parlay_tab
except Exception:
    render_parlay_tab = None
from database_manager import db
from render_unificado import render_analisis_card
from motors import analizar_nba_pro_v17, analizar_mlb_pro_v20
from motors.motor_fut_pro import analizar_futbol_pro_v20
from motors.futbol_analyzer_jerarquico import analizar_futbol_jerarquico
from scrapers.ufc_stats_scraper import UFCStatsScraper
from motors.predictor_hr_pro import PredictorHRPro
try:
    from motors.pick_memory import pick_memory
except Exception:
    pick_memory = None
from analyzers.ufc_analyzer import UFCAnalyzer
from utils.analista_total import AnalistaTotal
try:
    from scrapers.odds_scraper import get_mlb_odds_caliente
except Exception:
    def get_mlb_odds_caliente():  # fallback si el scraper no existe
        return {}

# Motores MLB integrados (HR + K + O/U + Clima + Decisión Inteligente)
try:
    from motors.predictor_hr import predictor_hr as _hr_singleton  # noqa: F401
    from motors.predictor_hr import PredictorHR
except ImportError:
    PredictorHR = None
try:
    from motors.predictor_ponches import PredictorPonches
except ImportError:
    PredictorPonches = None
try:
    from motors.motor_over_under import MotorOverUnder
except ImportError:
    MotorOverUnder = None
try:
    from utils.clima_mlb import ClimaMLB
except ImportError:
    try:
        from clima_mlb import ClimaMLB
    except ImportError:
        ClimaMLB = None
try:
    from motors.motor_decision_inteligente import MotorDecisionInteligente
except ImportError:
    MotorDecisionInteligente = None

try:
    # Importar desde utils para mantener la modularidad y corregir el error de sintaxis.
    from utils.cerebro_gemini_pro import CerebroGeminiPro
except ImportError:
    CerebroGeminiPro = None

try:
    from groq_ufc_engine import GroqUFCEngine
except ImportError:
    GroqUFCEngine = None

try:
    from utils.cerebro_claude import CerebroClaude
except ImportError:
    CerebroClaude = None

def get_api_key(name):
    # Prioridad 1: variables de entorno (.env o sistema) — funciona en local.
    val = os.getenv(name, "")
    if val:
        return val.strip().strip('"').strip("'")
    # Prioridad 2: Streamlit Secrets (Streamlit Cloud). Acceder a st.secrets sin
    # secrets.toml lanza excepción; la aislamos para NO perder la key del .env.
    try:
        if hasattr(st, "secrets") and name in st.secrets:
            return str(st.secrets[name]).strip()
    except Exception:
        pass
    return ""

def cargar_json_safe(filepath):
    """Carga un archivo JSON de forma segura, retornando None si falla."""
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None
    return None

def _initialize_ai_client(st_session_key: str, client_class, api_key_name: str):
    """Inicializa un cliente de IA y lo guarda en st.session_state."""
    if client_class:
        api_key = get_api_key(api_key_name)
        st.session_state[st_session_key] = client_class(api_key) if api_key else None
    else:
        st.session_state[st_session_key] = None

def _mapa_mlb_oficial():
    """Mapa equipo→{pitcher, game_pk} desde la MLB Stats API oficial (hoy).

    El game_pk REAL de MLB es necesario para obtener lineups y candidatos HR
    (el id de ESPN no sirve para esa API).
    """
    import requests
    mapa = {}
    try:
        fecha = datetime.now().strftime("%Y-%m-%d")
        url = (f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={fecha}"
               "&hydrate=probablePitcher,team")
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=12)
        if r.status_code == 200:
            for d in r.json().get("dates", []):
                for g in d.get("games", []):
                    game_pk = g.get("gamePk")
                    for lado in ("home", "away"):
                        t = g["teams"][lado]
                        nombre_eq = t.get("team", {}).get("name", "")
                        pitcher = t.get("probablePitcher", {}).get("fullName", "")
                        if nombre_eq:
                            mapa[nombre_eq.lower()] = {"pitcher": pitcher, "game_pk": game_pk}
    except Exception as e:
        logger.warning(f"No se pudo obtener datos oficiales MLB: {e}")
    return mapa


def _enriquecer_partidos_mlb_con_pitchers(partidos: list) -> list:
    """Rellena pitchers 'TBD' y el game_pk real de MLB (para lineups/HR)."""
    if not partidos:
        return []

    mapa = _mapa_mlb_oficial()
    if not mapa:
        return partidos

    def _buscar(nombre_equipo):
        ne = (nombre_equipo or "").lower()
        if ne in mapa:
            return mapa[ne]
        for k, v in mapa.items():
            if k in ne or ne in k:
                return v
        return None

    for p in partidos:
        p.setdefault("pitchers", {"local": {}, "visitante": {}})
        info_local = _buscar(p.get("local", ""))
        # game_pk REAL de MLB (sobre-escribe el id de ESPN para lineups/HR)
        if info_local and info_local.get("game_pk"):
            p["game_pk"] = info_local["game_pk"]
        for lado, equipo_key in (("local", "local"), ("visitante", "visitante")):
            actual = p.setdefault("pitchers", {}).setdefault(lado, {})
            if not isinstance(actual, dict):
                actual = {}
                p["pitchers"][lado] = actual
            if actual.get("nombre", "TBD") in ("TBD", "", "N/A", None):
                info = _buscar(p.get(equipo_key, ""))
                if info and info.get("pitcher"):
                    actual["nombre"] = info["pitcher"]

    return partidos

def _odds_espn_mlb() -> dict:
    """Fallback de cuotas MLB desde ESPN (moneyline o parseo de 'details').

    Devuelve {nombre_equipo: momio}. Cuando ESPN solo da el favorito en
    'details' (ej. 'NYY -149'), asigna ese momio al favorito y estima el rival.
    """
    import requests
    out = {}
    try:
        url = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard"
        data = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=12).json()
        for e in data.get("events", []):
            c = (e.get("competitions") or [{}])[0]
            comps = {x.get("homeAway"): x for x in c.get("competitors", [])}
            home, away = comps.get("home", {}), comps.get("away", {})
            home_name = home.get("team", {}).get("displayName", "")
            away_name = away.get("team", {}).get("displayName", "")
            home_ab = home.get("team", {}).get("abbreviation", "")
            away_ab = away.get("team", {}).get("abbreviation", "")
            o = (c.get("odds") or [{}])[0]
            home_ml = (o.get("homeTeamOdds", {}) or {}).get("moneyLine")
            away_ml = (o.get("awayTeamOdds", {}) or {}).get("moneyLine")
            det = o.get("details", "") or ""
            # Parseo de details si no hay moneyline directo
            if home_ml is None and away_ml is None and det:
                m = re.search(r"([A-Z]{2,4})\s*([+-]\d+)", det)
                if m:
                    ab_fav, ml_fav = m.group(1), int(m.group(2))
                    ml_dog = abs(ml_fav) + 20 if ml_fav < 0 else -(ml_fav + 20)
                    if ab_fav == home_ab:
                        home_ml, away_ml = ml_fav, ml_dog
                    elif ab_fav == away_ab:
                        away_ml, home_ml = ml_fav, ml_dog
            if home_ml is not None and home_name:
                out[home_name] = f"{home_ml:+d}" if isinstance(home_ml, int) else str(home_ml)
            if away_ml is not None and away_name:
                out[away_name] = f"{away_ml:+d}" if isinstance(away_ml, int) else str(away_ml)
    except Exception as e:
        logger.warning(f"Odds ESPN MLB no disponibles: {e}")
    return out


def _enriquecer_partidos_mlb_con_odds(partidos: list) -> list:
    """Fusiona cuotas de Caliente.mx (primario) + ESPN (fallback) en los partidos."""
    if not partidos:
        return []

    odds_map = {}
    # 1) the-odds-api: momios REALES de mercado (funciona en la nube)
    try:
        from scrapers.odds_api import obtener_odds_mlb
        odds_map.update(obtener_odds_mlb())
    except Exception as e:
        logger.warning(f"odds_api MLB: {e}")
    # 2) Caliente.mx (respaldo)
    try:
        for k, v in (get_mlb_odds_caliente() or {}).items():
            odds_map.setdefault(k, v)
    except Exception as e:
        logger.warning(f"Caliente odds falló: {e}")
    # 3) ESPN (respaldo)
    try:
        for k, v in _odds_espn_mlb().items():
            odds_map.setdefault(k, v)
    except Exception:
        pass

    if not odds_map:
        logger.warning("No se pudieron obtener cuotas MLB (Caliente ni ESPN).")
        return partidos

    def _buscar_odd(nombre):
        if not nombre:
            return "N/A"
        if nombre in odds_map:
            return odds_map[nombre]
        nl = nombre.lower()
        for k, v in odds_map.items():
            if k.lower() in nl or nl in k.lower():
                return v
        return "N/A"

    for p in partidos:
        p.setdefault("odds", {"moneyline": {}})
        p["odds"].setdefault("moneyline", {})
        p["odds"]["moneyline"]["visitante"] = _buscar_odd(p.get("visitante"))
        p["odds"]["moneyline"]["local"] = _buscar_odd(p.get("local"))

    return partidos

def _analisis_basico_record(partido: dict) -> dict:
    """
    Encapsula la lógica del motor de MLB antiguo, basado puramente en el récord de la temporada.
    Devuelve un pick simple y su confianza.
    """
    home_record = partido.get('local_record', '0-0')
    away_record = partido.get('visitante_record', '0-0')

    def get_win_pct(record):
        try:
            wins, losses = map(int, record.split('-'))
            total = wins + losses
            return wins / total if total > 0 else 0.5
        except:
            return 0.5

    home_wr = get_win_pct(home_record)
    away_wr = get_win_pct(away_record)
    
    # Probabilidad de victoria del local
    win_prob_home = home_wr / (home_wr + away_wr) if (home_wr + away_wr) > 0 else 0.5
    
    pick = partido.get('local') if win_prob_home > 0.5 else partido.get('visitante')
    confianza = int(max(win_prob_home, 1 - win_prob_home) * 100)
    
    return {'pick': pick, 'confianza': confianza}

def aplicar_estilos():
    st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); }
    section[data-testid="stSidebar"] { background: linear-gradient(180deg, #020617 0%, #0f172a 100%); border-right: 1px solid #334155; }
    .stButton > button { border-radius: 12px !important; background: linear-gradient(90deg, #3b82f6 0%, #9333ea 100%) !important; color: white !important; font-weight: bold !important; border: none !important; transition: all 0.3s !important; }
    .stButton > button:hover { transform: scale(1.02) !important; box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4) !important; }
    </style>
    """, unsafe_allow_html=True)

def cargar_base_ufc():
    try:
        with open("base_ufc_unificada.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except: return {}

def cargar_cuotas_ufc():
    """Momios UFC REALES: the-odds-api (mercado) + archivo legacy. Clave = nombre normalizado."""
    odds = {}
    # 1) Momios reales de mercado (the-odds-api con ODDS_API_KEY)
    try:
        from scrapers.odds_api import obtener_odds_ufc
        odds.update(obtener_odds_ufc())
    except Exception as _oe:
        logger.warning(f"odds_api UFC no disponible: {_oe}")
    # 2) Archivo legacy de Caliente (si existe) — complementa por nombre normalizado
    try:
        from utils.fuzzy_matching import normalizar
        with open("odds_caliente_ufc.json", "r", encoding="utf-8") as f:
            for p in json.load(f):
                odds[normalizar(p["p1"])] = p["m1"]
                odds[normalizar(p["p2"])] = p["m2"]
    except Exception:
        pass
    return odds

def cargar_mlb_desde_json():
    try:
        with open("resultados_finales_corregidos.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except: return None

def inicializar_bd_ufc():
    os.makedirs("data", exist_ok=True)
    try:
        conn = sqlite3.connect("data/betting_stats.db")
        cursor = conn.cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS peleadores_ufc_cache (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT UNIQUE, datos_json TEXT, ultima_actualizacion TEXT)""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS eventos_ufc (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, fecha TEXT, cartelera TEXT, ultima_actualizacion TEXT)""")
        conn.commit(); conn.close()
    except: pass

def _log_pick_ia(deporte, local, visitante, resultado_ia, fecha_evento=None):
    """Registra el pick de la IA en pick_memory con fuente='IA' para que el
    auto-resolver lo backtestee junto al heurístico. No-op si no hay pick válido.
    El historial de IA arranca desde hoy (antes nunca se guardaba)."""
    if pick_memory is None or not resultado_ia:
        return
    pick = resultado_ia.get('pick', '')
    if not pick or str(pick) in ('N/A', 'None', ''):
        return
    try:
        pick_memory.log_pick({
            "deporte": deporte,
            "evento": f"{local} vs {visitante}",
            "local": local, "visitante": visitante,
            "mercado": resultado_ia.get('mercado', '') or 'IA',
            "pick": pick, "seleccion": pick,
            "confianza": resultado_ia.get('confianza', 0) or 0,
            "cuota": resultado_ia.get('cuota', 1.90) or 1.90,
            "fuente": "IA",
            "fecha_evento": fecha_evento or datetime.now().strftime("%Y-%m-%d"),
        })
    except Exception as _e:
        logger.debug(f"log pick IA ({deporte}): {_e}")


def _auto_resolver_futbol():
    """Resuelve picks de fútbol pendientes cruzándolos con resultados reales de ESPN."""
    if pick_memory is None:
        return 0
    from espn_futbol import ESPN_FUTBOL
    from motors.futbol_backtest_real import _grade_pick, LIGAS_DEFAULT

    scraper = ESPN_FUTBOL()
    # Mapa de resultados: "home|away" normalizado → (gl, gv, local, visitante)
    resultados = {}
    for liga in LIGAS_DEFAULT:
        try:
            for p in scraper.gestor.obtener_partidos(liga, dias_atras=5):
                if p.get("completado") and p.get("goles_local") is not None:
                    h = (p.get("home") or p.get("local", "")).lower().strip()
                    a = (p.get("away") or p.get("visitante", "")).lower().strip()
                    resultados[f"{h}|{a}"] = (int(p["goles_local"]), int(p["goles_visitante"]),
                                              p.get("home", ""), p.get("away", ""))
        except Exception:
            continue

    n = 0
    for pk in pick_memory.pendientes():
        if (pk.get("deporte") or "").upper() != "SOCCER":
            continue
        evento = pk.get("evento", "")
        if " vs " not in evento:
            continue
        local, visitante = [x.strip() for x in evento.split(" vs ", 1)]
        clave = f"{local.lower()}|{visitante.lower()}"
        if clave not in resultados:
            continue
        gl, gv, loc_real, vis_real = resultados[clave]
        _, acierto = _grade_pick(pk.get("pick", ""), gl, gv, loc_real, vis_real)
        if acierto is None:
            continue
        pick_memory.resolver(pk["id"], "ganado" if acierto else "perdido", f"{gl}-{gv}")
        n += 1
    return n

def _no_iniciado(p):
    """True solo si el evento AÚN NO empieza (descarta finalizados / en vivo / pasados)."""
    if not isinstance(p, dict):
        return True
    # Marcadores explícitos de estado
    if p.get("completado") or p.get("en_vivo"):
        return False
    estado = str(p.get("status", "") or p.get("state", "")).lower()
    if any(x in estado for x in ("final", "ft", "post", "progress", "in progress",
                                 "en vivo", "live", "terminado", "finalizado", "completed")):
        return False
    # Si hay marcador con goles/puntos reales, ya empezó
    if p.get("marcador"):
        return False
    # Comparar fecha+hora de inicio contra ahora (si viene con hora)
    for campo in ("fecha_partido", "fecha", "date"):
        v = p.get(campo)
        if not v:
            continue
        txt = str(v).replace("T", " ").strip()
        # Handle ISO format with Z
        if 'Z' in txt.upper():
            try:
                from datetime import timezone
                dt = datetime.fromisoformat(txt.replace('Z', '+00:00'))
                return dt > datetime.now(timezone.utc)
            except Exception:
                pass # Fallback a otros formatos
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
            try:
                dt = datetime.strptime(txt[:len(fmt)], fmt)
                return dt > datetime.now()
            except ValueError:
                continue
        break
    return True  # sin hora parseable → asumir que sigue disponible

def main():
    st.set_page_config(page_title="BETTING_AI", page_icon="🎯", layout="wide")
    aplicar_estilos()
    
    if "init" not in st.session_state:
        inicializar_bd_ufc()
        st.session_state.tracker = BetTracker()
        _initialize_ai_client("gemini", CerebroGeminiPro, "GEMINI_API_KEY")
        _initialize_ai_client("groq", GroqUFCEngine, "GROQ_API_KEY")
        _initialize_ai_client("claude", CerebroClaude, "ANTHROPIC_API_KEY")

        st.session_state.ufc_enriched_cache = {}
        st.session_state.nba_partidos = []
        st.session_state.ufc_combates = []
        st.session_state.futbol_partidos = {}
        st.session_state.mlb_partidos = []
        st.session_state.analisis_nba = {}
        st.session_state.analisis_ufc = {}
        st.session_state.analisis_mlb = {}
        st.session_state.analisis_futbol = {}
        st.session_state.selected_ia_model = "Heurístico"

        st.session_state.predictor_hr = PredictorHRPro(mlb_partidos_hoy=st.session_state.mlb_partidos)

        # ── MOTORES MLB INTEGRADOS (lazy: instanciar solo si están disponibles) ──
        # hr_analyzer es alias de predictor_hr para compatibilidad con mlb_tab_renderer
        st.session_state.hr_analyzer = st.session_state.predictor_hr
        st.session_state.predictor_k = PredictorPonches() if PredictorPonches else None
        st.session_state.motor_ou = MotorOverUnder() if MotorOverUnder else None
        st.session_state.clima_mlb = ClimaMLB() if ClimaMLB else None
        st.session_state.motor_decision = MotorDecisionInteligente() if MotorDecisionInteligente else None
        st.session_state.conservative_mode = False
        st.session_state.token_log = []
        st.session_state.token_alert_threshold = 8000

        # AUTO-RESOLVER (sin nada manual): al iniciar la sesión, resuelve los picks
        # pendientes cuyos juegos ya terminaron, contra resultados reales. Así el
        # ciclo de aprendizaje se llena solo. No bloquea la app si algo falla.
        try:
            from motors.box_score_resolver import resolver_todo
            resolver_todo()
            _auto_resolver_futbol()
            # Resolver parlays a partir del resultado de sus legs (cerebro de parlays)
            from motors.parlay_brain import resolver_parlays_pendientes
            resolver_parlays_pendientes()
        except Exception as _are:
            logger.warning(f"Auto-resolver inicial: {_are}")

        # HR backtest DINÁMICO: si el reporte está viejo (>18h), recalcula qué
        # candidatos pegaron HR (ligero, 3 días) para nutrir el motor de HR.
        try:
            _hp = os.path.join("data", "hr_backtest_reporte.json")
            _stale = True
            if os.path.exists(_hp):
                _ts = (cargar_json_safe(_hp) or {}).get("timestamp", "")
                if _ts:
                    _stale = (datetime.now() - datetime.fromisoformat(_ts)).total_seconds() > 64800
            if _stale:
                from motors.hr_backtester import ejecutar_hr_backtest
                ejecutar_hr_backtest(dias=3)
        except Exception as _hre:
            logger.warning(f"Auto HR backtest: {_hre}")

        st.session_state.init = True

    # ── Objetos SIN estado: recrear en CADA ejecución para que los cambios de
    #    código siempre se reflejen (evita instancias obsoletas en session_state) ──
    st.session_state.scrapers = {"nba": ESPN_NBA(), "mlb": ESPN_MLB(), "ufc": ESPN_UFC(), "futbol": ESPN_FUTBOL()}
    st.session_state.visual_nba = VisualNBAMejorado()
    st.session_state.visual_ufc = VisualUFCMejoradoV2() if VisualUFCMejoradoV2 else VisualUFCFinal()
    st.session_state.visual_futbol = VisualFutbolTriple()
    st.session_state.visual_mlb = VisualMLB()
    st.session_state.motores = {"nba": analizar_nba_pro_v17, "mlb": analizar_mlb_pro_v20, "futbol": analizar_futbol_pro_v20}
    st.session_state.ufc_scraper = UFCStatsScraper()
    st.session_state.ufc_analyzer = UFCAnalyzer()

    st.markdown("<div id='tope-pagina'></div><div style='text-align:center;padding:10px'><h1 style='background:linear-gradient(90deg,#3b82f6,#9333ea);-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-size:2.5rem;margin:0'>🎯 BETTING_AI</h1><p style='color:#94a3b8;margin:5px 0 0 0'>🏀 NBA &bull; ⚾ MLB &bull; 🥊 UFC &bull; ⚽ Futbol</p></div>", unsafe_allow_html=True)

    # Botón flotante para volver arriba (ancla nativa, funciona dentro de Streamlit)
    st.markdown("""
    <style>
    #btn-arriba {position:fixed; bottom:30px; right:30px; z-index:9999;
                 display:flex; align-items:center; justify-content:center;
                 background:linear-gradient(135deg,#3b82f6,#9333ea); color:white !important;
                 width:54px; height:54px; border-radius:50%; text-decoration:none;
                 font-size:24px; border:2px solid rgba(255,255,255,0.25);
                 box-shadow:0 6px 20px rgba(59,130,246,0.45);
                 transition:transform .18s ease, box-shadow .18s ease, opacity .18s ease;
                 opacity:.85;}
    #btn-arriba:hover {transform:translateY(-3px) scale(1.12); opacity:1;
                       box-shadow:0 10px 28px rgba(147,51,234,0.6);}
    </style>
    <a id="btn-arriba" href="#tope-pagina" title="Volver arriba">⬆️</a>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.header("⚙️ CONTROLES")
        st.session_state.tracker.render_sidebar_tracker()
        st.markdown("---")
        with st.expander("🔧 Estado de IA", expanded=False):
            _gem_ok = bool(st.session_state.get("gemini") and getattr(st.session_state.gemini, "client", None))
            _grq_ok = bool(st.session_state.get("groq") and getattr(st.session_state.groq, "client", None))
            _cld_ok = bool(st.session_state.get("claude") and getattr(st.session_state.claude, "client", None))
            st.success("✅ Gemini conectado (gemini-2.5-flash)" if _gem_ok else "❌ Gemini no disponible")
            if _grq_ok:
                st.success("✅ Groq conectado")
            else:
                st.warning("⚠️ Groq no disponible — actualiza GROQ_API_KEY")
            if _cld_ok:
                st.success("✅ Claude conectado")
            else:
                st.info("ℹ️ Claude no configurado (ANTHROPIC_API_KEY)")

        # Selector de motor de análisis (Heurístico + IAs conectadas)
        opciones_ia = ["Heurístico"]
        if st.session_state.gemini: opciones_ia.append("Gemini")
        if st.session_state.groq:   opciones_ia.append("Groq")
        if st.session_state.claude: opciones_ia.append("Claude")
        if len(opciones_ia) > 2:    opciones_ia.append("Votación (Todas las IAs)")
        st.session_state.selected_ia_model = st.selectbox(
            "🧠 Motor de análisis",
            opciones_ia,
            index=opciones_ia.index(st.session_state.get("selected_ia_model", "Heurístico"))
                  if st.session_state.get("selected_ia_model", "Heurístico") in opciones_ia else 0,
            help="Heurístico = motores propios. Selecciona una IA para validar/mejorar el pick.",
        )
        st.markdown("---")
        
        if st.button("🏀 CARGAR NBA", use_container_width=True):
            with st.spinner("Cargando NBA..."):
                st.session_state.nba_partidos = st.session_state.scrapers["nba"].get_games()
                st.session_state.analisis_nba = {}  # limpiar cache viejo (evita datos cruzados)
                st.success(f"✅ {len(st.session_state.nba_partidos)} partidos" if st.session_state.nba_partidos else "⚠️ No hay partidos")

        if st.button("⚾ CARGAR MLB", use_container_width=True):
            with st.spinner("Cargando MLB (API Oficial + Cuotas)..."):
                # 1. Obtener partidos y pitchers de la API oficial de MLB
                partidos_base = st.session_state.scrapers["mlb"].get_games() # Usa el scraper mejorado

                # 2. Enriquecer con pitchers de la API oficial (más fiable)
                partidos_con_pitchers = _enriquecer_partidos_mlb_con_pitchers(partidos_base)

                # 3. Enriquecer con cuotas de Caliente.mx
                partidos_finales = _enriquecer_partidos_mlb_con_odds(partidos_con_pitchers)

                # 4. Ordenar por hora de inicio en Ciudad de México (UTC → CDMX)
                def _key_hora_cdmx(partido):
                    try:
                        from datetime import datetime, timezone
                        from zoneinfo import ZoneInfo
                        h = partido.get("hora", "")
                        if not h:
                            return "99:99"
                        today = datetime.now(timezone.utc).date()
                        dt_u = datetime.strptime(f"{today} {h}", "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
                        return dt_u.astimezone(ZoneInfo("America/Mexico_City")).strftime("%H:%M")
                    except Exception:
                        return "99:99"
                partidos_finales = sorted(partidos_finales, key=_key_hora_cdmx)
                st.session_state.mlb_partidos = partidos_finales
                st.session_state.analisis_mlb = {}  # Limpiar caché de análisis
                st.success(f"✅ {len(st.session_state.mlb_partidos)} partidos cargados y enriquecidos.")

        if st.button("🥊 CARGAR UFC", use_container_width=True):
            with st.spinner("🔄 Buscando cartelera UFC..."):
                all_combats = st.session_state.scrapers["ufc"].get_events()
                upcoming_combats = [c for c in all_combats if _no_iniciado(c)]
                if not upcoming_combats and all_combats:
                    st.session_state.ufc_combates = []
                    st.warning("La cartelera más reciente ya finalizó. La próxima se mostrará cuando esté disponible.")
                else:
                    st.session_state.ufc_combates = upcoming_combats
                st.session_state.analisis_ufc = {}        # limpiar análisis viejo
                st.session_state.ufc_enriched_cache = {}  # recargar stats frescas de cada pelea
                st.success(f"✅ {len(st.session_state.ufc_combates)} combates próximos" if st.session_state.ufc_combates else "ℹ️ No hay eventos próximos")
                st.rerun()  # refresca la cartelera automáticamente al actualizar

        st.markdown("---"); st.subheader("⚽ FUTBOL")
        ligas = st.session_state.scrapers["futbol"].get_available_leagues()

        # Alias en español → término ESPN (que "Mundial" encuentre "FIFA World Cup")
        _alias_es = {
            "mundial": "world cup", "copa del mundo": "world cup",
            "champions": "uefa champions", "libertadores": "libertadores",
            "sudamericana": "sudamericana", "eliminatorias": "world cup qualifying",
            "premier": "premier league",
        }

        # Buscador de ligas (filtra toda la lista, con alias en español)
        filtro_liga = st.text_input("🔎 Buscar liga / torneo", "", key="buscar_liga",
                                    placeholder="Ej: Mundial, Premier, Liga MX...").strip().lower()
        filtro_efectivo = _alias_es.get(filtro_liga, filtro_liga)
        ligas_filtradas = [lg for lg in ligas if filtro_efectivo in lg.lower()] if filtro_liga else ligas

        if filtro_liga:
            st.caption(f"{len(ligas_filtradas)} coincidencia(s)")
        else:
            st.caption(f"{len(ligas)} ligas y torneos disponibles")

        def _cargar_liga(lg):
            """Carga partidos + puebla historial (últimos 5) para análisis con datos reales.

            En la pestaña se muestran SOLO los partidos de hoy y próximos (con
            predicción). Los ya jugados nutren el historial y viven en el Backtesting.
            """
            partidos_lg = st.session_state.scrapers["futbol"].get_games(lg)
            # Historial con TODOS (los pasados alimentan los promedios del analizador)
            if partidos_lg:
                try:
                    st.session_state.scrapers["futbol"].poblar_historial(partidos_lg)
                except Exception as _he:
                    logger.warning(f"Poblar historial {lg}: {_he}")
            # Mostrar de HOY hasta +3 días (hoy → lunes), no terminados.
            # (Lo ya jugado va al historial/backtesting, no a la pestaña.)
            from datetime import timedelta as _td
            _hoy = datetime.now().strftime("%Y-%m-%d")
            _lim = (datetime.now() + _td(days=3)).strftime("%Y-%m-%d")
            futuros = [p for p in (partidos_lg or [])
                       if not p.get("completado")
                       and _hoy <= str(p.get("fecha_partido") or p.get("fecha") or "9999")[:10] <= _lim]
            # Odds REALES de fútbol (the-odds-api) donde falten las de ESPN
            try:
                from scrapers.odds_api import obtener_odds_futbol
                from utils.fuzzy_matching import normalizar
                team_odds = {}
                for o in obtener_odds_futbol():
                    if o.get("home_ml"):
                        team_odds[normalizar(o["home"])] = (o["home_ml"], o.get("draw_ml"))
                    if o.get("away_ml"):
                        team_odds[normalizar(o["away"])] = (o["away_ml"], o.get("draw_ml"))
                for p in futuros:
                    ml = p.setdefault("odds", {}).setdefault("moneyline", {})
                    if not ml.get("home") or ml.get("home") in ("N/A", "", None):
                        lo = team_odds.get(normalizar(p.get("home") or p.get("local", "")))
                        vo = team_odds.get(normalizar(p.get("visitante") or p.get("away", "")))
                        if lo:
                            ml["home"], ml["draw"] = lo[0], lo[1]
                        if vo:
                            ml["away"] = vo[0]
            except Exception as _foe:
                logger.warning(f"odds_api fútbol: {_foe}")
            st.session_state.futbol_partidos[lg] = futuros
            return futuros

        # ── 🔥 Ligas con juegos HOY (top 5, incluido el Mundial) ─────────────
        if "ligas_hoy" not in st.session_state:
            with st.spinner("Buscando ligas con juegos hoy..."):
                try:
                    st.session_state.ligas_hoy = st.session_state.scrapers["futbol"].ligas_con_juegos_hoy(5)
                except Exception as _lh:
                    logger.warning(f"ligas_con_juegos_hoy: {_lh}")
                    st.session_state.ligas_hoy = []

        ch1, ch2 = st.columns([3, 1])
        ch1.markdown("**🔥 Ligas con juegos HOY**")
        if ch2.button("🔄", key="refresh_hoy", help="Actualizar ligas de hoy"):
            st.session_state.pop("ligas_hoy", None)
            st.rerun()

        if st.session_state.get("ligas_hoy"):
            for liga_h, n_h in st.session_state.ligas_hoy:
                if st.button(f"⚽ {liga_h} · 🔴 {n_h} hoy", key=f"hoy_{liga_h}", use_container_width=True):
                    with st.spinner(f"Cargando {liga_h} + últimos 5 de cada equipo..."):
                        partidos_lg = _cargar_liga(liga_h)
                        st.session_state.analisis_futbol = {}
                        st.success(f"✅ {len(partidos_lg)} partidos · historial actualizado")
        else:
            st.caption("Sin juegos hoy en las ligas principales.")
        st.markdown("---")

        # Botón para cargar TODAS las filtradas de golpe (útil para 'Mundial' o 'Qualifying')
        if filtro_liga and 1 < len(ligas_filtradas) <= 8:
            if st.button(f"⚡ Cargar las {len(ligas_filtradas)} coincidencias", use_container_width=True):
                for lg in ligas_filtradas:
                    with st.spinner(f"Cargando {lg} + historial..."):
                        _cargar_liga(lg)
                # Limpiar análisis viejos para re-analizar con el historial nuevo
                st.session_state.analisis_futbol = {}

        # ── Listado de ligas: agrupado en categorías expandibles ────────────
        def _categoria_liga(nombre):
            n = nombre.lower()
            if any(k in n for k in ("world cup", "euro", "copa américa", "copa america",
                                    "nations", "friendly", "gold cup", "qualifying")):
                return "🌎 Selecciones / Torneos"
            if any(k in n for k in ("champions", "europa", "libertadores", "sudamericana",
                                    "club world", "fa cup", "copa del rey", "coppa", "pokal", "coupe")):
                return "🏆 Copas de clubes"
            if any(k in n for k in ("premier league", "la liga", "serie a", "serie b", "bundesliga",
                                    "ligue", "eredivisie", "primeira", "championship", "league one",
                                    "scottish", "belgian", "turkish", "greek", "austrian", "swiss",
                                    "danish", "norwegian", "swedish", "russian", "ukrainian")):
                return "🇪🇺 Ligas de Europa"
            if any(k in n for k in ("liga mx", "mls", "brazilian", "argentine", "colombian",
                                    "chilean", "uruguayan", "ecuadorian", "paraguayan", "peruvian")):
                return "🌎 Ligas de América"
            if any(k in n for k in ("saudi", "j1", "k league", "chinese", "a-league", "qatar", "uae")):
                return "🌏 Ligas de Asia / Oceanía"
            return "📋 Otras"

        _orden_cat = ["🌎 Selecciones / Torneos", "🏆 Copas de clubes", "🇪🇺 Ligas de Europa",
                      "🌎 Ligas de América", "🌏 Ligas de Asia / Oceanía", "📋 Otras"]

        def _boton_liga(liga):
            if st.button(f"⚽ {liga}", key=f"btn_{liga}", use_container_width=True):
                with st.spinner(f"Cargando {liga} + últimos 5 de cada equipo..."):
                    partidos_lg = _cargar_liga(liga)
                    st.session_state.analisis_futbol = {}
                    st.success(f"✅ {len(partidos_lg)} partidos · historial actualizado")

        if filtro_liga:
            # Con búsqueda activa: lista plana de coincidencias
            with st.container(height=320):
                for liga in ligas_filtradas:
                    _boton_liga(liga)
        else:
            # Sin búsqueda: agrupado en expanders (no se llena todo)
            grupos = {}
            for lg in ligas_filtradas:
                grupos.setdefault(_categoria_liga(lg), []).append(lg)
            for cat in _orden_cat:
                if cat in grupos:
                    with st.expander(f"{cat} ({len(grupos[cat])})", expanded=False):
                        for liga in grupos[cat]:
                            _boton_liga(liga)

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["🏀 NBA", "🥊 UFC", "⚽ FUTBOL", "⚾ MLB", "📊 Backtesting", "🎰 PARLAYS"])

    with tab1:
        if st.session_state.nba_partidos:
            for idx, p in enumerate(st.session_state.nba_partidos):
                game_key = f"nba_{p.get('local', '')}_{p.get('visitante', '')}"
                res_nba = st.session_state.analisis_nba.get(game_key)

                # Auto-análisis heurístico (sin botón): ganador + hándicap + O/U + puntos
                if res_nba is None:
                    try:
                        res_nba = analizar_nba_pro_v17(p)
                        st.session_state.analisis_nba[game_key] = res_nba
                        evento_nba = f"{p['local']} vs {p['visitante']}"
                        db.guardar_backtesting("NBA", evento_nba, res_nba.get('recomendacion', ''))
                        
                        # Guardar todas las props de jugador para backtesting
                        from motors.nba_props import obtener_props_partido
                        props = obtener_props_partido(p.get('local', ''), p.get('visitante', ''), db=db)
                        all_props = props.get("local", []) + props.get("visitante", [])
                        for prop in all_props:
                            if prop.get('confianza', 0) >= 50:
                                pick_text = f"{prop.get('jugador','?')} {prop.get('pick','')}"
                                market_type = f"NBA-PROP-{prop.get('tipo','').upper()}"
                                db.guardar_backtesting(market_type, evento_nba, pick_text)

                    except Exception as _ne:
                        logger.warning(f"Auto-análisis NBA: {_ne}")

                accion = st.session_state.visual_nba.render(p, idx, st.session_state.tracker, analisis_heuristico=res_nba)

                if accion == "analizar":
                    with st.spinner("🚀 Ejecutando Análisis de NBA..."):
                        resultado_heuristico = analizar_nba_pro_v17(p)
                        
                        # Si se selecciona una IA, usar AnalistaTotal
                        if st.session_state.get("selected_ia_model", "Heurístico") != "Heurístico":
                            analista = AnalistaTotal(
                                claude_client=st.session_state.claude,
                                gemini_client=st.session_state.gemini,
                                groq_client=st.session_state.groq,
                                # ... otros clientes
                                selected_model=st.session_state.selected_ia_model
                            )
                            resultado_ia = analista.analizar_nba(p, resultado_heuristico)
                            # FUSIONAR: conservar recomendacion/EV/total/mercados del
                            # motor heurístico y añadir la decisión de la IA encima
                            # (evita que la tarjeta muestre EV 0% / Confianza 50% / Total 0).
                            resultado_final = dict(resultado_heuristico)
                            resultado_final['ia'] = resultado_ia
                            if resultado_ia.get('pick'):
                                resultado_final['pick_ia'] = resultado_ia.get('pick')
                                resultado_final['confianza_ia'] = resultado_ia.get('confianza', 0)
                                resultado_final['razon_ia'] = resultado_ia.get('razon', '')
                                resultado_final['recomendacion'] = resultado_ia.get('pick') or resultado_final.get('recomendacion')
                                if resultado_ia.get('confianza'):
                                    resultado_final['confianza'] = resultado_ia['confianza']
                            st.session_state.analisis_nba[game_key] = resultado_final
                            db.guardar_backtesting("NBA", f"{p['local']} vs {p['visitante']}", resultado_ia.get('pick', resultado_final.get('recomendacion', '')))
                        else:
                            # Si no, usar solo el resultado heurístico
                            st.session_state.analisis_nba[game_key] = resultado_heuristico
                            db.guardar_backtesting("NBA", f"{p['local']} vs {p['visitante']}", resultado_heuristico.get('recomendacion', ''))
                        
                        # Forzar la recarga de la página para mostrar el resultado
                        st.rerun()


                with st.expander("🎯 Radar de Triples (Jugadores Clave)", expanded=False):
                    radar_triples.render(p.get('local', ''), p.get('visitante', ''))

                # ── Props de jugador (Puntos / Asistencias / Triples) ────────
                with st.expander("🏀 Props de jugador (Puntos · Asistencias · Triples)", expanded=False):
                    try:
                        from motors.nba_props import obtener_props_partido
                        props = obtener_props_partido(p.get('local', ''), p.get('visitante', ''), db=db)
                        ic = {"puntos": "🎯", "rebotes": "🏀", "asistencias": "🎁", "triples": "🏹", "doble-doble": "⭐"}
                        col_pl, col_pv = st.columns(2)
                        for col, lado, eq in ((col_pl, "local", p.get('local','')), (col_pv, "visitante", p.get('visitante',''))):
                            with col:
                                st.markdown(f"**{eq}**")
                                if props[lado]:
                                    for pr in props[lado]:
                                        prom_txt = f"prom {pr['promedio']} · " if pr.get('promedio') else ""
                                        st.markdown(
                                            f"{ic.get(pr['tipo'],'•')} **{pr['jugador']}** — "
                                            f"**{pr['pick']}** "
                                            f"<span style='color:#64748b;font-size:0.75rem'>({prom_txt}{pr['confianza']}%)</span>",
                                            unsafe_allow_html=True)
                                else:
                                    st.caption("Sin datos de jugadores.")
                    except Exception as _npe:
                        st.caption(f"Props no disponibles: {_npe}")
                st.markdown("---")
        else: st.info("👈 Carga NBA en el sidebar")

    with tab2:
        # ── Backtest del motor UFC (ganador / método / distancia) ──────────
        with st.expander("🧪 Backtest del Motor UFC — ¿qué tan bien predice?", expanded=False):
            calib_path = os.path.join("data", "ufc_calibracion.json")
            rep_path = os.path.join("data", "ufc_backtest_reporte.json")

            col_bt1, col_bt2, col_bt3 = st.columns([2, 1, 1])
            with col_bt2:
                bt_dias = st.number_input("Días", 1, 365, 30, step=1, key="ufc_bt_dias")
            with col_bt3:
                bt_max = st.number_input("Máx peleas", 20, 200, 50, step=10, key="ufc_bt_max")
            with col_bt1:
                st.write("")
                if st.button("▶️ EJECUTAR BACKTEST UFC", use_container_width=True, key="ufc_bt_run"):
                    barra = st.progress(0, text="Descargando peleas históricas...")
                    def _prog(i, n, txt):
                        barra.progress(i / max(n, 1), text=f"({i}/{n}) {txt}")
                    try:
                        from motors.ufc_backtester import UFCBacktester
                        bt = UFCBacktester()
                        bt.ejecutar_backtest(dias=int(bt_dias), max_peleas=int(bt_max), progreso_cb=_prog)
                        barra.empty()
                        st.success("✅ Backtest completado — calibración guardada y aplicada al motor.")
                        st.rerun()
                    except Exception as _bte:
                        barra.empty()
                        st.error(f"Error en backtest: {_bte}")

            if os.path.exists(rep_path):
                try:
                    with open(rep_path, encoding="utf-8") as f:
                        rep = json.load(f)
                    g = rep.get('ganador', {})
                    me = rep.get('metodo', {})
                    di = rep.get('distancia', {})
                    st.caption(f"Último backtest: {rep.get('timestamp', '')[:16].replace('T', ' ')} · "
                               f"{rep.get('muestras', 0)} peleas evaluadas")
                    m1, m2, m3 = st.columns(3)
                    m1.metric("🏆 Ganador", f"{g.get('precision', 0)}%",
                              f"{g.get('aciertos', 0)}/{rep.get('muestras', 0)} aciertos")
                    mp = me.get('precision_por_metodo', {})
                    m2.metric("🥊 Método", " · ".join(f"{k.split('/')[0]} {v}%" for k, v in mp.items()) or "—")
                    m3.metric("⏱️ Distancia", f"{di.get('precision', 0)}%",
                              f"decisiones reales: {di.get('tasa_real_decisiones', 0)}%")

                    conf_bk = g.get('por_confianza', {})
                    if conf_bk:
                        st.markdown("**Precisión por nivel de confianza del motor:**")
                        st.table([{ 'Confianza': k, 'Peleas': v['peleas'], 'Precisión': f"{v['precision']}%"}
                                  for k, v in conf_bk.items()])

                    confusion = me.get('confusion', {})
                    if confusion:
                        st.markdown("**Matriz método (predicho → real):**")
                        st.table([{'Predicho': m, **reales} for m, reales in confusion.items()])
                except Exception as _re:
                    st.caption(f"No se pudo leer el reporte: {_re}")
            else:
                st.info("Ejecuta el backtest para medir la precisión del motor y calibrarlo automáticamente.")

        base_ufc = cargar_base_ufc()
        odds_ufc = cargar_cuotas_ufc()
        
        if st.session_state.ufc_combates:
            for idx, c in enumerate(st.session_state.ufc_combates):
                if isinstance(c, dict):
                    p1_raw = c.get('peleador1', {})
                    p2_raw = c.get('peleador2', {})
                    p1_nombre = p1_raw.get('nombre', '')
                    p2_nombre = p2_raw.get('nombre', '')
                else: continue
                if not p1_nombre or not p2_nombre: continue
                
                fight_key = f"{p1_nombre}_vs_{p2_nombre}"
                if fight_key in st.session_state.ufc_enriched_cache:
                    p1_stats, p2_stats = st.session_state.ufc_enriched_cache[fight_key]
                else:
                    with st.spinner(f"🔄 Cargando stats de {p1_nombre} y {p2_nombre}..."):
                        p1_stats = st.session_state.ufc_scraper.get_fighter_stats(p1_nombre)
                        p2_stats = st.session_state.ufc_scraper.get_fighter_stats(p2_nombre)
                        if p1_stats and p2_stats:
                            st.session_state.ufc_enriched_cache[fight_key] = (p1_stats, p2_stats)
                
                p1_base = next((p for p in base_ufc if p.get('nombre','') == p1_nombre), {})
                p2_base = next((p for p in base_ufc if p.get('nombre','') == p2_nombre), {})

                # Cuotas: 1) Caliente.mx (odds_ufc)  2) las que trae el scraper de ESPN
                from scrapers.odds_api import odds_de as _odds_de
                odds1 = _odds_de(p1_nombre, odds_ufc) or p1_raw.get('odds') or 'N/A'
                odds2 = _odds_de(p2_nombre, odds_ufc) or p2_raw.get('odds') or 'N/A'

                # ESPN (p_stats) tiene prioridad sobre el JSON legacy (p_base)
                partido_visual = {
                    'peleador1': {**p1_base, **p1_stats, 'nombre': p1_nombre, 'odds': str(odds1)},
                    'peleador2': {**p2_base, **p2_stats, 'nombre': p2_nombre, 'odds': str(odds2)}
                }
                
                res_ufc = st.session_state.analisis_ufc.get(fight_key)

                # Auto-análisis: con los datos cargados, el motor da el pick sin botón
                if res_ufc is None:
                    try:
                        res_ufc = st.session_state.ufc_analyzer.analizar_combate(
                            partido_visual['peleador1'], partido_visual['peleador2'])
                        st.session_state.analisis_ufc[fight_key] = res_ufc
                        db.guardar_backtesting("UFC", f"{p1_nombre} vs {p2_nombre}", res_ufc.get('ganador', ''))
                    except Exception as _e:
                        logger.warning(f"Auto-análisis UFC falló ({p1_nombre} vs {p2_nombre}): {_e}")

                # Análisis de Claude para la columna "Premium Analytics" (si está conectado)
                claude_key = f"{fight_key}_claude"
                res_claude = st.session_state.analisis_ufc.get(claude_key)

                accion = st.session_state.visual_ufc.render(
                    c, idx, st.session_state.tracker,
                    datos_peleador1=partido_visual['peleador1'],
                    datos_peleador2=partido_visual['peleador2'],
                    analisis_ufc=res_ufc,
                    analisis_premium=res_claude,
                )

                if accion == "analizar":
                    with st.spinner("🚀 Ejecutando Análisis de UFC..."):
                        resultado_heuristico = st.session_state.ufc_analyzer.analizar_combate(partido_visual['peleador1'], partido_visual['peleador2'])

                        if st.session_state.get("selected_ia_model", "Heurístico") != "Heurístico":
                            analista = AnalistaTotal(
                                claude_client=st.session_state.claude,
                                gemini_client=st.session_state.gemini,
                                groq_client=st.session_state.groq,
                                selected_model=st.session_state.selected_ia_model
                            )
                            resultado_ia_ufc = analista.analizar_ufc(partido_visual, resultado_heuristico)
                            # FUSIONAR: conservar campos heurísticos + agregar decisión IA
                            resultado_final = dict(resultado_heuristico)
                            _ia_pick_ufc = resultado_ia_ufc.get('pick', '')
                            if _ia_pick_ufc and _ia_pick_ufc != 'N/A':
                                resultado_final['pick_ia'] = _ia_pick_ufc
                                resultado_final['confianza_ia'] = resultado_ia_ufc.get('confianza', 0)
                                resultado_final['razon_ia'] = resultado_ia_ufc.get('razon', '')
                                resultado_final['mercado_ia'] = resultado_ia_ufc.get('mercado', '')
                                resultado_final['alerta_ia'] = resultado_ia_ufc.get('alerta', '')
                            elif resultado_ia_ufc.get('error'):
                                resultado_final['ia_error'] = resultado_ia_ufc.get('error', 'Error de IA')
                            st.session_state.analisis_ufc[fight_key] = resultado_final
                            _log_pick_ia("UFC", p1_nombre, p2_nombre, resultado_ia_ufc)
                            db.guardar_backtesting("UFC", f"{p1_nombre} vs {p2_nombre}", _ia_pick_ufc or resultado_heuristico.get('ganador', ''))
                        else:
                            st.session_state.analisis_ufc[fight_key] = resultado_heuristico
                            db.guardar_backtesting("UFC", f"{p1_nombre} vs {p2_nombre}", resultado_heuristico.get('ganador', ''))

                        # Claude SIEMPRE (si está conectado) para la columna Premium, independiente del modelo elegido
                        if st.session_state.get("claude"):
                            try:
                                analista_claude = AnalistaTotal(claude_client=st.session_state.claude, selected_model="Claude")
                                st.session_state.analisis_ufc[claude_key] = analista_claude.analizar_ufc(partido_visual, resultado_heuristico)
                            except Exception as _ce:
                                logger.warning(f"Claude UFC falló: {_ce}")

                        st.rerun()



                st.markdown("---")
        else: st.info("👈 Carga UFC en el sidebar")

    with tab3:
        if st.session_state.futbol_partidos:
            for liga, partidos in st.session_state.futbol_partidos.items():
                if partidos:
                    st.markdown(f"### ⚽ {liga}")
                    for idx, p in enumerate(partidos):
                        # La versión del motor en la clave invalida el caché viejo
                        # automáticamente cuando se actualiza la lógica del motor.
                        key_fut = f"fut_v27_{liga}_{idx}"
                        res_fut = st.session_state.analisis_futbol.get(key_fut)

                        # Auto-análisis jerárquico (con fallback FIFA para el Mundial)
                        if res_fut is None:
                            try:
                                res_fut = analizar_futbol_jerarquico(
                                    p.get('home') or p.get('local', ''),
                                    p.get('away') or p.get('visitante', ''),
                                    es_torneo=p.get('es_torneo', False),
                                    fase=p.get('fase', ''),
                                    liga=liga,
                                )
                                st.session_state.analisis_futbol[key_fut] = res_fut
                                pick_f = res_fut.get('pick', '')
                                if pick_f and 'revisar' not in pick_f.lower():
                                    db.guardar_backtesting("SOCCER", f"{p.get('home')} vs {p.get('away')}", pick_f)
                            except Exception as _fe:
                                logger.warning(f"Auto-análisis fútbol {liga} {idx}: {_fe}")

                        with st.container(border=True):   # borde tipo MLB, visual más organizado
                            accion_fut = st.session_state.visual_futbol.render(
                                p, idx, liga, st.session_state.tracker,
                                analisis_heuristico=res_fut,
                                analisis_ia=st.session_state.analisis_futbol.get(f"{key_fut}_ia"),
                                mercados=st.session_state.analisis_futbol.get(f"{key_fut}_mkt"),
                            )
                        if accion_fut == "analizar":
                            with st.spinner("Calculando mercados (Moneyline · O/U · BTTS · goleadores)..."):
                                # Mercados completos (heurístico Poisson) — SIEMPRE
                                try:
                                    from motors.futbol_analyzer_jerarquico import mercados_completos_futbol
                                    st.session_state.analisis_futbol[f"{key_fut}_mkt"] = mercados_completos_futbol(
                                        p.get('home') or p.get('local', ''),
                                        p.get('away') or p.get('visitante', ''),
                                        es_torneo=p.get('es_torneo', False), fase=p.get('fase', ''))
                                except Exception as _mke:
                                    logger.warning(f"mercados fútbol: {_mke}")
                                # IA opcional (si hay modelo seleccionado)
                                if st.session_state.get("selected_ia_model", "Heurístico") != "Heurístico":
                                    analista = AnalistaTotal(
                                        claude_client=st.session_state.claude,
                                        gemini_client=st.session_state.gemini,
                                        groq_client=st.session_state.groq,
                                        selected_model=st.session_state.selected_ia_model,
                                    )
                                    _res_ia_fut = analista.analizar_futbol(p, res_fut, res_fut)
                                    st.session_state.analisis_futbol[f"{key_fut}_ia"] = _res_ia_fut
                                    _log_pick_ia("SOCCER",
                                                 p.get('home') or p.get('local', ''),
                                                 p.get('away') or p.get('visitante', ''),
                                                 _res_ia_fut)
                            st.rerun()
                        st.markdown("---")
        else: st.info("👈 Carga ligas en el sidebar")

    with tab4:
        if st.session_state.mlb_partidos:
            for idx, p in enumerate(st.session_state.mlb_partidos):
                # Clave única por equipos (evita colisión de game_pk → datos cruzados)
                game_key = f"mlb_{p.get('visitante','')}_{p.get('local','')}_{idx}"
                res_mlb = st.session_state.analisis_mlb.get(game_key)

                # Auto-análisis (sin botón): pick + candidatos HR + O/U automáticos
                if res_mlb is None:
                    try:
                        # 1. Ejecutar el análisis avanzado (el que ya tenías)
                        res_avanzado = analizar_mlb_pro_v20(p, game_pk=p.get('game_pk'), predictor_hr=st.session_state.predictor_hr)
                        
                        # 2. Ejecutar el análisis básico (tu motor antiguo)
                        res_basico = _analisis_basico_record(p)

                        # 3. Sistema de Votación y Decisión Final
                        from collections import Counter
                        votos = Counter()
                        votos[res_avanzado.get('pick')] += 1
                        votos[res_basico.get('pick')] += 1
                        
                        pick_final = votos.most_common(1)[0][0]
                        
                        # Fusionar resultados en un solo diccionario
                        res_final = res_avanzado.copy()
                        res_final['pick'] = pick_final
                        # La confianza puede ser un promedio o la del modelo que gana
                        res_final['confianza'] = (res_avanzado.get('confianza', 50) + res_basico.get('confianza', 50)) // 2
                        res_final['razon_desglose'] = {
                            "Récord General (Motor Antiguo)": f"{res_basico.get('pick')} ({res_basico.get('confianza')}%)",
                            "Análisis Avanzado (Pitchers/Stats)": f"{res_avanzado.get('pick')} ({res_avanzado.get('confianza')}%)",
                            "Decisión Final (Voto)": pick_final
                        }
                        st.session_state.analisis_mlb[game_key] = res_final
                        res_mlb = res_final   # ← para que el visual SÍ muestre el pick
                        evento_mlb = f"{p.get('visitante','?')} @ {p.get('local','?')}"
                        db.guardar_backtesting("MLB", evento_mlb, f"Gana {res_final.get('pick', '')}")
                        if res_final.get('ou_pick'):
                            db.guardar_backtesting("MLB-OU", evento_mlb, f"{res_final['ou_pick']} {res_final.get('ou_linea_ajustada','')}")
                        for _kp in res_final.get('k_picks', []):
                            db.guardar_backtesting("MLB-K", evento_mlb, f"{_kp.get('pitcher','')}: {_kp.get('prediccion','')} {_kp.get('linea','')} K")
                        for _hr in res_final.get('hr_candidates', [])[:3]:
                            if _hr.get('probabilidad', 0) >= 25:
                                db.guardar_backtesting("MLB-HR", evento_mlb, f"{_hr.get('jugador','')} HR ({_hr.get('probabilidad',0):.0f}%)")
                    except Exception as _me:
                        logger.warning(f"Auto-análisis MLB: {_me}")

                accion = st.session_state.visual_mlb.render(p, idx, st.session_state.tracker, analisis_mlb=res_mlb)

                if accion == "analizar":
                    with st.spinner("🚀 Ejecutando Análisis Dinámico de MLB..."):
                        resultado_heuristico = analizar_mlb_pro_v20(
                            p,
                            game_pk=p.get('game_pk'),
                            predictor_hr=st.session_state.predictor_hr
                        )
                        
                        if st.session_state.get("selected_ia_model", "Heurístico") != "Heurístico":
                            analista = AnalistaTotal(
                                claude_client=st.session_state.claude,
                                gemini_client=st.session_state.gemini,
                                groq_client=st.session_state.groq,
                                selected_model=st.session_state.selected_ia_model
                            )
                            resultado_ia = analista.analizar_mlb(p, resultado_heuristico)
                            # FUSIONAR: conservar HR/K/O-U del motor + agregar la decisión IA
                            resultado_final = dict(resultado_heuristico)
                            resultado_final['ia'] = resultado_ia
                            _ia_pick_mlb = resultado_ia.get('pick', '')
                            if _ia_pick_mlb and _ia_pick_mlb != 'N/A':
                                resultado_final['pick_ia'] = _ia_pick_mlb
                                resultado_final['confianza_ia'] = resultado_ia.get('confianza', 0)
                                resultado_final['razon_ia'] = resultado_ia.get('razon', '')
                                resultado_final['mercado_ia'] = resultado_ia.get('mercado', '')
                            elif resultado_ia.get('error'):
                                resultado_final['ia_error'] = resultado_ia.get('error', 'Error de IA')
                            st.session_state.analisis_mlb[game_key] = resultado_final
                            _log_pick_ia("MLB", p.get('local', ''), p.get('visitante', ''), resultado_ia)
                            db.guardar_backtesting("MLB", f"{p['local']} vs {p['visitante']}", resultado_ia.get('pick', resultado_heuristico.get('pick', '')))
                        else:
                            st.session_state.analisis_mlb[game_key] = resultado_heuristico
                            db.guardar_backtesting("MLB", f"{p['local']} vs {p['visitante']}", resultado_heuristico.get('pick', ''))

                        st.rerun()

                st.markdown("---")
        else: st.info("👈 Carga MLB en el sidebar")

    with tab5:
        st.header("📊 Reporte de Backtesting Universal")
        st.caption("Resultados del rendimiento histórico de los motores de análisis.")

        # ── 🧠 APRENDIZAJE — Parlays generados + aciertos ───────────────────
        with st.expander("🧠 Aprendizaje — Parlays generados y resultados", expanded=False):
            try:
                from utils.parlay_log import historial as _ph_historial, stats_parlays as _ph_stats
                _ph_stats_data = _ph_stats()
                _ph_hist = _ph_historial(dias=30)
            except Exception as _ple:
                _ph_stats_data = {}
                _ph_hist = []

            # ── Métricas globales de picks (pick_memory) ──────────────────────
            if pick_memory is not None:
                s = pick_memory.stats()
                g = s["global"]
                cA, cB, cC, cD = st.columns(4)
                cA.metric("Picks resueltos", g["total"])
                cB.metric("Win Rate picks", f"{g['win_rate']}%")
                cC.metric("ROI picks", f"{g['roi']:+.1f}%")
                cD.metric("Pendientes", s["pendientes"])

                # ── Comparativo IA vs Heurístico ──────────────────────────────
                pf = s.get("por_fuente", {})
                pend_f = s.get("pendientes_por_fuente", {})
                st.markdown("**🤖 IA vs 🧮 Heurístico** — quién acierta más (se llena conforme se resuelven los juegos):")
                fuentes = sorted(set(pf) | set(pend_f), key=lambda x: x != "IA")  # IA primero
                if not pf.get("IA") and pend_f.get("IA", 0) == 0:
                    st.info("ℹ️ Aún no hay picks de IA registrados. Analiza partidos con un modelo de IA "
                            "seleccionado (no 'Heurístico') y se empezarán a guardar para backtestear.")
                cols_f = st.columns(max(1, len(fuentes)))
                for i, fte in enumerate(fuentes):
                    d = pf.get(fte, {"total": 0, "win_rate": 0, "roi": 0})
                    pend = pend_f.get(fte, 0)
                    etiqueta = "🤖 IA" if fte == "IA" else f"🧮 {fte}"
                    cols_f[i].metric(
                        etiqueta,
                        f"{d['win_rate']}% WR" if d["total"] else "sin resolver",
                        f"ROI {d['roi']:+.1f}% · {d['total']} res · {pend} pend" if d["total"]
                        else f"{pend} pendientes",
                    )

            # ── Métricas de parlays ───────────────────────────────────────────
            if _ph_stats_data.get("total", 0) > 0:
                st.markdown("**Rendimiento de parlays generados:**")
                pA, pB, pC, pD = st.columns(4)
                pA.metric("Parlays resueltos", _ph_stats_data["total"])
                pB.metric("Ganados", _ph_stats_data["ganados"])
                pC.metric("Win Rate", f"{_ph_stats_data['win_rate']}%")
                pD.metric("ROI", f"{_ph_stats_data['roi']:+.1f}%")

            # ── Historial de parlays por día ──────────────────────────────────
            if _ph_hist:
                st.markdown("---")
                st.markdown("**Parlays generados (últimos 30 días):**")

                # Agrupar por fecha
                por_fecha: dict = {}
                for p in _ph_hist:
                    f = p.get("fecha", "?")
                    por_fecha.setdefault(f, []).append(p)

                for fecha, parlays in sorted(por_fecha.items(), reverse=True):
                    ganados_dia  = sum(1 for p in parlays if p.get("estado") == "ganado")
                    perdidos_dia = sum(1 for p in parlays if p.get("estado") == "perdido")
                    pend_dia     = sum(1 for p in parlays if p.get("estado") in (None, "pendiente"))
                    resumen_dia  = (f"✅ {ganados_dia}G" if ganados_dia else "") + \
                                   (f" ❌ {perdidos_dia}P" if perdidos_dia else "") + \
                                   (f" ⏳ {pend_dia} pend." if pend_dia else "")
                    st.markdown(f"**📅 {fecha}** · {len(parlays)} parlays · {resumen_dia.strip()}")

                    for p in parlays:
                        estado = p.get("estado") or "pendiente"
                        ico_estado = {"ganado": "✅", "perdido": "❌", "parcial": "🔶",
                                      "pendiente": "⏳"}.get(estado, "⏳")
                        cuota = p.get("cuota", 0)
                        def _dec2am(d):
                            try:
                                d = float(d)
                                if d <= 1: return "—"
                                return f"+{round((d-1)*100)}" if d >= 2 else f"-{round(100/(d-1))}"
                            except Exception: return "—"
                        momio_str = _dec2am(cuota) if cuota else "—"
                        tipo_short = str(p.get("tipo", "")).replace("🎯", "").replace("🚀", "").replace(
                            "💎", "").replace("💣", "").replace("⚡", "").strip()[:20]

                        with st.container():
                            col_e, col_t, col_m, col_p = st.columns([1, 3, 2, 2])
                            col_e.markdown(f"<span style='font-size:1.1rem'>{ico_estado}</span>",
                                           unsafe_allow_html=True)
                            col_t.markdown(f"<span style='font-size:0.82rem;color:#cbd5e1'>{tipo_short}</span>"
                                           f"<br><span style='font-size:0.72rem;color:#64748b'>"
                                           f"{p.get('n_legs', len(p.get('legs',[])))}-legs · "
                                           f"EV {p.get('ev_pct',0):+.1f}%</span>",
                                           unsafe_allow_html=True)
                            col_m.markdown(f"<span style='color:#22c55e;font-weight:700'>{momio_str}</span>"
                                           f"<span style='color:#64748b;font-size:0.75rem'> ({cuota:.1f}x)</span>",
                                           unsafe_allow_html=True)
                            col_p.markdown(f"<span style='color:#94a3b8;font-size:0.78rem'>"
                                           f"Prob {p.get('prob',0):.1f}%</span>",
                                           unsafe_allow_html=True)

                        # Legs del parlay (colapsado)
                        legs_txt = " · ".join(
                            f"{l.get('sport','').split()[-1]} {l.get('pick','')[:30]}"
                            for l in p.get("legs", [])
                        )
                        st.caption(legs_txt)
                        st.markdown("<hr style='margin:4px 0;border-color:#1e293b'>",
                                    unsafe_allow_html=True)
            else:
                st.info("Aún no hay parlays guardados. Ve a la pestaña **Parlays** para generar el primero — "
                        "cada parlay se guarda automáticamente y aquí verás sus resultados.")

            # ── Auto-resolver ─────────────────────────────────────────────────
            st.markdown("---")
            col_r1, col_r2 = st.columns(2)
            with col_r1:
                if st.button("🔄 Auto-resolver MLB + NBA", use_container_width=True):
                    try:
                        from motors.box_score_resolver import resolver_todo
                        with st.spinner("Cruzando picks con box scores reales..."):
                            rr = resolver_todo()
                        if rr['total'] == 0:
                            st.info("0 resueltos — los juegos de esos picks aún no terminan.")
                        else:
                            st.success(f"✅ {rr['mlb']} MLB + {rr['nba']} NBA resueltos.")
                        # Cerrar el ciclo: resolver los parlays cuyos picks ya se saben
                        try:
                            from motors.parlay_brain import resolver_parlays_pendientes
                            n_par = resolver_parlays_pendientes()
                            if n_par:
                                st.success(f"🎰 {n_par} parlay(s) resueltos automáticamente.")
                        except Exception:
                            pass
                        st.rerun()
                    except Exception as _be:
                        st.error(f"Error: {_be}")
            with col_r2:
                if st.button("⚽ Auto-resolver Fútbol", use_container_width=True):
                    try:
                        with st.spinner("Cruzando picks de fútbol..."):
                            _res_f = _auto_resolver_futbol()
                        st.success(f"✅ {_res_f} picks de fútbol resueltos.")
                        try:
                            from motors.parlay_brain import resolver_parlays_pendientes
                            n_par = resolver_parlays_pendientes()
                            if n_par:
                                st.success(f"🎰 {n_par} parlay(s) resueltos automáticamente.")
                        except Exception:
                            pass
                        st.rerun()
                    except Exception as _re:
                        st.error(f"Error: {_re}")

            # ── Estadísticas de aprendizaje por TIPO de parlay ────────────────
            try:
                from motors.parlay_brain import stats_por_tipo
                _stats_t = stats_por_tipo()
                if _stats_t:
                    st.markdown("---")
                    st.markdown("**📊 Aprendizaje por tipo de parlay (resultados reales):**")
                    st.caption("Cuántos parlays de cada tipo se resolvieron y cuál tiene mejor tasa de acierto. "
                               "El generador ya usa esto para mostrarte primero los tipos más rentables.")
                    filas_t = sorted(_stats_t.items(), key=lambda x: x[1].get("win_rate", 0), reverse=True)
                    for tipo_t, s_t in filas_t:
                        color_t = "#22c55e" if s_t["win_rate"] >= 50 else "#ef4444"
                        tipo_lbl = str(tipo_t).replace("🎯","").replace("🟢","").replace("🟡","").replace(
                            "🔴","").replace("🟣","").replace("💎","").replace("⚡","").strip()[:30]
                        st.markdown(
                            f"<div style='background:#0f172a;border-radius:6px;padding:5px 12px;margin:2px 0'>"
                            f"<b>{tipo_lbl}</b> — "
                            f"<span style='color:{color_t}'>{s_t['win_rate']}% acierto</span> "
                            f"({s_t['ganados']}/{s_t['total']}) · "
                            f"ROI <span style='color:{'#22c55e' if s_t['roi']>=0 else '#ef4444'}'>"
                            f"{s_t['roi']:+.1f}%</span>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                    st.caption("⚠️ Necesitas al menos 4+ parlays resueltos por tipo para que el aprendizaje "
                               "sea estadísticamente significativo. Genera parlays diariamente y resuélvelos "
                               "con los botones de arriba.")
            except Exception:
                pass

            # ── Tabla pick_memory por deporte / mercado ───────────────────────
            if pick_memory is not None:
                s2 = pick_memory.stats()
                if s2.get("por_deporte"):
                    with st.expander("📊 Detalle por deporte y mercado", expanded=False):
                        st.markdown("**Por deporte:**")
                        st.table([{"Deporte": k, "Picks": v["total"], "Aciertos": v["aciertos"],
                                   "Win Rate": f"{v['win_rate']}%", "ROI": f"{v['roi']:+.1f}%"}
                                  for k, v in s2["por_deporte"].items()])
                        if s2.get("por_mercado"):
                            st.markdown("**Por mercado:**")
                            st.table([{"Mercado": k, "Picks": v["total"], "Aciertos": v["aciertos"],
                                       "Win Rate": f"{v['win_rate']}%", "ROI": f"{v['roi']:+.1f}%"}
                                      for k, v in sorted(s2["por_mercado"].items(),
                                                         key=lambda x: x[1]["win_rate"], reverse=True)])
                            st.caption("💡 El selector de Parlays ya usa estas tasas automáticamente.")


        # ── BACKTEST REAL MLB (scraper oficial → auditor → efectividad) ──────
        # ── BACKTEST REAL DEL MOTOR (corre el motor sobre cada juego histórico) ──
        with st.expander("🎯 BACKTEST REAL DEL MOTOR — corre el motor sobre los últimos N días", expanded=True):
            st.caption("Reconstruye cada juego de los últimos N días con los datos de ESE día (récords, pitchers, estadio), "
                       "corre el MOTOR COMPLETO igual que la app, y compara contra el resultado real. "
                       "Mide si el moneyline ganó, si el O/U acertó y cuáles candidatos a HR conectaron ese día.")
            col_br1, col_br2 = st.columns([3, 1])
            with col_br2:
                dias_real = st.number_input("Días", 1, 30, 15, step=1, key="br_dias")
            with col_br1:
                st.write("")
                if st.button("🎯 EJECUTAR BACKTEST REAL DEL MOTOR", use_container_width=True, type="primary", key="br_run"):
                    barra_br = st.progress(0, text="Corriendo el motor sobre cada juego histórico...")
                    def _pbr(i, txt):
                        barra_br.progress(min(0.99, i / 300), text=txt[:60])
                    try:
                        from motors.mlb_backtest_real import ejecutar_backtest_real
                        ejecutar_backtest_real(dias=int(dias_real), progreso_cb=_pbr)
                        barra_br.empty()
                        st.success("✅ Backtest real completado.")
                    except Exception as _bre:
                        barra_br.empty()
                        st.error(f"Error: {_bre}")
                        logger.exception(_bre)

            br = cargar_json_safe(os.path.join("data", "mlb_backtest_real.json"))
            if br:
                st.caption(f"Último: {br.get('timestamp','')[:16].replace('T',' ')} · {br.get('juegos',0)} juegos analizados con el motor")
                mlb_, ou_, hr_ = br.get("moneyline", {}), br.get("over_under", {}), br.get("home_runs", {})
                rl_ = br.get("run_line", {})
                m1, m2, m3 = st.columns(3)
                m1.metric("🏆 Moneyline", f"{mlb_.get('precision_global',0)}%", f"{mlb_.get('aciertos',0)}/{mlb_.get('total',0)}")
                m2.metric("📊 Over/Under", f"{ou_.get('precision',0)}%", f"{ou_.get('aciertos',0)}/{ou_.get('total',0)}")
                m3.metric("💣 Home Runs", f"{hr_.get('precision_global',0)}%", f"{hr_.get('aciertos',0)}/{hr_.get('predichos',0)}")
                if rl_.get("total"):
                    st.metric("🎯 Hándicap (Run Line ±1.5)", f"{rl_.get('precision',0)}%",
                              f"{rl_.get('aciertos',0)}/{rl_.get('total',0)} · ¿conviene meter run line?")

                pc = mlb_.get("por_confianza_motor", {})
                if pc:
                    st.markdown("**Moneyline por confianza del motor** (a mayor confianza, debe acertar más):")
                    st.table([{"Confianza motor": k, "Juegos": v["n"], "Aciertos": v["ok"], "Precisión": f"{v['precision']}%"}
                              for k, v in sorted(pc.items(), reverse=True)])
                ht = hr_.get("por_tramo", {})
                if ht:
                    st.markdown("**Home Runs por probabilidad del motor:**")
                    st.table([{"Probabilidad": k, "Candidatos": v["pred"], "Conectaron": v["ok"], "Precisión": f"{v['precision']}%"}
                              for k, v in sorted(ht.items(), reverse=True)])

        # ── BACKTEST REAL NBA + UFC (corre los motores sobre juegos pasados) ──
        with st.expander("🏀 BACKTEST REAL NBA — corre el motor NBA sobre los últimos N días", expanded=False):
            st.caption("Reconstruye cada juego NBA de los últimos N días (récords + marcador real) y corre el motor "
                       "para medir si el moneyline ganó, el O/U acertó y el hándicap cubrió.")
            col_nb1, col_nb2 = st.columns([3, 1])
            with col_nb2:
                dias_nba = st.number_input("Días", 1, 45, 7, step=1, key="nba_br_dias")
            with col_nb1:
                st.write("")
                if st.button("🏀 EJECUTAR BACKTEST REAL NBA", use_container_width=True, key="nba_br_run"):
                    barra_nb = st.progress(0, text="Corriendo el motor NBA sobre juegos pasados...")
                    try:
                        from motors.nba_backtest_real import ejecutar_nba_backtest_real
                        ejecutar_nba_backtest_real(dias=int(dias_nba),
                                                   progreso_cb=lambda i, t: barra_nb.progress(min(0.99, i/80), text=t[:55]))
                        barra_nb.empty()
                        st.success("✅ Backtest NBA completado.")
                    except Exception as _ne:
                        barra_nb.empty()
                        st.error(f"Error: {_ne}")

            nbr = cargar_json_safe(os.path.join("data", "nba_backtest_real.json"))
            if nbr:
                st.caption(f"Último: {nbr.get('timestamp','')[:16].replace('T',' ')} · {nbr.get('juegos',0)} juegos")
                n1, n2, n3 = st.columns(3)
                n1.metric("🏆 Moneyline", f"{nbr['moneyline']['precision_global']}%", f"{nbr['moneyline']['aciertos']}/{nbr['moneyline']['total']}")
                n2.metric("📊 Over/Under", f"{nbr['over_under']['precision']}%", f"{nbr['over_under']['aciertos']}/{nbr['over_under']['total']}")
                n3.metric("🎯 Hándicap", f"{nbr['handicap']['precision']}%", f"{nbr['handicap']['aciertos']}/{nbr['handicap']['total']}")
                pcn = nbr['moneyline'].get("por_confianza_motor", {})
                if pcn:
                    st.table([{"Confianza motor": k, "Juegos": v["n"], "Aciertos": v["ok"], "Precisión": f"{v['precision']}%"}
                              for k, v in sorted(pcn.items(), reverse=True)])

                # Detalle por juego: ML / O-U / Hándicap con aciertos
                det_nba = nbr.get("detalle", [])
                if det_nba:
                    with st.expander(f"🔍 Ver {min(len(det_nba),30)} juegos (ML · O/U · Hándicap)", expanded=False):
                        def _mk(v):
                            return "✅" if v is True else ("❌" if v is False else "—")
                        st.table([{
                            "Juego": d.get("juego", ""), "Marcador": d.get("marcador", ""),
                            "ML": f"{d.get('ml_pick','')} {_mk(d.get('ml_ok'))}",
                            "O/U": f"{d.get('ou_pick','')} {_mk(d.get('ou_ok'))}",
                            "Hcap": _mk(d.get("hcap_ok")),
                        } for d in det_nba[:30]])

        with st.expander("🥊 BACKTEST REAL UFC — corre el motor UFC sobre peleas pasadas", expanded=False):
            st.caption("Descarga peleas reales recientes y mide si el motor acertó el ganador, el método y la distancia.")
            col_uf1, col_uf2 = st.columns([3, 1])
            with col_uf2:
                dias_ufc_bt = st.number_input("Días", 1, 180, 30, step=1, key="ufc_br_dias")
                max_ufc = st.number_input("Máx peleas", 20, 120, 40, step=10, key="ufc_br_max")
            with col_uf1:
                st.write("")
                if st.button("🥊 EJECUTAR BACKTEST REAL UFC", use_container_width=True, key="ufc_br_run"):
                    barra_uf = st.progress(0, text="Corriendo el motor UFC sobre peleas pasadas...")
                    try:
                        from motors.ufc_backtester import UFCBacktester
                        UFCBacktester().ejecutar_backtest(dias=int(dias_ufc_bt), max_peleas=int(max_ufc),
                                                          progreso_cb=lambda i, n, t: barra_uf.progress(min(0.99, i/max(n,1)), text=t[:50]))
                        barra_uf.empty()
                        st.success("✅ Backtest UFC completado (calibración aplicada al motor).")
                    except Exception as _ue:
                        barra_uf.empty()
                        st.error(f"Error: {_ue}")

            ubr = cargar_json_safe(os.path.join("data", "ufc_backtest_reporte.json"))
            if ubr:
                st.caption(f"Último: {ubr.get('timestamp','')[:16].replace('T',' ')} · {ubr.get('muestras',0)} peleas")
                u1, u2, u3 = st.columns(3)
                u1.metric("🏆 Ganador", f"{ubr.get('ganador',{}).get('precision',0)}%")
                mp_ufc = ubr.get('metodo', {}).get('precision_por_metodo', {})
                u2.metric("🥊 Método", " · ".join(f"{k.split('/')[0]} {v}%" for k, v in mp_ufc.items()) or "—")
                u3.metric("⏱️ Distancia", f"{ubr.get('distancia',{}).get('precision',0)}%")

                # ── Última cartelera: predicciones del motor vs resultado real ──
                detalle_ufc = ubr.get("detalle", [])
                if detalle_ufc:
                    # Tomar el evento más reciente (mayor fecha)
                    ult_fecha = max((d.get("fecha", "") for d in detalle_ufc), default="")
                    ult = [d for d in detalle_ufc if d.get("fecha", "") == ult_fecha]
                    nombre_ev = ult[0].get("evento", "Última cartelera") if ult else "Última cartelera"
                    aciertos_ev = sum(1 for d in ult if d.get("ganador_ok"))
                    st.markdown(f"**🥊 Última cartelera evaluada: {nombre_ev}** "
                                f"({ult_fecha}) — acertó {aciertos_ev}/{len(ult)} ganadores")
                    st.table([{
                        "Pelea": d.get("pelea", ""),
                        "Predicción": d.get("ganador_pred", ""),
                        "Real": d.get("ganador_real", ""),
                        "Conf.": f"{d.get('confianza',0):.0f}%",
                        "Método pred/real": f"{d.get('metodo_pred','?')} / {d.get('metodo_real','?')}",
                        "Ganador": "✅" if d.get("ganador_ok") else "❌",
                    } for d in ult])
                    st.caption("💡 Esto alimenta la calibración del motor: aprende de qué tipo de pelea acierta o falla.")

        # ── BACKTEST REAL FÚTBOL (corre el motor jerárquico sobre partidos pasados) ──
        with st.expander("⚽ BACKTEST REAL FÚTBOL — out-of-sample, SIN leakage", expanded=False):
            st.caption("Descarga partidos finalizados de las ligas principales (Premier, LaLiga, Serie A, "
                       "Bundesliga, Ligue 1, Liga MX, MLS, etc.) en los últimos N días y corre el motor "
                       "jerárquico CON CORTE TEMPORAL: para cada partido solo ve la forma ANTERIOR (no el "
                       "marcador). Por eso esta precisión SÍ es la que el programa puede acertar en vivo "
                       "(ya no el ~95% inflado que salía cuando el motor 'veía' el resultado).")
            col_fb1, col_fb2 = st.columns([3, 1])
            with col_fb2:
                dias_fut = st.number_input("Días", 1, 30, 7, step=1, key="fut_br_dias")
            with col_fb1:
                st.write("")
                if st.button("⚽ EJECUTAR BACKTEST REAL FÚTBOL", use_container_width=True, key="fut_br_run"):
                    barra_fb = st.progress(0, text="Corriendo el motor de fútbol sobre partidos pasados...")
                    def _pfb(i, n, t):
                        barra_fb.progress(min(0.99, i / max(n, 1)), text=str(t)[:55])
                    try:
                        from motors.futbol_backtest_real import ejecutar_futbol_backtest_real
                        ejecutar_futbol_backtest_real(dias=int(dias_fut), progreso_cb=_pfb)
                        barra_fb.empty()
                        st.success("✅ Backtest de fútbol completado.")
                    except Exception as _fe:
                        barra_fb.empty()
                        st.error(f"Error: {_fe}")
                        logger.exception(_fe)

            fbr = cargar_json_safe(os.path.join("data", "futbol_backtest_real.json"))
            if fbr and fbr.get("evaluados"):
                st.caption(f"Último: {fbr.get('timestamp','')[:16].replace('T',' ')} · "
                           f"{fbr.get('partidos',0)} partidos · {fbr.get('evaluados',0)} picks evaluados")
                mk = fbr.get("mercados", {})
                f1, f2, f3, f4 = st.columns(4)
                f1.metric("🏆 Moneyline", f"{mk.get('moneyline',{}).get('precision',0)}%",
                          f"{mk.get('moneyline',{}).get('aciertos',0)}/{mk.get('moneyline',{}).get('total',0)}")
                f2.metric("⚽ Over/Under", f"{mk.get('over_under',{}).get('precision',0)}%",
                          f"{mk.get('over_under',{}).get('aciertos',0)}/{mk.get('over_under',{}).get('total',0)}")
                f3.metric("🤝 BTTS", f"{mk.get('btts',{}).get('precision',0)}%",
                          f"{mk.get('btts',{}).get('aciertos',0)}/{mk.get('btts',{}).get('total',0)}")
                f4.metric("🎰 Combo", f"{mk.get('combo',{}).get('precision',0)}%",
                          f"{mk.get('combo',{}).get('aciertos',0)}/{mk.get('combo',{}).get('total',0)}")
                st.markdown(f"**Precisión global del motor de fútbol: {fbr.get('precision_global',0)}%**")
                # Nota metodológica: el backtest puede diferir del pick en vivo
                nota_bt = fbr.get("nota_metodologia", "")
                if nota_bt:
                    if fbr.get("sin_leakage"):
                        st.success(f"✅ **Backtest honesto (out-of-sample):**\n\n{nota_bt}")
                    else:
                        st.warning(f"⚠️ **Backtest con leakage (precisión inflada, NO reproducible en vivo):**\n\n{nota_bt}")
                det = fbr.get("detalle", [])
                if det:
                    st.table([{"Fecha": d.get("fecha", ""), "Partido": d["partido"],
                               "Pick (motor)": d["pick"],
                               "Mercado": d["mercado"], "Conf.": f"{d['confianza']}%",
                               "Resultado": "✅" if d["acierto"] else "❌"} for d in det[:25]])
            elif fbr:
                st.info(fbr.get("error", "Sin picks evaluables todavía. Ejecuta el backtest."))

        # ── DASHBOARD MARCADOR CORRECTO (Dixon-Coles) ──────────────────────────
        with st.expander("🎯 MARCADOR CORRECTO — ¿acertó el Top-3 del modelo Dixon-Coles?", expanded=False):
            st.caption("Para cada partido de selecciones de los últimos N días, el modelo propone 3 marcadores. "
                       "Aquí ves cuál pegó EXACTO (y en qué posición), cuál se ACERCÓ más, y si acertó el 1X2. "
                       "El modelo se entrena EXCLUYENDO esos días (out-of-sample, sin trampa).")
            col_mc1, col_mc2 = st.columns([3, 1])
            with col_mc2:
                dias_mc = st.number_input("Días", 3, 30, 10, step=1, key="mc_bt_dias")
            with col_mc1:
                st.write("")
                if st.button("🎯 EJECUTAR BACKTEST MARCADOR CORRECTO", use_container_width=True, key="mc_bt_run"):
                    with st.spinner("Entrenando Dixon-Coles sin la ventana y evaluando marcadores..."):
                        try:
                            from motors.backtest_marcador_correcto import backtest_marcador
                            st.session_state["_mc_bt"] = backtest_marcador(dias=int(dias_mc))
                        except Exception as _mce:
                            st.error(f"Error: {_mce}")
                            logger.exception(_mce)

            _mc = st.session_state.get("_mc_bt")
            if _mc and _mc.get("resumen", {}).get("partidos"):
                r = _mc["resumen"]
                st.caption(f"Ventana: {r['desde']} → {r['hasta']} · {r['partidos']} partidos de selecciones (out-of-sample)")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("✅ Exacto (Top-3)", f"{r['exacto_top3_pct']}%", f"Top-1: {r['exacto_top1_pct']}%")
                m2.metric("🏆 Resultado 1X2", f"{r['outcome_1x2_pct']}%")
                m3.metric("🎯 Cerca (≤1 gol)", f"{r['cerca_1gol_pct']}%")
                m4.metric("📏 Distancia media", f"{r['distancia_media']}", help="0 = marcador exacto")
                st.info("ℹ️ Acertar el marcador EXACTO ronda 1 de 7 por partido; ~34% en Top-3 y ~67% a ≤1 gol "
                        "es lo realista. Úsalo para ver dónde el modelo se acerca y seguir calibrando.")
                def _icono_mc(p):
                    if p["exacto_rank"]:
                        return f"✅ EXACTO (#{p['exacto_rank']})"
                    if p["outcome_ok"]:
                        return "🎯 acertó 1X2"
                    return f"📏 cerca (d={p['distancia']})" if p["distancia"] <= 1 else f"❌ d={p['distancia']}"
                st.table([{
                    "Fecha": p["fecha"],
                    "Partido": f"{p['local']} {p['real']} {p['visitante']}",
                    "Top-3 predicho": " · ".join(p["top3"]),
                    "Resultado": _icono_mc(p),
                } for p in _mc["partidos"][:30]])
            elif _mc and _mc.get("error"):
                st.warning(f"⚠️ {_mc['error']}")

        with st.expander("⚾ Backtest por picks guardados (efectividad acumulada HR / ML / O-U / K)", expanded=False):
            st.caption("Descarga resultados reales de la MLB Stats API, cruza tus picks pendientes y mide qué tan efectivo es cada mercado.")
            col_mlb_bt1, col_mlb_bt2 = st.columns([3, 1])
            with col_mlb_bt2:
                dias_mlb = st.number_input("Días", 1, 45, 15, step=1, key="mlb_real_bt_dias")
            with col_mlb_bt1:
                st.write("")
                if st.button("▶️ EJECUTAR BACKTEST REAL MLB", use_container_width=True, key="mlb_real_bt_run"):
                    try:
                        from scrapers.mlb_resultados_scraper import MLBResultadosScraper
                        from motors.mlb_backtest_auditor import MLBBacktestAuditor
                        from motors.mlb_effectiveness import EffectivenessCalculator
                        with st.spinner("1/3 Descargando resultados reales de MLB..."):
                            MLBResultadosScraper(dias=int(dias_mlb)).collect_last_n_days(int(dias_mlb))
                        with st.spinner("2/3 Auditando picks pendientes contra resultados reales..."):
                            reporte_audit = MLBBacktestAuditor(db=db).audit_pending(dias=int(dias_mlb))
                        with st.spinner("3/3 Calculando efectividad por tipo de pick..."):
                            EffectivenessCalculator(db=db).persist(dias=int(dias_mlb))
                        st.success("✅ Backtest REAL MLB completado.")
                        st.session_state["_mlb_real_bt_done"] = True
                    except Exception as _mbe:
                        st.error(f"Error en backtest real MLB: {_mbe}")
                        logger.exception(_mbe)

            # ── Backtest específico de CANDIDATOS A HR (vs HR reales) ──────────
            st.markdown("**💣 Backtest de candidatos a Home Run (precisión real):**")
            col_hr1, col_hr2 = st.columns([3, 1])
            with col_hr2:
                dias_hr = st.number_input("Días HR", 1, 20, 7, step=1, key="hr_bt_dias")
            with col_hr1:
                st.write("")
                if st.button("💣 EJECUTAR BACKTEST DE HR", use_container_width=True, key="hr_bt_run"):
                    barra_hr = st.progress(0, text="Cruzando candidatos vs HR reales...")
                    def _phr(i, txt):
                        barra_hr.progress(min(0.99, i / 150), text=txt[:60])
                    try:
                        from motors.hr_backtester import ejecutar_hr_backtest
                        ejecutar_hr_backtest(dias=int(dias_hr), progreso_cb=_phr)
                        barra_hr.empty()
                        st.success("✅ Backtest de HR completado.")
                    except Exception as _he:
                        barra_hr.empty()
                        st.error(f"Error: {_he}")

            hr_rep = cargar_json_safe(os.path.join("data", "hr_backtest_reporte.json"))
            if hr_rep:
                st.caption(f"Último: {hr_rep.get('timestamp','')[:16].replace('T',' ')} · "
                           f"{hr_rep.get('juegos',0)} juegos · precisión global {hr_rep.get('precision_global',0)}%")
                tramos = hr_rep.get("por_tramo_probabilidad", {})
                if tramos:
                    st.table([{"Probabilidad del motor": k, "Predichos": v["predichos"],
                               "Acertaron HR": v["aciertos"], "Precisión real": f"{v['precision']}%"}
                              for k, v in sorted(tramos.items(), reverse=True)])
                    st.caption("💡 Si el tramo '45%+' acierta mucho menos que 45%, el motor está inflando probabilidades. "
                               "Lo importante es el ORDEN: los de mayor probabilidad deben acertar más que los de menor.")

                # Candidatos a HR: predicción vs RESULTADO real (✅ pegó / ❌ no)
                det_hr = sorted(hr_rep.get("detalle", []),
                                key=lambda d: d.get("probabilidad", 0), reverse=True)
                if det_hr:
                    _nh = sum(1 for d in det_hr if d.get("pegó_hr"))
                    st.markdown("**💣 Candidatos a HR — predicción vs resultado real:**")
                    st.table([{"Fecha": d.get("fecha", ""), "Jugador": d["jugador"],
                               "Equipo": d["equipo"], "Prob. motor": f"{d['probabilidad']}%",
                               "Resultado": "✅ HR" if d.get("pegó_hr") else "❌"}
                              for d in det_hr[:30]])
                    st.caption(f"🧠 {_nh}/{len(det_hr)} candidatos conectaron HR — el resultado calibra el motor de HR "
                               "y el peso del mercado HOME RUN en los parlays.")

            # ── Backtest de MONEYLINE + OVER/UNDER (vs resultados reales) ──────
            st.markdown("**🏆 Backtest de Moneyline y Over/Under (precisión real):**")
            col_ml1, col_ml2 = st.columns([3, 1])
            with col_ml2:
                dias_ml = st.number_input("Días ML", 1, 30, 15, step=1, key="ml_bt_dias")
            with col_ml1:
                st.write("")
                if st.button("🏆 EJECUTAR BACKTEST ML + O/U", use_container_width=True, key="ml_bt_run"):
                    barra_ml = st.progress(0, text="Cruzando picks vs marcadores reales...")
                    def _pml(i, txt):
                        barra_ml.progress(min(0.99, i / 250), text=txt[:60])
                    try:
                        from motors.mlb_motor_backtester import ejecutar_mlb_backtest
                        ejecutar_mlb_backtest(dias=int(dias_ml), progreso_cb=_pml)
                        barra_ml.empty()
                        st.success("✅ Backtest ML + O/U completado (calibración guardada).")
                    except Exception as _mle:
                        barra_ml.empty()
                        st.error(f"Error: {_mle}")

            ml_rep = cargar_json_safe(os.path.join("data", "mlb_motor_backtest.json"))
            if ml_rep:
                mlb_data = ml_rep.get("moneyline", {})
                ou_data = ml_rep.get("over_under", {})
                st.caption(f"Último: {ml_rep.get('timestamp','')[:16].replace('T',' ')} · {ml_rep.get('juegos',0)} juegos")
                cmm1, cmm2 = st.columns(2)
                cmm1.metric("🏆 Moneyline (global)", f"{mlb_data.get('precision_global',0)}%")
                cmm2.metric(f"📊 O/U {ou_data.get('linea',8.5)}", f"{ou_data.get('tasa_over',0)}% OVER",
                            delta=f"sesgo {ou_data.get('sesgo','')}")
                tramos_ml = mlb_data.get("por_tramo_record", {})
                if tramos_ml:
                    st.table([{"Diferencia de récord": k, "Juegos": v["juegos"],
                               "Aciertos": v["aciertos"], "Precisión": f"{v['precision']}%"}
                              for k, v in sorted(tramos_ml.items(), reverse=True)])
                    st.caption("💡 El moneyline atina mucho más cuando hay gran diferencia de récord. "
                               "En juegos parejos es casi 50/50 — ahí conviene hándicap o evitar.")

            # Mostrar efectividad guardada
            efect_path = os.path.join("data", "backtesting_cache", "pick_type_performance.json")
            efect = cargar_json_safe(efect_path)
            if efect:
                filas = []
                for tipo, m in efect.items():
                    if isinstance(m, dict) and m.get("total", 0) > 0:
                        filas.append({
                            "Tipo": tipo,
                            "Picks": m.get("total", 0),
                            "Aciertos": m.get("hits", m.get("ganadas", 0)),
                            "Win Rate": f"{m.get('win_rate', 0):.1f}%",
                            "ROI": f"{m.get('roi', 0):+.1f}%",
                            "Clasif.": m.get("classification", m.get("clasificacion", "—")),
                        })
                if filas:
                    st.markdown("**Efectividad por tipo de pick (datos reales):**")
                    st.table(filas)
                else:
                    st.info("Aún no hay picks auditados. Genera picks en MLB y vuelve a ejecutar.")
            else:
                st.caption("Ejecuta el backtest para ver la efectividad real por tipo de apuesta.")

        st.markdown("---")

        if st.button("🔄 Ejecutar Backtest Completo (15 días)", use_container_width=True):
            with st.spinner("Ejecutando backtesting... Esto puede tardar varios minutos."):
                try:
                    import subprocess
                    # Usamos sys.executable para asegurar que se usa el intérprete correcto
                    result = subprocess.run(
                        [sys.executable, "run_backtest.py"],
                        capture_output=True, text=True, timeout=300, encoding='utf-8'
                    )
                    st.code((result.stdout or "") + "\n" + (result.stderr or ""), language="bash")
                    st.success("Backtest finalizado. El reporte se ha actualizado.")
                except Exception as e:
                    st.error(f"Error al ejecutar el backtest: {e}")

        reporte_path = os.path.join("data", "aprendizaje_backtest.json")
        reporte = cargar_json_safe(reporte_path)

        if reporte:
            st.markdown(f"**Última actualización:** `{reporte.get('timestamp', 'N/A')}`")
            
            metricas = reporte.get("metricas", {})
            global_metrics = metricas.get("GLOBAL", {})
            
            if global_metrics:
                st.markdown("---")
                st.subheader("🌎 Rendimiento Global")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Total Picks", global_metrics.get("total", 0))
                col2.metric("Win Rate", f"{global_metrics.get('win_rate', 0):.1f}%")
                col3.metric("Profit (Unidades)", f"{global_metrics.get('profit_u', 0):+.2f}u")
                col4.metric("ROI", f"{global_metrics.get('roi_pct', 0):.1f}%")

            st.markdown("---")
            st.subheader("📈 Rendimiento por Deporte")

            data_deportes = [
                {"Deporte": k, **v} for k, v in metricas.items() if k != "GLOBAL"
            ]

            # ── Fusionar la precisión de los backtests reales por deporte ──────
            # Asegura que NBA, UFC y FÚTBOL aparezcan aunque el reporte de
            # aprendizaje aún no los incluya.
            deportes_presentes = {d["Deporte"].upper() for d in data_deportes}
            extra = []

            def _fila_backtest(nombre, ruta, getter):
                rep = cargar_json_safe(ruta)
                if not rep:
                    return None
                try:
                    return {"Deporte": nombre, **getter(rep)}
                except Exception:
                    return None

            if "MLB" not in deportes_presentes:
                f = _fila_backtest("MLB", os.path.join("data", "mlb_backtest_real.json"),
                                   lambda r: {"Precisión ML": f"{r.get('moneyline',{}).get('precision_global',0)}%",
                                              "Juegos": r.get("juegos", 0)})
                if f: extra.append(f)
            if "NBA" not in deportes_presentes:
                f = _fila_backtest("NBA", os.path.join("data", "nba_backtest_real.json"),
                                   lambda r: {"Precisión ML": f"{r.get('moneyline',{}).get('precision_global',0)}%",
                                              "Juegos": r.get("juegos", 0)})
                if f: extra.append(f)
            if "UFC" not in deportes_presentes:
                f = _fila_backtest("UFC", os.path.join("data", "ufc_backtest_reporte.json"),
                                   lambda r: {"Precisión ML": f"{r.get('ganador',{}).get('precision',0)}%",
                                              "Juegos": r.get("muestras", 0)})
                if f: extra.append(f)
            if "SOCCER" not in deportes_presentes:
                f = _fila_backtest("SOCCER", os.path.join("data", "futbol_backtest_real.json"),
                                   lambda r: {"Precisión ML": f"{r.get('precision_global',0)}%",
                                              "Juegos": r.get("evaluados", 0)})
                if f: extra.append(f)

            if data_deportes:
                df_reporte = pd.DataFrame(data_deportes)
                st.dataframe(df_reporte, use_container_width=True)
            if extra:
                st.caption("Precisión de motores (desde backtests, si no están en la memoria de aprendizaje):")
                st.dataframe(pd.DataFrame(extra), use_container_width=True)
            if not data_deportes and not extra:
                st.info("Ejecuta los backtests reales (arriba) para ver el rendimiento por deporte.")
            
            pesos = reporte.get("pesos", {})
            if pesos:
                with st.expander("⚙️ Pesos de Motores Auto-Ajustados"):
                    st.json(pesos)
        else:
            st.info("No se ha encontrado un reporte de backtesting. Ejecuta el backtest para generar uno.")

    with tab6:
        if render_parlay_tab:
            try:
                render_parlay_tab()
            except Exception as _pe:
                st.error(f"Error en el generador de parlays: {_pe}")
                logger.exception(_pe)
        else:
            st.error("El generador de parlays no se pudo cargar. Reinicia la app por completo.")

if __name__ == "__main__":
    main()