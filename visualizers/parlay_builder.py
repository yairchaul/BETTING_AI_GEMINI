# -*- coding: utf-8 -*-
"""
PARLAY BUILDER — Tab de parlays cross-deporte.

Auto-analiza TODOS los juegos cargados (NBA, MLB, UFC, Fútbol) con los motores
reales, extrae el mejor pick de cada uno con su probabilidad, y arma parlays
escalonados por riesgo:
  • SEGURO  → solo mercados de alta probabilidad (ML / Hándicap / O-U / Decisión)
  • VALOR   → seguros + 1 prop de HR (mayor pago)
  • BOMBA   → varias props de HR (pago alto, prob baja)

No depende de que el usuario analice cada juego: ejecuta los motores al vuelo.
"""

import re
import streamlit as st
import logging
from datetime import datetime, timedelta

try:
    from motors.pick_memory import pick_memory
    from motors.parlay_brain import stats_por_tipo
except ImportError:
    pick_memory = None

logger = logging.getLogger(__name__)


def _mercado_pick(pick: str) -> str:
    """Infiere el mercado de un pick de fútbol para el parlay."""
    p = (pick or "").lower()
    if "over 1.5" in p: return "OVER 1.5"
    if "over 2.5" in p: return "OVER 2.5"
    if "over 3.5" in p: return "OVER 3.5"
    if "btts" in p or "ambos" in p: return "BTTS"
    if "under" in p: return "UNDER"
    if "local (" in p or "visitante (" in p: return "1X2"
    if "combinado" in p or "combo" in p: return "COMBINADO"
    return "1X2/Goles"


def _deporte_code(sport: str) -> str:
    """Normaliza '🏀 NBA' / '⚽ FÚTBOL' → código canónico (NBA/MLB/UFC/SOCCER)."""
    s = (sport or "").upper()
    if "FÚTBOL" in s or "FUTBOL" in s or "SOCCER" in s:
        return "SOCCER"
    if "NBA" in s:
        return "NBA"
    if "MLB" in s:
        return "MLB"
    if "UFC" in s:
        return "UFC"
    return s.split()[-1] if s else ""


def _fecha_iso(p):
    """Extrae 'YYYY-MM-DD' de un partido/combate, sea cual sea el campo de fecha."""
    if not isinstance(p, dict):
        return datetime.now().strftime("%Y-%m-%d")
    for campo in ("fecha_partido", "fecha", "date", "fecha_iso"):
        v = p.get(campo)
        if v:
            return str(v).replace("T", " ").strip()[:10]
    return datetime.now().strftime("%Y-%m-%d")  # sin fecha → asumir hoy


def _no_iniciado(p):
    """True solo si el evento AÚN NO empieza (descarta finalizados / en vivo / pasados)."""
    if not isinstance(p, dict):
        return True
    # Marcadores explícitos de estado
    if p.get("completado") or p.get("en_vivo"):
        return False
    estado = str(p.get("status", "")).lower()
    if any(x in estado for x in ("final", "ft", "post", "progress", "in progress",
                                 "en vivo", "live", "terminado", "finalizado")):
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
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
            try:
                dt = datetime.strptime(txt[:16] if len(txt) >= 16 else txt, fmt)
                # Margen de 10 min: si ya pasó la hora de inicio, descartar
                return dt > (datetime.now() - timedelta(minutes=10))
            except ValueError:
                continue
        break
    return True  # sin hora parseable → asumir que sigue disponible

# Cuotas por defecto cuando no hay momio del scraper (americano → decimal aprox)
CUOTA_DEFAULT = {
    "MONEYLINE": 1.90, "HÁNDICAP": 1.90, "TOTAL": 1.90,
    "MÉTODO": 2.50, "DISTANCIA": 1.90, "HR": 3.50, "1X2": 2.10, "BTTS": 1.85,
}


def _americano_a_decimal(ml):
    try:
        v = float(str(ml).replace('+', ''))
        if v == 0:
            return None
        return round(1 + (v / 100 if v > 0 else 100 / abs(v)), 2)
    except Exception:
        return None


def _decimal_a_americano(dec):
    """Cuota decimal → momio americano (str). 28.0 → '+2700', 1.5 → '-200'."""
    try:
        dec = float(dec)
        if dec <= 1.0:
            return "—"
        if dec >= 2.0:
            return f"+{round((dec - 1) * 100)}"
        return f"-{round(100 / (dec - 1))}"
    except Exception:
        return "—"


def _recolectar_picks_nba(ss, _es_del_dia, **kwargs):
    """Recolecta los picks de NBA."""
    pool = []
    try:
        from motors import analizar_nba_pro_v17
        for p in ss.get("nba_partidos", []) or []:
            if not _es_del_dia(p):
                continue
            r = analizar_nba_pro_v17(p)
            evento = f"{p.get('local','?')} vs {p.get('visitante','?')}"
            mejor = r.get("mejor_mercado", {})
            # Motor NBA v17 puede devolver solo recomendacion/confianza sin mejor_mercado
            if not mejor and r.get("recomendacion") and r.get("confianza", 0) >= 50:
                mejor = {
                    "mercado": "MONEYLINE",
                    "pick": r.get("recomendacion") or r.get("pick", ""),
                    "confianza": r.get("confianza", 55),
                }
            if mejor and mejor.get("pick"):
                pool.append({
                    "sport": "🏀 NBA", "evento": evento,
                    "mercado": mejor.get("mercado", "MONEYLINE"),
                    "pick": mejor.get("pick", ""),
                    "prob": mejor.get("confianza", 0),
                    "tipo": "SEGURO",
                    "cuota": CUOTA_DEFAULT.get(mejor.get("mercado", "").split()[0], 1.90),
                    "razon": f"Mejor mercado por confianza ({mejor.get('confianza', 0)}%)",
                })
            # Props de jugador (puntos/asistencias/triples) — la más confiable por equipo
            # Añadir racha para el parlay de rachas
            if mejor and mejor.get("pick"):
                is_local_pick = p.get('local', '') in mejor.get('pick', '')
                streak = p.get('local_streak', '') if is_local_pick else p.get('visitante_streak', '')
                if streak:
                    pool[-1]['streak'] = streak

            try:
                from motors.nba_props import obtener_props_partido
                pr = obtener_props_partido(p.get('local',''), p.get('visitante',''), db=ss.get('_db'))
                todas = pr.get("local", []) + pr.get("visitante", [])
                mejor_prop = max(todas, key=lambda x: x['confianza']) if todas else None
                if mejor_prop and mejor_prop['confianza'] >= 55:
                    pool.append({
                        "sport": "🏀 NBA", "evento": evento, "mercado": "PROP JUGADOR",
                        "pick": f"{mejor_prop['jugador']} {mejor_prop['pick']}",
                        "prob": mejor_prop['confianza'], "tipo": "VALOR", "cuota": 1.90,
                    })
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"Parlay NBA: {e}")

    return pool


_HR_CALIB = None


def _calibrar_prob_hr(raw):
    """Ajusta la probabilidad de HR a la tasa REAL de su tramo (backtest). El modelo
    INFLA el tope: el tramo 22%+ pega MENOS (6.7%) que el 15-21% bien calibrado (17.2%). Esta
    versión MEZCLA la probabilidad cruda del modelo con la tasa histórica, para que valores
    distintos dentro del mismo tramo (ej. 16% y 20%) tengan probabilidades calibradas
    distintas, haciéndolo más preciso. Muestras chicas → se mezclan con la tasa global."""
    global _HR_CALIB
    if _HR_CALIB is None:
        import os, json
        try:
            rep = json.load(open(os.path.join("data", "hr_backtest_reporte.json"), encoding="utf-8"))
            _HR_CALIB = (rep.get("por_tramo_probabilidad", {}) or {},
                         float(rep.get("precision_global", 12) or 12))
        except Exception:
            _HR_CALIB = ({}, 12.0)
    tramos, glob = _HR_CALIB
    try:
        raw = float(raw or 0)
    except (ValueError, TypeError):
        return raw
    for nombre, t in tramos.items():
        prec = t.get("precision")
        n = t.get("predichos", 0) or 0
        nm = str(nombre)
        lo = hi = None
        # El regex es más robusto para formatos como "15-20%" o "22%+"
        if "<" in nm:
            lo, hi = 0.0, float(re.sub(r"[^0-9.]", "", nm) or 15)
        elif "+" in nm:
            lo, hi = float(re.sub(r"[^0-9.]", "", nm) or 0), 100.0
        elif "-" in nm:
            partes = re.sub(r"[^0-9.\-]", "", nm).split("-")
            try:
                lo, hi = float(partes[0]), float(partes[1]) + 0.999
            except Exception:
                continue
        if lo is not None and prec is not None and lo <= raw <= hi:
            # Tasa histórica del tramo, suavizada con la tasa global si la muestra es chica.
            peso_hist = min(1.0, n / 40.0)
            tasa_hist_suavizada = prec * peso_hist + glob * (1 - peso_hist)
            # MEJORA: Mezclar la probabilidad cruda con la tasa histórica (50/50).
            # Esto hace que la calibración sea más granular y no un valor único por tramo.
            prob_mezclada = 0.5 * raw + 0.5 * tasa_hist_suavizada
            return round(prob_mezclada, 1)
    return round(min(raw, 18.0), 1)  # sin tramo: cap (el modelo infla el tope)


def _recolectar_picks_mlb(ss, _es_del_dia, **kwargs):
    """Recolecta los picks de MLB."""
    pool = []
    try:
        from motors import analizar_mlb_pro_v20
        for p in ss.get("mlb_partidos", []) or []:
            if not _es_del_dia(p):
                continue
            r = analizar_mlb_pro_v20(p, game_pk=p.get("game_pk"), predictor_hr=ss.get("predictor_hr"))
            evento = f"{p.get('visitante','?')} @ {p.get('local','?')}"
            odds = p.get("odds", {}) or {}
            ml = odds.get("moneyline", {}) if isinstance(odds.get("moneyline"), dict) else {}
            cuota_ml = _americano_a_decimal(ml.get("local") if r.get("pick") == p.get("local") else ml.get("visitante")) or 1.90

            # ── MEJOR LEG DEL JUEGO: el mercado de mayor probabilidad CALIBRADA ──
            # (el motor ya comparó ML, runline, O/U, K, HR y eligió el mejor por
            #  confianza × tasa real histórica). Solo ESA leg sube al parlay seguro.
            mejor = r.get("mejor_apuesta") or {}
            _etiqueta = {"MONEYLINE": "MONEYLINE", "HANDICAP": "RUNLINE", "TOTAL": "TOTAL",
                         "PONCHES": "PONCHES (K)", "TOTAL_BASES": "TOTAL BASES", "HOME_RUN": "HOME RUN"}
            _cuota = {"MONEYLINE": cuota_ml, "HANDICAP": 1.80, "TOTAL": 1.90,
                      "PONCHES": 1.85, "TOTAL_BASES": 1.95, "HOME_RUN": 3.50}
            if mejor.get("pick") and mejor.get("mercado") != "HOME_RUN":
                mk = mejor["mercado"]
                pool.append({
                    "sport": "⚾ MLB", "evento": evento,
                    "mercado": _etiqueta.get(mk, mk), "pick": mejor["pick"],
                    "prob": mejor.get("confianza_ajustada", mejor.get("confianza", 0)),
                    "tipo": "SEGURO",
                    "cuota": _cuota.get(mk, 1.90),
                    "razon": mejor.get("razon"),
                    "is_adjusted": True,  # La confianza ya viene ajustada por el motor MLB
                })
                # Añadir racha para el parlay de rachas
                is_local_pick = p.get('local', '') in mejor.get('pick', '')
                streak = p.get('local_streak', '') if is_local_pick else p.get('visitante_streak', '')
                if streak:
                    pool[-1]['streak'] = streak

            # HR candidates (props de mayor pago) — para los parlays BOMBA/SLUGGER.
            # SOLO si el bateador está en la alineación del día (oficial o proyectada).
            for hr in r.get("hr_candidates", []):
                if hr.get("en_lineup") is False:
                    continue
                prob_modelo = hr.get("probabilidad", hr.get("prob", 0))
                prob_hr = _calibrar_prob_hr(prob_modelo)   # tasa REAL del tramo (no la inflada)
                pool.append({
                    "sport": "⚾ MLB", "evento": evento, "mercado": "HOME RUN",
                    "pick": f"{hr.get('jugador', hr.get('nombre','?'))} pega HR",
                    "prob": prob_hr, "prob_modelo": prob_modelo,
                    "tipo": "BOMBA", "cuota": 3.50,
                })
    except Exception as e:
        logger.warning(f"Parlay MLB: {e}")
    return pool


def _recolectar_picks_ufc(ss, _es_del_dia, **kwargs):
    """Recolecta los picks de UFC."""
    pool = []
    _ufc_analyzer = ss.get("ufc_analyzer")
    combates = ss.get("ufc_combates", []) or []
    analisis_cache = ss.get("analisis_ufc", {}) or {}

    for idx, c in enumerate(combates):
        if not _es_del_dia(c):
            continue

        res = analisis_cache.get(idx)
        if not res and _ufc_analyzer:
            try:
                p1 = c.get("peleador1", {})
                p2 = c.get("peleador2", {})
                res = _ufc_analyzer.analizar_combate(p1, p2)
            except Exception as _ue:
                logger.debug(f"UFC on-the-fly para {c.get('evento')}: {_ue}")

        if not res:
            continue

        evento_ufc = f"{c.get('peleador1',{}).get('nombre','?')} vs {c.get('peleador2',{}).get('nombre','?')}"

        # Pick principal (ganador)
        pick_text = res.get("recomendacion") or res.get("ganador")
        conf = res.get("confianza", 0)
        if pick_text and conf >= 55:
            pool.append({
                "sport": "🥊 UFC", "evento": evento_ufc,
                "mercado": "GANADOR", "pick": pick_text,
                "prob": conf, "tipo": "SEGURO",
                "cuota": CUOTA_DEFAULT.get("MONEYLINE", 2.0),
                "razon": res.get("razon"),
            })

        # Total de rounds más probable
        rt = sorted(res.get("rounds_totales", []), key=lambda x: x.get("confianza", 0), reverse=True)
        if rt and rt[0].get("confianza", 0) >= 58:
            pool.append({
                "sport": "🥊 UFC", "evento": evento_ufc, "mercado": "ROUNDS",
                "pick": rt[0].get("etiqueta", ""), "prob": rt[0].get("confianza", 0),
                "tipo": "VALOR", "cuota": 1.85,
                "razon": f"Probabilidad Monte Carlo: {rt[0].get('confianza', 0)}%",
            })

        # Gana por KO/TKO o Sumisión
        mp = res.get("metodo_probs", {})
        ganador = res.get("ganador", "")
        if ganador:
            for metodo, prob_metodo, cuota_metodo in [("KO/TKO", mp.get("KO/TKO", 0), 2.60), ("Sumisión", mp.get("Sumisión", 0), 3.20)]:
                if prob_metodo >= 40:
                    pool.append({
                        "sport": "🥊 UFC", "evento": evento_ufc, "mercado": f"GANA POR {metodo}",
                        "pick": f"{ganador} gana por {metodo}",
                        "prob": prob_metodo, "tipo": "BOMBA", "cuota": cuota_metodo,
                        "razon": f"Probabilidad de método: {prob_metodo}%",
                    })
    return pool


def _recolectar_picks_futbol(ss, _es_del_dia, **kwargs):
    """Recolecta los picks de Fútbol."""
    pool = []
    # Cuotas REALES: The Odds API (moneyline) como fuente principal + Caliente
    # como respaldo. Para OVER/UNDER/BTTS se usan cuotas de mercado típicas.
    cal_fut = kwargs.get("cal_fut", {})
    odds_api_ml = kwargs.get("odds_api_ml", {})

    _CUOTA_MKT = {"over 1.5 ht": 2.20, "over 1.5": 1.25, "over 2.5": 1.95,
                  "over 3.5": 3.20, "under 2.5": 1.70, "btts": 1.85, "ambos": 1.85}

    def _norm_eq(s):
        return re.sub(r"[^a-z ]", "", (s or "").lower()).strip()

    def _cuota_real_futbol(pick, home, away):
        """Cuota decimal REAL/mercado para el pick."""
        pl = pick.lower()
        # Moneyline → cuota real de The Odds API (o Caliente)
        if "local" in pl or _norm_eq(home)[:5] in pl or f"gana {home.lower()}" in pl:
            c = odds_api_ml.get(home.lower())
            if c:
                return c
        if "visitante" in pl or _norm_eq(away)[:5] in pl:
            c = odds_api_ml.get(away.lower())
            if c:
                return c
        # Mercados de goles → cuota de mercado típica
        for k, v in _CUOTA_MKT.items():
            if k in pl:
                return v
        return None

    try:
        from motors.futbol_analyzer_jerarquico import analizar_futbol_jerarquico
        for liga, partidos in (ss.get("futbol_partidos", {}) or {}).items():
            for p in partidos or []:
                if not _es_del_dia(p):
                    continue
                home_f = p.get("home") or p.get("local", "")
                away_f = p.get("away") or p.get("visitante", "")
                r = analizar_futbol_jerarquico(
                    home_f, away_f,
                    es_torneo=p.get("es_torneo", False), fase=p.get("fase", ""),
                    liga=liga,
                    gemini_client=ss.get("gemini"),
                )
                pick = r.get("pick", "")
                if not pick or "revisar" in pick.lower():
                    continue
                evento_f = f"{home_f or '?'} vs {away_f or '?'}"
                # Determinar racha para el parlay de rachas
                streak = ""
                if "local" in pick.lower() or home_f.lower() in pick.lower():
                    streak = r.get("streak_local", "")
                elif "visitante" in pick.lower() or away_f.lower() in pick.lower():
                    streak = r.get("streak_visitante", "")

                # Construir razón a partir de las notas del motor
                notas = [
                    r.get("h2h_nota"),
                    r.get("wc_nota"),
                    r.get("liga_nota"),
                    r.get("ajuste_dc"),
                    r.get("nota_ia")
                ]
                razon_fut = " · ".join(filter(None, notas))
                cuota_real = _cuota_real_futbol(pick, home_f, away_f)
                picks_ya_en_pool = {pick}  # deduplicar por partido
                pool.append({
                    "sport": "⚽ FÚTBOL", "evento": evento_f,
                    "mercado": "1X2/Goles", "pick": pick,
                    "prob": r.get("confianza", 0),
                    "streak": streak,
                    "tipo": "SEGURO" if r.get("confianza", 0) >= 55 else "VALOR",
                    "cuota": cuota_real or 1.90,
                    "cuota_real": bool(cuota_real),
                    "razon": razon_fut,
                    "es_torneo": p.get("es_torneo", False),
                })
                # Picks múltiples: agregar CADA market que califica independientemente
                for pm in r.get("picks_multiples", []):
                    pm_pick = pm.get("pick", "")
                    if not pm_pick or pm_pick in picks_ya_en_pool:
                        continue
                    picks_ya_en_pool.add(pm_pick)
                    pm_cuota = _cuota_real_futbol(pm_pick, home_f, away_f) or 1.85
                    pool.append({
                        "sport": "⚽ FÚTBOL", "evento": evento_f,
                        "mercado": _mercado_pick(pm_pick), "pick": pm_pick,
                        "prob": pm.get("confianza", 0),
                        "tipo": "SEGURO" if pm.get("confianza", 0) >= 55 else "VALOR",
                        "cuota": pm_cuota,
                        "razon": pm.get("razon"), # Asumir que puede tener razón
                        "es_torneo": p.get("es_torneo", False),
                    })
                for op in r.get("todas_opciones", []):
                    if op.get("combo") and op.get("confianza", 0) >= 38 and op.get("pick", "") not in picks_ya_en_pool:
                        pool.append({
                            "sport": "⚽ FÚTBOL", "evento": evento_f,
                            "mercado": "COMBINADO", "pick": op["pick"],
                            "prob": op["confianza"], "tipo": "VALOR",
                            "cuota": op.get("cuota", 2.4),
                            "razon": op.get("razon"),
                            "es_torneo": p.get("es_torneo", False),
                        })
    except Exception as e:
        logger.warning(f"Parlay fútbol: {e}")
    return pool


def _recolectar_picks(dia_filtro=None):
    """
    Corre los motores sobre todo lo cargado y devuelve un pool de picks.
    Llama a sub-funciones por deporte para mayor legibilidad.

    dia_filtro: 'YYYY-MM-DD' para quedarte solo con los juegos de ese día.
    """
    ss = st.session_state
    pool = []

    def _es_del_dia(p):
        if not _no_iniciado(p):
            return False
        return (dia_filtro is None) or (_fecha_iso(p) == dia_filtro)

    # --- Pre-fetch de datos compartidos (cuotas) para optimizar ---
    # Cuotas de Fútbol
    cal_fut = {}
    odds_api_ml = {}
    try:
        from scrapers.odds_scraper import get_soccer_odds_caliente
        cal_fut = get_soccer_odds_caliente() or {}
    except Exception as _ce:
        logger.warning(f"Caliente fútbol odds: {_ce}")
    try:
        from scrapers.odds_api import obtener_odds_futbol
        def _am2dec(am):
            try:
                a = int(str(am).replace("+", ""))
                return round(1 + (a / 100.0 if a > 0 else 100.0 / abs(a)), 2)
            except Exception:
                return None
        for o in obtener_odds_futbol() or []:
            if o.get("home_ml"):
                odds_api_ml[(o.get("home") or "").lower()] = _am2dec(o["home_ml"])
            if o.get("away_ml"):
                odds_api_ml[(o.get("away") or "").lower()] = _am2dec(o["away_ml"])
    except Exception as _oe:
        logger.warning(f"odds_api fútbol: {_oe}")

    # Llama a cada recolector, pasando los datos pre-cargados si es necesario
    pool.extend(_recolectar_picks_nba(ss, _es_del_dia))
    pool.extend(_recolectar_picks_mlb(ss, _es_del_dia))
    pool.extend(_recolectar_picks_ufc(ss, _es_del_dia))
    pool.extend(_recolectar_picks_futbol(ss, _es_del_dia, cal_fut=cal_fut, odds_api_ml=odds_api_ml))

    # ── FASE 3 (Evolución): ponderar cada pick por su rendimiento histórico ──
    # El selector se vuelve más inteligente: penaliza mercados que históricamente
    # fallan y premia los que aciertan (factor_confianza desde la memoria).
    if pick_memory is not None:
        for pk in pool:
            if pk.get("is_adjusted"):
                continue
            try:
                pk["prob_base"] = pk["prob"]
                factor = pick_memory.factor_confianza(_deporte_code(pk.get("sport", "")), pk.get("mercado", ""))
                pk["factor_hist"] = factor
                # Cap de realismo también en la prob MOSTRADA: nada de "99%".
                pk["prob"] = max(1, min(90, round(pk["prob"] * factor, 1)))
            except Exception:
                pass
        # Excluir del parlay los mercados PROBADOS perdedores (factor ≤0.6 = win
        # rate <40% con muestra suficiente: HR 22%, total bases 32%). Bajar la prob
        # no basta — en un parlay una sola pata mala lo tumba. Los de factor 1.0
        # (sin datos aún) se mantienen. Siguen disponibles como pick suelto.
        n0 = len(pool)
        pool = [pk for pk in pool if pk.get("factor_hist", 1.0) > 0.6]
        if len(pool) < n0:
            logger.info(f"Parlay: {n0 - len(pool)} picks excluidos por mercado probado perdedor (factor ≤0.6)")

    return pool


_CALIB_MERCADOS = None


def _rate_real_mercado(sport, mercado):
    """Tasa de acierto REAL del mercado (aprendizaje_mercados.json) o None."""
    global _CALIB_MERCADOS
    if _CALIB_MERCADOS is None:
        import os, json
        try:
            with open(os.path.join("data", "aprendizaje_mercados.json"), encoding="utf-8") as f:
                _CALIB_MERCADOS = json.load(f).get("por_mercado", {})
        except Exception:
            _CALIB_MERCADOS = {}
    s = (sport or "").upper()
    dep = ("MLB" if "MLB" in s else "SOCCER" if "FÚTBOL" in s or "FUTBOL" in s
           else "NBA" if "NBA" in s else "UFC" if "UFC" in s else "")
    return _CALIB_MERCADOS.get(f"{dep} · {mercado}", {}).get("win_rate")


REALISMO_CAP = 90.0   # ninguna leg vale >90%: no existe la apuesta "99% segura"
PRIOR_SIN_CALIBRAR = 55.0  # prior conservador para mercados sin tasa real (UFC, nuevos)


def _prob_realista_leg(l):
    """Probabilidad de la leg con DOS correcciones contra la sobreconfianza que
    nos tiene en 0/27:
      • Si hay tasa real del mercado (aprendizaje) → 60% real + 40% modelo.
      • Si NO la hay (UFC, mercados sin muestra) → el modelo corre CALIENTE, así
        que lo descontamos hacia un prior conservador (70% modelo + 30% prior).
      • Cap duro: ninguna leg supera el 90%.
    """
    mk = (l.get("mercado") or "").upper()
    real = _rate_real_mercado(l.get("sport", ""), l.get("mercado", ""))
    if real is not None:
        p = l["prob"] * 0.4 + real * 0.6
    elif "RUNLINE" in mk or "HAND" in mk:
        # El run line YA viene calibrado a la tasa real del backtest en el motor
        # (_runline_pick). No re-encogerlo hacia el prior: se pasa tal cual.
        p = l["prob"]
    else:
        p = l["prob"] * 0.7 + PRIOR_SIN_CALIBRAR * 0.3
    return min(p, REALISMO_CAP)


def _armar_parlay(legs):
    """Calcula prob combinada, cuota y EV. La probabilidad de cada leg se
    CALIBRA con la tasa real del mercado (aprendizaje) y se acota a un techo
    realista, para que la prob combinada refleje lo que de verdad acierta."""
    prob = 1.0
    cuota = 1.0
    for l in legs:
        p = _prob_realista_leg(l)
        prob *= max(0.01, p / 100.0)
        cuota *= l.get("cuota", 1.9)
    ev = prob * cuota - 1.0
    return {
        "legs": legs,
        "prob": round(prob * 100, 2),
        "cuota": round(cuota, 2),
        "ev_pct": round(ev * 100, 1),
    }


def _guardar_parlay(titulo, parlay):
    """Guarda cada parlay GENERADO en data/parlay_history.json (idempotente por
    día + legs) para que el cerebro aprenda qué estructuras de parlay ganan."""
    import os, json
    from datetime import datetime
    ruta = os.path.join("data", "parlay_history.json")
    try:
        hist = json.load(open(ruta, encoding="utf-8")) if os.path.exists(ruta) else []
    except Exception:
        hist = []
    fecha = datetime.now().strftime("%Y-%m-%d")
    firma = "|".join(sorted(f"{l['sport']}::{l['pick']}" for l in parlay.get("legs", [])))
    if any(h.get("fecha") == fecha and h.get("firma") == firma for h in hist):
        return  # ya guardado hoy
    hist.append({
        "id": f"par_{datetime.now().strftime('%Y%m%d%H%M%S')}_{abs(hash(firma)) % 10000}",
        "fecha": fecha, "tipo": titulo, "firma": firma,
        "prob": parlay.get("prob"), "cuota": parlay.get("cuota"),
        "ev_pct": parlay.get("ev_pct"), "n_legs": len(parlay.get("legs", [])),
        "legs": [{"sport": l["sport"], "pick": l["pick"], "mercado": l.get("mercado", ""),
                  "evento": l.get("evento", ""), "prob": l.get("prob")} for l in parlay.get("legs", [])],
        "estado": "pendiente",   # se resuelve cuando se resuelvan sus legs
    })
    try:
        os.makedirs("data", exist_ok=True)
        json.dump(hist[-500:], open(ruta, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    except Exception:
        pass

def _parlay_de_ia(ss, dia_filtro, n_legs=3):
    """
    Corre los motores de IA sobre todos los juegos del día y arma un parlay
    con los mejores picks de IA.
    """
    from utils.analista_total import AnalistaTotal
    from motors import analizar_mlb_pro_v20, analizar_nba_pro_v17
    from motors.futbol_analyzer_jerarquico import analizar_futbol_jerarquico
    from analyzers.ufc_analyzer import UFCAnalyzer

    # 1. Instanciar el analizador de IA
    modelo_ia = ss.get("selected_ia_model", "Heurístico")
    if modelo_ia == "Heurístico":
        return None # No hay IA seleccionada

    analista = AnalistaTotal(
        gemini_client=ss.get("gemini"),
        groq_client=ss.get("groq"),
        deepseek_client=ss.get("deepseek"),
        claude_client=ss.get("claude"),
        new_ai_client=ss.get("new_ai"),
        selected_model=modelo_ia,
    )

    ia_picks = []
    
    def _es_del_dia(p):
        return (dia_filtro is None) or (_fecha_iso(p) == dia_filtro)

    # 2. Analizar cada deporte
    # MLB
    for p in ss.get("mlb_partidos", []):
        if not _es_del_dia(p): continue
        try:
            res_h = analizar_mlb_pro_v20(p, game_pk=p.get('game_pk'), predictor_hr=ss.get('predictor_hr'))
            res_ia = analista.analizar_mlb(p, res_h)
            if res_ia and res_ia.get('pick') and res_ia.get('confianza', 0) >= 55:
                ia_picks.append({
                    "sport": "⚾ MLB", "evento": f"{p.get('visitante','?')} @ {p.get('local','?')}",
                    "mercado": res_ia.get('mercado', 'IA Pick'), "pick": res_ia.get('pick'),
                    "prob": res_ia.get('confianza'), "tipo": "IA", "cuota": res_ia.get('cuota', 1.9),
                    "razon": res_ia.get('razon')
                })
        except Exception as e:
            logger.debug(f"IA Parlay MLB: {e}")

    # NBA
    for p in ss.get("nba_partidos", []):
        if not _es_del_dia(p): continue
        try:
            res_h = analizar_nba_pro_v17(p)
            res_ia = analista.analizar_nba(p, res_h)
            if res_ia and res_ia.get('pick') and res_ia.get('confianza', 0) >= 55:
                ia_picks.append({
                    "sport": "🏀 NBA", "evento": f"{p.get('visitante','?')} @ {p.get('local','?')}",
                    "mercado": res_ia.get('mercado', 'IA Pick'), "pick": res_ia.get('pick'),
                    "prob": res_ia.get('confianza'), "tipo": "IA", "cuota": res_ia.get('cuota', 1.9),
                    "razon": res_ia.get('razon')
                })
        except Exception as e:
            logger.debug(f"IA Parlay NBA: {e}")

    # Fútbol
    for liga, partidos in (ss.get("futbol_partidos", {}) or {}).items():
        for p in partidos or []:
            if not _es_del_dia(p): continue
            try:
                home_f = p.get("home") or p.get("local", "")
                away_f = p.get("away") or p.get("visitante", "")
                res_h = analizar_futbol_jerarquico(
                    home_f, away_f, es_torneo=p.get("es_torneo", False),
                    fase=p.get("fase", ""), liga=liga, gemini_client=None
                )
                res_ia = analista.analizar_futbol(p, res_h)
                if res_ia and res_ia.get('pick') and res_ia.get('confianza', 0) >= 55:
                    ia_picks.append({
                        "sport": "⚽ FÚTBOL", "evento": f"{home_f or '?'} vs {away_f or '?'}",
                        "mercado": res_ia.get('mercado', 'IA Pick'), "pick": res_ia.get('pick'),
                        "prob": res_ia.get('confianza'), "tipo": "IA", "cuota": res_ia.get('cuota', 1.9),
                        "razon": res_ia.get('razon')
                    })
            except Exception as e:
                logger.debug(f"IA Parlay Fútbol: {e}")

    # UFC
    ufc_analyzer = UFCAnalyzer()
    for c in ss.get("ufc_combates", []):
        if not _es_del_dia(c): continue
        try:
            p1, p2 = c.get('peleador1', {}), c.get('peleador2', {})
            res_h = ufc_analyzer.analizar_combate(p1, p2, c)
            res_ia = analista.analizar_ufc(c, res_h)
            if res_ia and res_ia.get('pick') and res_ia.get('confianza', 0) >= 55:
                 ia_picks.append({
                    "sport": "🥊 UFC", "evento": f"{p1.get('nombre','?')} vs {p2.get('nombre','?')}",
                    "mercado": res_ia.get('mercado', 'IA Pick'), "pick": res_ia.get('pick'),
                    "prob": res_ia.get('confianza'), "tipo": "IA", "cuota": res_ia.get('cuota', 1.9),
                    "razon": res_ia.get('razon')
                })
        except Exception as e:
            logger.debug(f"IA Parlay UFC: {e}")

    if len(ia_picks) < 2:
        return None

    # 3. Seleccionar los mejores y armar parlay
    ia_picks.sort(key=lambda x: x["prob"], reverse=True)
    legs_ia = []
    eventos_vistos = set()
    for pick in ia_picks:
        if len(legs_ia) >= n_legs: break
        if pick["evento"] not in eventos_vistos:
            legs_ia.append(pick)
            eventos_vistos.add(pick["evento"])
    return _armar_parlay(legs_ia) if len(legs_ia) >= 2 else None

def _parlay_moneyline_seguro(pool, n_legs=3):
    """
    Crea un parlay con los Money Lines más seguros del día.
    """
    # Filtrar por picks de Moneyline/1X2 con alta confianza
    candidatos = [
        p for p in pool
        if p.get("mercado") in ("MONEYLINE", "1X2", "1X2/Goles", "GANADOR")
        and p.get("prob", 0) >= 62
    ]

    if not candidatos:
        return None

    # Ordenar por probabilidad descendente
    candidatos.sort(key=lambda x: x["prob"], reverse=True)

    # Seleccionar los mejores N de eventos distintos
    legs_seguras = []
    eventos_vistos = set()
    for p in candidatos:
        if len(legs_seguras) >= n_legs:
            break
        if p["evento"] not in eventos_vistos:
            legs_seguras.append(p)
            eventos_vistos.add(p["evento"])

    if len(legs_seguras) < 2:
        return None

    return _armar_parlay(legs_seguras)

def _parlay_underdog(pool, n_legs=3):
    """
    Crea un parlay de 'underdogs' con los picks de cuota más alta
    que aún mantienen una probabilidad razonable.
    """
    # Filtrar por probabilidad mínima y cuota mínima para ser underdog
    candidatos = [
        p for p in pool
        if p.get("prob", 0) >= 35 and p.get("cuota", 0) >= 2.1 # Cuota > +110
    ]

    if not candidatos:
        return None

    # Ordenar por cuota descendente
    candidatos.sort(key=lambda x: x["cuota"], reverse=True)

    # Seleccionar los mejores N de eventos distintos
    legs_underdog = []
    eventos_vistos = set()
    for p in candidatos:
        if len(legs_underdog) >= n_legs:
            break
        if p["evento"] not in eventos_vistos:
            legs_underdog.append(p)
            eventos_vistos.add(p["evento"])

    if len(legs_underdog) < 2:
        return None

    return _armar_parlay(legs_underdog)

def _parlay_de_rachas(pool, n_legs=3):
    """
    Crea un parlay de 'momentum' con los equipos favoritos (Moneyline)
    con mayor probabilidad de victoria del día.
    """
    # Filtrar por picks de Moneyline/1X2 con alta confianza
    candidatos = [
        p for p in pool
        if p.get("mercado") in ("MONEYLINE", "1X2", "1X2/Goles", "GANADOR")
        and p.get("prob", 0) >= 65
    ]

    if not candidatos:
        return None

    # Ordenar por probabilidad descendente
    candidatos.sort(key=lambda x: x["prob"], reverse=True)

    # Seleccionar los mejores N de eventos distintos
    legs_rachas = []
    eventos_vistos = set()
    for p in candidatos:
        if len(legs_rachas) >= n_legs:
            break
        if p["evento"] not in eventos_vistos:
            legs_rachas.append(p)
            eventos_vistos.add(p["evento"])

    if len(legs_rachas) < 2:
        return None

    return _armar_parlay(legs_rachas)

def _parlay_mundial(pool, n_legs=3):
    """
    Crea un parlay con los mejores picks de la Copa del Mundo
    con confianza superior al 60%.
    """
    # Filtrar por picks de fútbol de torneo con alta confianza
    candidatos = [
        p for p in pool
        if p.get("es_torneo")
        and "FÚTBOL" in p.get("sport", "")
        and p.get("prob", 0) >= 60
    ]

    if not candidatos:
        return None

    # Ordenar por probabilidad descendente
    candidatos.sort(key=lambda x: x["prob"], reverse=True)

    # Seleccionar los mejores N de eventos distintos
    legs_mundial = []
    eventos_vistos = set()
    for p in candidatos:
        if len(legs_mundial) >= n_legs:
            break
        if p["evento"] not in eventos_vistos:
            legs_mundial.append(p)
            eventos_vistos.add(p["evento"])

    if len(legs_mundial) < 2:
        return None

    return _armar_parlay(legs_mundial)

def _get_historical_performance_html(titulo: str) -> str:
    """
    Consulta el rendimiento histórico de un tipo de parlay y devuelve
    una cadena HTML para mostrar en la tarjeta.
    """
    try:
        from motors.parlay_brain import stats_de_tipo
        _h = stats_de_tipo(titulo)
        if _h and _h.get("total", 0) >= 2:
            _wc = "#22c55e" if _h["win_rate"] >= 50 else "#ef4444"
            return (f"  ·  <span style='color:{_wc}'>📊 histórico: {_h['win_rate']}% "
                    f"({_h['ganados']}/{_h['total']}) · ROI {_h['roi']:+.0f}%</span>")
    except Exception:
        pass
    return ""


# Parlays SECUNDARIOS: redundantes con el Óptimo/Valor+EV o de pura lotería.
# En "Modo enfocado" se ocultan (pero SE SIGUEN guardando para el aprendizaje).
# Se mantienen los distintos y útiles: Óptimo, Valor (+EV), Solo Fútbol, Mundial,
# HR + Fútbol, IA y la Escalera.
_PARLAYS_SECUNDARIOS = (
    "DOBLE SEGURO", "PARLAY SEGURO", "PARLAY VALOR", "BOMBA",
    "SLUGGER", "GIGANTE", "MÁXIMO PAGO", "RACHAS", "UNDERDOG", "MONEYLINE SEGURO", "PARLAY DE IA",
)


def _tarjeta_parlay(titulo, color, descripcion, parlay):
    _guardar_parlay(titulo, parlay)   # registra el parlay generado para aprender de él

    # Poda: en modo enfocado, ocultar los parlays secundarios (ya quedaron
    # guardados arriba para el aprendizaje). "DE VALOR (+EV)" NO se oculta:
    # contiene "DE VALOR", no "PARLAY VALOR".
    if st.session_state.get("_parlay_focus", True) and any(
            s in titulo.upper() for s in _PARLAYS_SECUNDARIOS):
        return

    # Mapeo de títulos a íconos para una UI más clara
    ICONOS_PARLAY = {
        "SEGURO": "🟢",
        "VALOR": "🟡",
        "BOMBA": "🔴",
        "RACHAS": "🔥",
        "ÓPTIMO": "🎯",
        "DOBLE SEGURO": "🔐",
        "GIGANTE": "🟣",
        "MÁXIMO PAGO": "💎",
        "VALOR (+EV)": "💎",
        "SLUGGER": "⚡",
        "HR + FÚTBOL": "🎯",
        "MEJOR RACHA": "📈",
        "MUNDIAL": "🏆",
        "UNDERDOG": "🐺",
        "MONEYLINE SEGURO": "🛡️",
        "PARLAY DE IA": "🤖",
    }
    icono = next((icon for key, icon in ICONOS_PARLAY.items() if key in titulo.upper()), "🎰")

    momio = _decimal_a_americano(parlay['cuota'])
    ganancia = round((parlay['cuota'] - 1) * 100)   # ganancia por cada $100 apostados
    # Rendimiento HISTÓRICO de este tipo de parlay (el cerebro aprendiendo)
    hist_html = _get_historical_performance_html(titulo)
    st.markdown(
        f"<div style='background:#1e293b;border-left:5px solid {color};border-radius:10px;padding:14px;margin-bottom:6px'>"
        f"<div style='color:{color};font-weight:800;font-size:1.05rem'>{icono} {titulo}</div>"
        f"<div style='color:#94a3b8;font-size:0.8rem;margin-bottom:8px'>{descripcion}</div>"
        f"<div style='display:flex;gap:18px;flex-wrap:wrap'>"
        f"<span style='color:#fff'>Momio: <b style='color:#fbbf24;font-size:1.15rem'>{momio}</b></span>"
        f"<span style='color:#fff'>Cuota: <b style='color:#fbbf24'>{parlay['cuota']:.2f}x</b></span>"
        f"<span style='color:#fff'>Prob. combinada: <b style='color:{color}'>{parlay['prob']}%</b></span>"
        f"<span style='color:#fff'>EV: <b style='color:{'#22c55e' if parlay['ev_pct']>=0 else '#ef4444'}'>{parlay['ev_pct']:+.1f}%</b></span>"
        f"</div>"
        f"<div style='color:#64748b;font-size:0.8rem;margin-top:6px'>💵 $100 → <b style='color:#22c55e'>${ganancia:,}</b> de ganancia ({len(parlay['legs'])} legs){hist_html}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )
    for l in parlay["legs"]:
        _c = l.get("cuota", 1.9) or 1.9
        _impl = 100.0 / _c if _c > 0 else 100.0
        _edge = l["prob"] - _impl
        _ecol = "#22c55e" if _edge >= 0 else "#ef4444"
        _razon_html = f"title='Razón: {l['razon']}'" if l.get("razon") else ""
        st.markdown(
            f"<div style='background:#0f172a;border-radius:6px;padding:6px 12px;margin:3px 0' {_razon_html}>"
            f"{l['sport']} · <b>{l['pick']}</b> "
            f"<span style='color:#64748b'>({l['mercado']} · {l['evento']})</span> "
            f"<span style='float:right'>"
            f"<span style='color:{_ecol};font-size:0.78rem' title='Valor = prob. modelo − prob. implícita del momio'>valor {_edge:+.0f}%</span>  "
            f"<span style='color:#22c55e;font-weight:700'>{l['prob']:.0f}%</span></span></div>",
            unsafe_allow_html=True,
        )


def _sluggers_del_dia(top_n: int = 5, equipos_hoy: set = None) -> list:
    """
    Lee hr_backtest_reporte.json y devuelve los sluggers con más HRs recientes
    como legs de parlay, con probabilidad calibrada por la tasa real del backtest.
    """
    import os, json
    from collections import defaultdict

    ruta = os.path.join("data", "hr_backtest_reporte.json")
    if not os.path.exists(ruta):
        return []
    try:
        with open(ruta, encoding='utf-8') as f:
            rep = json.load(f)
    except Exception:
        return []

    det = rep.get('detalle', [])
    tramos = rep.get('por_tramo_probabilidad', {})
    prec_global = rep.get('precision_global', 13.6)

    # La key 'pegó_hr' tiene acento en UTF-8 — buscar dinámicamente
    pego_key = None
    if det:
        for k in det[0]:
            if k.endswith('_hr') and 'prob' not in k:
                pego_key = k
                break

    stats = defaultdict(lambda: {'hits': 0, 'probs': [], 'equipo': ''})
    for d in det:
        pego = bool(d.get(pego_key, False)) if pego_key else False
        if pego:
            j = d.get('jugador', '')
            if not j:
                continue
            stats[j]['hits'] += 1
            stats[j]['probs'].append(float(d.get('probabilidad', 15)))
            stats[j]['equipo'] = d.get('equipo', '')

    if not stats:
        return []

    # Precisión calibrada por tramo de probabilidad (tasa real del backtest)
    def _prec_tramo(avg_prob):
        for nombre, t in sorted(tramos.items(), key=lambda x: x[0], reverse=True):
            prec = t.get('precision', prec_global)
            # el tramo "15%+" cubre prob >= 15, "12-14%" para 12-14, etc.
            if '+' in nombre:
                lim = float(nombre.replace('%+', '').replace('%', ''))
                if avg_prob >= lim:
                    return prec
            elif '-' in nombre and '%' in nombre:
                partes = nombre.replace('%', '').split('-')
                try:
                    lo, hi = float(partes[0]), float(partes[1])
                    if lo <= avg_prob <= hi:
                        return prec
                except ValueError:
                    pass
        return prec_global

    # Intentar cargar factor Statcast (barrel rate real) para cada jugador
    try:
        from motors.pybaseball_hr import factor_hr_statcast
        _statcast_ok = True
    except Exception:
        _statcast_ok = False

    ranking = []
    for jugador, s in stats.items():
        avg_prob = sum(s['probs']) / len(s['probs'])
        prec = _prec_tramo(avg_prob)
        # Prob calibrada: ponderación 40% motor, 60% tasa real; boost por racha (+1% por HR adicional)
        prob_cal = round(prec * 0.6 + avg_prob * 0.4 + (s['hits'] - 1) * 0.8, 1)
        prob_cal = max(8.0, min(35.0, prob_cal))

        # ── Boost Statcast: si el jugador tiene barrel_rate alto, mejorar prob ──
        statcast_nota = ""
        statcast_factor = 1.0
        if _statcast_ok:
            try:
                statcast_factor, statcast_nota = factor_hr_statcast(jugador)
                if statcast_factor != 1.0:
                    # Aplicar factor con límite (no más de +5pp ni -5pp)
                    ajuste = (statcast_factor - 1.0) * 5.0
                    ajuste = max(-5.0, min(5.0, ajuste))
                    prob_cal = round(max(8.0, min(35.0, prob_cal + ajuste)), 1)
            except Exception:
                pass

        ranking.append({
            'sport': '⚾ MLB',
            'evento': s['equipo'],
            'mercado': 'HOME RUN',
            'pick': f"{jugador} pega HR",
            'prob': prob_cal,
            'tipo': 'BOMBA',
            'cuota': 3.50,
            '_hits': s['hits'],
            '_avg_prob_motor': round(avg_prob, 1),
            '_prec_historica': prec,
            '_statcast_factor': round(statcast_factor, 2),
            '_statcast_nota': statcast_nota,
        })

    # Filtra el ranking para incluir solo jugadores de equipos que juegan hoy.
    if equipos_hoy and ranking:
        from utils.fuzzy_matching import normalizar_equipo
        equipos_hoy_norm = {normalizar_equipo(e) for e in equipos_hoy}
        ranking = [r for r in ranking if normalizar_equipo(r.get('evento', '')) in equipos_hoy_norm]

    ranking.sort(key=lambda x: (x['_hits'], x['_statcast_factor'], x['_avg_prob_motor']), reverse=True)
    return ranking[:top_n]


def render_parlay_tab():
    """Renderiza la pestaña de parlays cross-deporte."""
    st.header("🎰 PARLAYS — Lo mejor de todos los deportes")
    st.caption("Combina los picks más probables de NBA, MLB, UFC y Fútbol en parlays estructurados.")

    # ── 📋 Resultados de picks recientes (qué propuso y cómo acertó) ─────────
    if pick_memory is not None:
        try:
            resueltos = [p for p in pick_memory.todos() if p.get("estado") in ("ganado", "perdido")]
            recientes = sorted(resueltos, key=lambda x: x.get("resuelto_en") or x.get("timestamp", ""),
                               reverse=True)[:15]
            if recientes:
                ok = sum(1 for p in recientes if p["estado"] == "ganado")
                with st.expander(f"📋 Resultados recientes de picks — {ok}/{len(recientes)} acertados ✅", expanded=True):
                    for p in recientes:
                        ico = "✅" if p["estado"] == "ganado" else "❌"
                        res = f" → {p.get('resultado_real','')}" if p.get("resultado_real") else ""
                        st.markdown(
                            f"<div style='font-size:0.85rem;padding:2px 0'>{ico} "
                            f"<b>{p.get('deporte','')}</b> · {p.get('pick','')} "
                            f"<span style='color:#64748b'>({p.get('evento','')})</span>"
                            f"<span style='color:#94a3b8'>{res}</span></div>",
                            unsafe_allow_html=True)
                    st.caption("💡 Marca/auto-resuelve picks en la pestaña Backtesting → 🧠 Aprendizaje "
                               "para alimentar estos resultados.")
        except Exception:
            pass

    cargados = (len(st.session_state.get("nba_partidos", [])) +
                len(st.session_state.get("mlb_partidos", [])) +
                len(st.session_state.get("ufc_combates", [])) +
                sum(len(v) for v in st.session_state.get("futbol_partidos", {}).values()))
    if cargados == 0:
        st.info("👈 Carga partidos de algún deporte en el panel de control para generar parlays.")
        return

    # Filtro por día: entre semana puede haber cambios/lesiones, así que recalcula
    # picks frescos del día elegido (hoy / mañana) en vez de usar los del fin de semana.
    hoy = datetime.now().strftime("%Y-%m-%d")
    manana = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    dia_opt = st.radio("📅 Día de los picks", ["Hoy", "Mañana", "Todos"],
                       horizontal=True, index=0,
                       help="Filtra los juegos por fecha y recalcula los picks de ese día.")
    dia_filtro = {"Hoy": hoy, "Mañana": manana, "Todos": None}[dia_opt]

    col_cfg1, col_cfg2, col_cfg3 = st.columns(3)
    with col_cfg1:
        min_prob = st.slider("Prob. mínima por leg (%)", 45, 75, 55, step=1)
    with col_cfg2:
        n_legs = st.slider("Legs del parlay Seguro", 2, 15, 5, step=1)
    with col_cfg3:
        st.write("")
        generar = st.button("⚡ GENERAR MEJORES PARLAYS", use_container_width=True, type="primary")

    # Modo enfocado (poda): por defecto muestra solo los ~7 parlays de calidad y
    # oculta los redundantes/lotería. Los ocultos SE SIGUEN guardando para el
    # aprendizaje; desmarca para verlos todos.
    st.session_state["_parlay_focus"] = st.checkbox(
        "🎯 Modo enfocado — menos parlays, más calidad (oculta redundantes/lotería)",
        value=st.session_state.get("_parlay_focus", True))

    # Persistencia: una vez generado, los parlays QUEDAN visibles aunque toques
    # otro control (slider, día). Antes se recalculaba solo mientras 'generar'
    # estaba en True, así que cualquier clic posterior reiniciaba todo y los
    # parlays desaparecían ("me reinicia todo"). Un flag de sesión los mantiene.
    if generar:
        st.session_state["_parlay_visible"] = True

    if not st.session_state.get("_parlay_visible"):
        st.caption("Pulsa **Generar** para analizar todo lo cargado y armar los parlays.")
        return

    # El pool (correr todos los motores) es lo CARO. Se cachea por día: ajustar
    # 'prob mínima' o 'nº de legs' re-arma los parlays al instante sin re-analizar.
    # Solo se re-analiza al pulsar Generar o al cambiar el día.
    _pool_key = f"_parlay_pool_{dia_filtro}"
    if generar or _pool_key not in st.session_state:
        with st.spinner(f"Analizando juegos ({dia_opt.lower()}) y armando parlays..."):
            pool = _recolectar_picks(dia_filtro)
        st.session_state[_pool_key] = pool
    else:
        pool = st.session_state[_pool_key]

    if not pool and dia_filtro is not None:
        st.warning(f"No hay juegos para **{dia_opt}** ({dia_filtro}). Prueba con 'Todos' o carga más juegos.")
        return

    if not pool:
        st.warning("No se generaron picks. Asegúrate de tener juegos cargados.")
        return

    # ── Diagnóstico: picks por deporte (detecta si falta alguno) ──────────────
    por_deporte = {}
    for pk in pool:
        s = pk.get("sport", "?")
        por_deporte[s] = por_deporte.get(s, 0) + 1
    deportes_cargados = {
        "🏀 NBA":  len(st.session_state.get("nba_partidos", [])),
        "⚾ MLB":  len(st.session_state.get("mlb_partidos", [])),
        "🥊 UFC":  len(st.session_state.get("ufc_combates", [])),
        "⚽ FÚTBOL": sum(len(v) for v in st.session_state.get("futbol_partidos", {}).values()),
    }
    alertas = []
    for deporte, n_cargados in deportes_cargados.items():
        n_picks = por_deporte.get(deporte, 0)
        if n_cargados > 0 and n_picks == 0:
            alertas.append(f"**{deporte}**: {n_cargados} partido(s) cargado(s) pero 0 picks generados "
                           f"(¿juegos de otro día o ya iniciados?)")
    if alertas:
        with st.expander("⚠️ Deportes sin picks — diagnóstico", expanded=True):
            for a in alertas:
                st.warning(a)
            st.caption("Solución: selecciona **Todos** en el filtro de día, o verifica que los juegos "
                       "no hayan empezado ya. UFC requiere que el tab UFC esté cargado.")

    # ── FASE 1 (Memoria): registrar los picks propuestos para aprender de ellos ──
    if pick_memory is not None:
        try:
            registros = [{
                "deporte": _deporte_code(pk.get("sport", "")),
                "liga": pk.get("sport", ""),
                "evento": pk.get("evento", ""),
                "mercado": pk.get("mercado", ""),
                "pick": pk.get("pick", ""),
                "seleccion": pk.get("pick", ""),
                "cuota": pk.get("cuota", 1.9),
                "confianza": pk.get("prob_base", pk.get("prob", 0)),
                "fecha_evento": _fecha_iso(pk.get("_partido", {})) if pk.get("_partido") else datetime.now().strftime("%Y-%m-%d"),
            } for pk in pool]
            n_log = len(pick_memory.log_varios(registros))
            st.caption(f"🧠 {n_log} picks registrados en la memoria de aprendizaje.")
        except Exception as _le:
            logger.warning(f"log picks: {_le}")

    # ── 🤖 PARLAY DE IA (auto-generado) ───────────────────────────────────────
    st.markdown("---")
    modelo_ia = st.session_state.get("selected_ia_model", "Heurístico")
    if modelo_ia != "Heurístico":
        with st.spinner(f"🤖 Generando parlay con {modelo_ia}..."):
            parlay_ia = _parlay_de_ia(st.session_state, dia_filtro, n_legs=3)
        if parlay_ia:
            _tarjeta_parlay(f"🤖 PARLAY DE IA ({modelo_ia})", "#8b5cf6", # Violet color
                            f"Los 3 mejores picks generados automáticamente por la IA '{modelo_ia}'.",
                            parlay_ia)
        else:
            st.info(f"🤖 La IA ({modelo_ia}) no encontró suficientes picks de alta confianza para armar un parlay hoy.")

    # Ordenar por probabilidad
    pool.sort(key=lambda x: x["prob"], reverse=True)

    # ── Mejor pick por deporte ───────────────────────────────────────────
    st.subheader("🏆 Mejor pick por deporte")
    mejores_por_deporte = {}
    for pk in pool:
        if pk["mercado"] not in ("HOME RUN",):  # el "mejor seguro" no es una prop de HR
            if pk["sport"] not in mejores_por_deporte:
                mejores_por_deporte[pk["sport"]] = pk
    cols = st.columns(max(1, len(mejores_por_deporte)))
    for col, (sport, pk) in zip(cols, mejores_por_deporte.items()):
        col.markdown(
            f"<div style='background:#1e293b;border-radius:10px;padding:12px;text-align:center'>"
            f"<div style='font-size:1.1rem'>{sport}</div>"
            f"<div style='color:#fff;font-weight:700;font-size:0.95rem;margin:4px 0'>{pk['pick']}</div>"
            f"<div style='color:#22c55e;font-weight:800;font-size:1.3rem'>{pk['prob']:.0f}%</div>"
            f"<div style='color:#64748b;font-size:0.72rem'>{pk['mercado']}</div></div>",
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # ── 🏆 PARLAY DEL MUNDIAL ───────────────────────────────────────────────
    parlay_mundial = _parlay_mundial(pool, n_legs=3)
    if parlay_mundial:
        st.markdown("")
        _tarjeta_parlay("🏆 PARLAY DEL MUNDIAL", "#8a2be2", # BlueViolet
                        "Combina los 3 mejores picks de la Copa del Mundo con confianza > 60%.",
                        parlay_mundial)
        st.markdown("---")

    # ── 🔥 PARLAY DE RACHAS (MOMENTUM) ──────────────────────────────────────
    parlay_rachas = _parlay_de_rachas(pool, n_legs=3)
    if parlay_rachas:
        st.markdown("")
        _tarjeta_parlay("🔥 PARLAY DE RACHAS (MOMENTUM)", "#f97316",
                        "Combina los 3 equipos favoritos con mayor probabilidad de victoria del día.",
                        parlay_rachas)

    # ── 🐺 PARLAY UNDERDOG (CUOTAS ALTAS) ───────────────────────────────────
    parlay_underdog = _parlay_underdog(pool, n_legs=3)
    if parlay_underdog:
        st.markdown("")
        _tarjeta_parlay("🐺 PARLAY UNDERDOG", "#a78bfa",
                        "Combina 3 picks con cuotas altas pero una probabilidad razonable (>35%).",
                        parlay_underdog)
    # NOTA: aquí había un segundo parlay "📈 MEJOR RACHA" que llamaba a
    # _parlay_mejor_racha() — función que NUNCA se definió → NameError que cortaba
    # la pestaña. Se eliminó por estar roto y ser redundante con "🔥 RACHAS".

    # ── 🎯 PARLAY ÓPTIMO (4 legs de MAYOR probabilidad real) ──────────────
    # 4 legs: mejor balance prob/pago. Toma la MEJOR leg calibrada por evento
    # (sin HR, 1 por evento), top 4 por probabilidad calibrada.
    def _prob_cal(l):
        return _prob_realista_leg(l)   # calibración + cap de realismo unificados

    cand_opt = sorted([p for p in pool if p["mercado"] != "HOME RUN"],
                      key=_prob_cal, reverse=True)
    vistos_opt, legs_opt = set(), []
    for p in cand_opt:
        if p["evento"] in vistos_opt:
            continue
        vistos_opt.add(p["evento"])
        legs_opt.append(p)
        if len(legs_opt) >= 4:
            break
    if len(legs_opt) >= 2:
        _tarjeta_parlay(f"🎯 PARLAY ÓPTIMO ({len(legs_opt)} legs)", "#10b981",
                        f"Las {len(legs_opt)} legs de MAYOR probabilidad real (1 por evento) — "
                        "el más fiable según backtest",
                        _armar_parlay(legs_opt))

    # ── 🛡️ PARLAY MONEYLINE SEGURO (los favoritos más claros) ──────────────
    parlay_ml_seguro = _parlay_moneyline_seguro(pool, n_legs=3)
    if parlay_ml_seguro:
        st.markdown("")
        _tarjeta_parlay("🛡️ MONEYLINE SEGURO", "#3b82f6", # Blue color
                        "Combina los 3 favoritos (Moneyline) con mayor probabilidad de victoria del día.",
                        parlay_ml_seguro)

    # ── 🔐 PARLAY DOBLE SEGURO: mínimas legs para cuota ≥ 2.0x ────────────
    # Elige el mínimo de legs de alta probabilidad para que el parlay pague
    # al menos el DOBLE de lo apostado (cuota ≥ 2.0x → $100 se vuelven ≥$200).
    legs_doble, cuota_doble_acc = [], 1.0
    for p in cand_opt:
        ev_d = p.get("evento", "")
        if any(l.get("evento") == ev_d for l in legs_doble):
            continue
        legs_doble.append(p)
        cuota_doble_acc *= p.get("cuota", 1.85) or 1.85
        if cuota_doble_acc >= 2.0 and len(legs_doble) >= 2:
            break
    if legs_doble and cuota_doble_acc >= 2.0:
        par_doble = _armar_parlay(legs_doble)
        _tarjeta_parlay("🔐 PARLAY DOBLE SEGURO", "#22d3ee", # Cyan color
                        f"Mínimas legs de mayor prob para duplicar tu dinero (cuota ≥ 2x) — "
                        f"{len(legs_doble)} legs, {par_doble['prob']:.1f}% prob",
                        par_doble)

    # ── 🪜 ESCALERA DE PARLAYS: elige tu riesgo (prob real vs pago) ────────
    # Usa las mejores legs calibradas (1 por evento, ya ordenadas por prob).
    # Muestra, por tamaño, la probabilidad REAL de que ganen TODAS y el pago,
    # para decidir entre "no perder" (pocas legs) y "gran ganancia" (muchas).
    legs_esc, vistos_esc = [], set()
    for p in cand_opt:
        if p["evento"] in vistos_esc:
            continue
        vistos_esc.add(p["evento"])
        legs_esc.append(p)
    if len(legs_esc) >= 2:
        st.markdown("#### 🪜 Escalera de parlays — elige tu riesgo")
        st.caption("Probabilidad REAL de que ganen TODAS las legs (calibrada con backtest). "
                   "Más legs = más pago pero MENOS probable. Ningún parlay es 100% seguro.")
        filas = []
        try:
            from motors.montecarlo_parlay import prob_combinada_mc, simular_estrategia
            _mc_ok = True
        except Exception:
            _mc_ok = False
        for n in range(2, min(len(legs_esc), 10) + 1):
            sub = legs_esc[:n]
            par = _armar_parlay(sub)
            prob = par["prob"]
            # Monte Carlo: corrige la prob si hay legs correlacionadas (mismo
            # partido) y simula el riesgo/retorno de apostarlo 30 veces.
            rentable = roi = None
            if _mc_ok:
                mc_legs = [{"prob": _prob_cal(l), "evento": l.get("evento", "")} for l in sub]
                prob = round(prob_combinada_mc(mc_legs, n_sims=4000) * 100, 1)
                sim = simular_estrategia(prob / 100.0, par["cuota"], n_apuestas=30, sims=2500)
                rentable, roi = sim["pct_rentable"], sim["roi_medio_pct"]
            filas.append({"n": n, "prob": prob, "cuota": par["cuota"],
                          "gan": round((par["cuota"] - 1) * 100), "ev": par["ev_pct"],
                          "rentable": rentable, "roi": roi})
        # el de MAYOR ganancia cuya probabilidad aún es razonable (≥10%)
        grande = max([f for f in filas if f["prob"] >= 10], key=lambda f: f["gan"], default=None)
        for f in filas:
            color = "#22c55e" if f["prob"] >= 25 else "#fbbf24" if f["prob"] >= 10 else "#ef4444"
            tags = []
            if f["n"] <= 3:
                tags.append("<span style='color:#22c55e'>🛡️ para no perder</span>")
            if grande and f["n"] == grande["n"]:
                tags.append("<span style='color:#f59e0b'>💰 mayor ganancia razonable</span>")
            riesgo_txt = ""
            if f.get("rentable") is not None:
                rc = "#22c55e" if f["rentable"] >= 50 else "#ef4444"
                riesgo_txt = (f" · <span style='color:{rc};font-size:0.8rem' "
                              f"title='Monte Carlo: 30 apuestas de $100'>rentable {f['rentable']}% · "
                              f"ROI {f['roi']:+.0f}%</span>")
            st.markdown(
                f"<div style='background:#0f172a;border-radius:6px;padding:5px 12px;margin:2px 0'>"
                f"<b>{f['n']} legs</b> · prob <b style='color:{color}'>{f['prob']}%</b> · "
                f"cuota {f['cuota']}x · $100 → <b style='color:#22c55e'>${f['gan']:,}</b>"
                f"{riesgo_txt}  {' · '.join(tags)}</div>",
                unsafe_allow_html=True)
        if grande:
            st.caption(f"💡 'No perder': 2-3 legs ({filas[0]['prob']}% a 2). 'Gran ganancia': hasta "
                       f"{grande['n']} legs (~{grande['prob']}% real, ${grande['gan']:,}). "
                       "Más allá es lotería. NOTA: el pago usa cuotas ESTIMADAS; con cuotas reales "
                       "de tu casa se calcula el valor (EV) exacto. Si cada leg tiene valor positivo, "
                       "a la larga rinde más apostarlas POR SEPARADO que en parlay.")

    # ── ⚽ PARLAY SOLO FÚTBOL (las predicciones que auditamos) ───────────────
    # Reúne SOLO legs de fútbol (mejor por partido), priorizadas por la tasa de
    # acierto auditada del backtest. Las mismas legs siguen en el pool, así que
    # también alimentan los parlays cross-deporte de abajo.
    _parlay_solo_futbol(pool, n_legs=n_legs, min_prob=min_prob)

    # ── Parlay SEGURO: COMBINA deportes (mejor de cada uno) + relleno por prob ──
    seguros = [p for p in pool if p["prob"] >= min_prob and p["mercado"] != "HOME RUN"]
    vistos_evento = set()
    legs_seguro = []
    # 1) Lo mejor de CADA deporte primero (garantiza combinación NBA/MLB/UFC/Fútbol)
    deportes_vistos = set()
    for p in seguros:  # pool ya viene ordenado por prob desc
        if p["sport"] in deportes_vistos or p["evento"] in vistos_evento:
            continue
        deportes_vistos.add(p["sport"])
        vistos_evento.add(p["evento"])
        legs_seguro.append(p)
    # 2) Rellenar el resto por probabilidad (distintos eventos)
    for p in seguros:
        if len(legs_seguro) >= n_legs:
            break
        if p["evento"] in vistos_evento:
            continue
        vistos_evento.add(p["evento"])
        legs_seguro.append(p)
    # Recortar y reordenar por probabilidad
    legs_seguro = sorted(legs_seguro, key=lambda x: x["prob"], reverse=True)[:n_legs]

    if len(legs_seguro) >= 2:
        n_deportes = len(set(l["sport"] for l in legs_seguro))
        _tarjeta_parlay("🟢 PARLAY SEGURO", "#22c55e", # Green color
                        f"{len(legs_seguro)} picks de {n_deportes} deporte(s), distintos eventos",
                        _armar_parlay(legs_seguro))
    else:
        st.info(f"No hay suficientes picks con prob ≥ {min_prob}% para el parlay seguro. Baja el umbral.")

    # ── Parlay VALOR: 3 seguros + 1 HR top ───────────────────────────────
    hrs = [p for p in pool if p["mercado"] == "HOME RUN"]
    if legs_seguro and hrs:
        base = legs_seguro[:3]
        mejor_hr = max(hrs, key=lambda x: x["prob"])
        legs_valor = base + [mejor_hr]
        st.markdown("")
        _tarjeta_parlay("🟡 PARLAY VALOR", "#fbbf24", # Amber/Yellow color
                        "Picks seguros + el mejor candidato a Home Run (mayor pago)",
                        _armar_parlay(legs_valor))

    # ── Parlay BOMBA: las 3 mejores props de HR ──────────────────────────
    if len(hrs) >= 2:
        hrs.sort(key=lambda x: x["prob"], reverse=True)
        legs_bomba = hrs[:3]
        st.markdown("")
        _tarjeta_parlay("🔴 PARLAY BOMBA", "#ef4444", # Red color
                        "Solo candidatos a Home Run — baja probabilidad, pago muy alto",
                        _armar_parlay(legs_bomba))

    # ── PARLAY HR + FÚTBOL: sluggers top (HR) + mejores picks de fútbol ──────
    # Tu escenario ganador: 2-3 home runs de élite + 2-3 picks de fútbol.
    hr_top = sorted([p for p in pool if p["mercado"] == "HOME RUN"],
                    key=lambda x: x["prob"], reverse=True)[:3]
    fut_top, _vf = [], set()
    for p in sorted([p for p in pool if "FÚTBOL" in p["sport"] and p["prob"] >= min_prob],
                    key=lambda x: x["prob"], reverse=True):
        if p["evento"] in _vf:
            continue
        _vf.add(p["evento"]); fut_top.append(p)
        if len(fut_top) >= 3:
            break
    legs_hrfut = fut_top[:3] + hr_top[:2]
    if len(legs_hrfut) >= 3 and hr_top:
        st.markdown("")
        _tarjeta_parlay("🎯 PARLAY HR + FÚTBOL", "#e11d48", # Rose color
                        "Sluggers top (home run) + mejores picks de fútbol — pago alto, tu combo favorito",
                        _armar_parlay(legs_hrfut))

    # ── ⚡ PARLAY SLUGGER DEL DÍA: basado en datos aprendidos del backtest ─────
    # Usa SOLO la memoria histórica de quién pegó HR en los últimos días,
    # calibrando la probabilidad con la tasa de acierto real (no la del motor).
    equipos_mlb_hoy = set()
    if pool:
        for p in pool:
            if "MLB" in p.get("sport", ""):
                try:
                    # El evento es 'Away @ Home', con nombres normalizados
                    away, home = p.get("evento", "").split(" @ ")
                    equipos_mlb_hoy.add(away.strip())
                    equipos_mlb_hoy.add(home.strip())
                except ValueError:
                    pass
    sluggers = _sluggers_del_dia(top_n=5, equipos_hoy=equipos_mlb_hoy)
    if len(sluggers) >= 3:
        st.markdown("")
        prec_global_bt = 0.0
        try:
            import json as _json
            _rep_path = __import__('os').path.join("data", "hr_backtest_reporte.json")
            with open(_rep_path, encoding='utf-8') as _f:
                _rep = _json.load(_f)
            prec_global_bt = _rep.get('precision_global', 0)
            _ts = _rep.get('timestamp', '')[:10]
            _juegos = _rep.get('juegos', 0)
        except Exception:
            _ts, _juegos = '', 0
        desc_slug = (
            f"Los {len(sluggers)} sluggers con más HRs recientes (backtest {_juegos} juegos · "
            f"{prec_global_bt:.1f}% tasa real · datos: {_ts}) — prob calibrada con tasa histórica"
        )
        _tarjeta_parlay("⚡ PARLAY SLUGGER DEL DÍA", "#f59e0b", desc_slug, _armar_parlay(sluggers)) # Orange color

        # Detalle de cada slugger (oculto en modo enfocado, junto con su tarjeta)
        if not st.session_state.get("_parlay_focus", True):
          with st.expander("📊 Detalle de la racha de cada Slugger + Statcast", expanded=False):
            st.markdown(
                "<div style='font-size:0.82rem;color:#94a3b8'>Jugadores con HRs confirmados "
                "en los últimos días del backtest, mejorados con datos Statcast (barrel rate / exit velo). "
                "La probabilidad combina: tasa real (60%) + motor (40%) + racha + Statcast.</div>",
                unsafe_allow_html=True)
            for s in sluggers:
                racha = "🔥" * min(s['_hits'], 3)
                sc_factor = s.get('_statcast_factor', 1.0)
                sc_nota = s.get('_statcast_nota', '')
                sc_color = "#22c55e" if sc_factor >= 1.1 else "#ef4444" if sc_factor < 0.9 else "#94a3b8"
                sc_ico = "🚀" if sc_factor >= 1.2 else "📈" if sc_factor >= 1.05 else "📊" if sc_factor >= 0.95 else "📉"
                sc_html = (f"<br><span style='color:{sc_color};font-size:0.75rem'>"
                           f"{sc_ico} {sc_nota[:80]}</span>") if sc_nota else ""
                st.markdown(
                    f"<div style='background:#1e293b;border-radius:6px;padding:8px 12px;margin:3px 0'>"
                    f"<b>{s['pick']}</b> · {s['evento']} "
                    f"<span style='float:right'>"
                    f"{racha} <span style='color:#fbbf24'>{s['_hits']} HRs recientes</span> | "
                    f"motor: {s['_avg_prob_motor']}% → calibrada: "
                    f"<b style='color:#22c55e'>{s['prob']}%</b>"
                    f"</span>"
                    f"{sc_html}"
                    f"</div>",
                    unsafe_allow_html=True)

    # ── PARLAY GIGANTE: TODOS los picks sólidos (1 por evento, 10+ legs) ──
    gigante = [p for p in pool if p["prob"] >= min_prob and p["mercado"] != "HOME RUN"]
    vistos_g = set()
    legs_gigante = []
    for p in gigante:
        if p["evento"] in vistos_g:
            continue
        vistos_g.add(p["evento"])
        legs_gigante.append(p)
    if len(legs_gigante) >= 7:
        st.markdown("")
        _tarjeta_parlay(f"🟣 PARLAY GIGANTE ({len(legs_gigante)} legs)", "#a855f7", # Purple color
                        "Todos los picks sólidos del día — pago enorme, probabilidad baja pero estructurada",
                        _armar_parlay(legs_gigante))

    # ── PARLAY MÁXIMO PAGO: por evento, el mercado que MÁS paga (combinados) ──
    # No se queda en el Over 0.5 seguro: prefiere el combinado gana+Over (mayor
    # momio) por cada evento, manteniendo una probabilidad razonable.
    candidatos_pago = [p for p in pool
                       if p["prob"] >= max(40, min_prob - 12) and p["mercado"] != "HOME RUN"]
    mejor_por_evento = {}
    for p in candidatos_pago:
        ev = p["evento"]
        if ev not in mejor_por_evento or p["cuota"] > mejor_por_evento[ev]["cuota"]:
            mejor_por_evento[ev] = p
    legs_pago = sorted(mejor_por_evento.values(), key=lambda x: x["cuota"], reverse=True)[:n_legs]
    if len(legs_pago) >= 2:
        st.markdown("")
        _tarjeta_parlay("💎 PARLAY MÁXIMO PAGO", "#06b6d4", # Cyan color
                        "Por evento elige el mercado que MÁS paga (combinados gana+Over) sin perder calidad",
                        _armar_parlay(legs_pago))

    # ── 💎 PARLAY DE VALOR (+EV): solo legs con valor real ──────────────────
    # Valor = prob. del modelo > prob. implícita del momio (prob > 100/cuota).
    # Es la apuesta matemáticamente correcta: solo donde el momio paga de más.
    def _ev(p):
        c = p.get("cuota", 1.9) or 1.9
        return p["prob"] / 100.0 * c - 1.0
    valor, _ve = [], set()
    for p in sorted(pool, key=_ev, reverse=True):
        c = p.get("cuota", 1.9) or 1.9
        implied = 100.0 / c if c > 0 else 100.0
        if p["prob"] > implied and p["mercado"] != "HOME RUN" and p["evento"] not in _ve:
            _ve.add(p["evento"]); valor.append(p)
        if len(valor) >= n_legs:
            break
    if len(valor) >= 2:
        st.markdown("")
        _tarjeta_parlay("💎 PARLAY DE VALOR (+EV)", "#14b8a6", # Teal color
                        "Solo selecciones con VALOR real: prob. del modelo > prob. implícita del momio",
                        _armar_parlay(valor))

    # ── Tabla completa del pool ──────────────────────────────────────────
    st.markdown("---")
    with st.expander(f"📋 Ver los {len(pool)} picks analizados", expanded=False):
        st.table([
            {"Deporte": p["sport"], "Pick": p["pick"], "Mercado": p["mercado"],
             "Prob": f"{p['prob']:.0f}%", "Evento": p["evento"]}
            for p in pool
        ])

def render_parlay_backtest_section():
    # ── 📊 BACKTEST DE PARLAYS: historial real y resolución ─────────────────
    st.markdown("---")
    st.markdown("#### 📊 Backtest de parlays generados")
    st.caption("Cada parlay que genera esta página se guarda automáticamente. "
               "Al terminar los juegos, resuelve para ver cuántos acertaste.")

    col_bt1, col_bt2 = st.columns(2)
    with col_bt1:
        if st.button("🔄 Auto-resolver parlays pendientes", use_container_width=True, key="bt_parlays_resolve"):
            with st.spinner("Cruzando resultados reales con legs del parlay..."):
                # resolver_todo() ya cierra picks (MLB/NBA/UFC/Fútbol) Y parlays en
                # una sola pasada — fuente única, sin doble resolución redundante.
                try:
                    from motors.box_score_resolver import resolver_todo
                    rr = resolver_todo()
                    st.success(f"Picks: {rr['mlb']} MLB + {rr['nba']} NBA + {rr.get('ufc', 0)} UFC "
                               f"+ {rr.get('soccer', 0)} Fútbol resueltos · 🎰 {rr.get('parlays', 0)} parlays cerrados")
                    if not any(rr.get(k, 0) for k in ('mlb', 'nba', 'ufc', 'soccer', 'parlays')):
                        st.info("Nada nuevo que resolver — los juegos de los picks/parlays pendientes "
                                "aún no terminan.")
                except Exception as _ep:
                    st.error(f"Error al resolver: {_ep}")
            st.rerun()

    # Stats por tipo
    with col_bt2:
        try:
            from motors.parlay_brain import stats_por_tipo as _spt
            _stats = _spt()
            if _stats:
                # Prioridad: mostrar stats del Parlay del Mundial si existen
                wc_stats = next((v for k, v in _stats.items() if "MUNDIAL" in k.upper()), None)
                if wc_stats and wc_stats.get("total", 0) > 0:
                    st.metric("🏆 Parlay Mundial", f"{wc_stats['win_rate']:.1f}% WR", f"ROI {wc_stats['roi']:+.1f}%")
                else:
                    # Fallback al mejor tipo si no hay datos del Mundial
                    mejor = max(_stats.items(), key=lambda x: x[1].get("win_rate", 0))
                    st.metric("Mejor tipo", mejor[0][:20], f"{mejor[1]['win_rate']}% acierto")
        except Exception:
            pass

    # Historial últimos 14 días
    try:
        import json as _json, os as _os
        from datetime import datetime as _dt, timedelta as _td
        _ruta = _os.path.join("data", "parlay_history.json")
        _hist = _json.load(open(_ruta, encoding="utf-8")) if _os.path.exists(_ruta) else []
        _cutoff = (_dt.now() - _td(days=14)).strftime("%Y-%m-%d")
        _recientes = [h for h in _hist if h.get("fecha", "") >= _cutoff]
        if _recientes:
            _total = len(_recientes)

            col_filter, col_export = st.columns([3, 1])
            with col_filter:
                # Filtro por tipo de parlay
                tipos_parlay = sorted(list(set(h.get("tipo", "Desconocido") for h in _recientes)))
                filtro_tipo = st.selectbox(
                    "Filtrar por tipo de parlay",
                    ["Todos"] + tipos_parlay
                )

            parlays_a_mostrar = [h for h in _recientes if filtro_tipo == "Todos" or h.get("tipo") == filtro_tipo]

            with col_export:
                st.write("") # for vertical alignment
                if parlays_a_mostrar:
                    import pandas as pd
                    csv_data = []
                    for parlay in parlays_a_mostrar:
                        # Calcular profit/loss
                        estado = parlay.get("estado")
                        cuota = parlay.get("cuota", 0) or 0
                        profit = 0.0
                        if estado == "ganado":
                            profit = cuota - 1.0
                        elif estado == "perdido":
                            profit = -1.0

                        base_info = {
                            "parlay_id": parlay.get("id"), "fecha": parlay.get("fecha"),
                            "tipo_parlay": parlay.get("tipo"), "estado_parlay": parlay.get("estado"),
                            "cuota_parlay": parlay.get("cuota"), "prob_parlay": parlay.get("prob"),
                            "profit_loss": round(profit, 2),
                            "n_legs": parlay.get("n_legs"),
                        }
                        for leg in parlay.get("legs", []):
                            csv_data.append({**base_info, **leg})
                    
                    df = pd.DataFrame(csv_data)
                    csv_string = df.to_csv(index=False).encode('utf-8')
                    
                    st.download_button(
                       label="📥 Exportar CSV", data=csv_string,
                       file_name=f"historial_parlays_{filtro_tipo.lower().replace(' ', '_')}.csv",
                       mime="text/csv", use_container_width=True
                    )

            _gan = sum(1 for h in parlays_a_mostrar if h.get("estado") == "ganado")
            _per = sum(1 for h in parlays_a_mostrar if h.get("estado") == "perdido")
            _pend = len(parlays_a_mostrar) - _gan - _per
            _wr = round(_gan / (_gan + _per) * 100, 1) if (_gan + _per) > 0 else None
            _resumen = (f"**{len(parlays_a_mostrar)}** parlays mostrados — "
                        f"✅ {_gan} ganados · ❌ {_per} perdidos · ⏳ {_pend} pendientes"
                        + (f" · **{_wr}% win rate**" if _wr is not None else ""))
            st.markdown(_resumen)

            with st.expander("📅 Ver historial detallado", expanded=False):
                _by_day: dict = {}
                for h in reversed(parlays_a_mostrar):
                    _day = h.get("fecha", "?")
                    _by_day.setdefault(_day, []).append(h)
                def _dec2am(d):
                    if d >= 2.0: return f"+{round((d-1)*100)}"
                    return f"-{round(100/(d-1))}" if d > 1 else "N/A"
                for _day, _parlays_day in sorted(_by_day.items(), reverse=True):
                    st.markdown(f"**{_day}** ({len(_parlays_day)} parlays)")
                    for _h in _parlays_day:
                        _ico = "✅" if _h.get("estado") == "ganado" else "❌" if _h.get("estado") == "perdido" else "⏳"
                        _tipo_lbl = _h.get("tipo", "")[:30]
                        _cuota_str = _dec2am(_h.get("cuota", 1.0)) if _h.get("cuota") else "?"
                        _legs_str = f"{_h.get('n_legs', '?')} legs"
                        st.markdown(
                            f"<div style='background:#0f172a;border-radius:6px;padding:4px 10px;margin:2px 0'>"
                            f"{_ico} <b>{_tipo_lbl}</b> · {_legs_str} · {_cuota_str} · "
                            f"{_h.get('prob', '?')}% prob"
                            f"</div>",
                            unsafe_allow_html=True)
                        for _leg in _h.get("legs", []):
                            st.markdown(
                                f"<div style='background:#1e293b;border-radius:4px;padding:2px 8px;"
                                f"margin:1px 0 1px 16px;font-size:0.8rem;color:#94a3b8'>"
                                f"• {_leg.get('pick', '?')} · {_leg.get('evento', '')}</div>",
                                unsafe_allow_html=True)
    except Exception:
        pass

    # Renderizar la nueva sección de análisis de rentabilidad
    _render_profitability_by_type()


def _render_profitability_by_type():
    """Muestra el rendimiento histórico (WR, ROI) por tipo de parlay."""
    if stats_por_tipo is None:
        return

    try:
        _stats_t = stats_por_tipo()
        if _stats_t:
            st.markdown("---")
            st.markdown("**📊 Aprendizaje por tipo de parlay (resultados reales):**")
            st.caption("Cuál tipo de parlay ha sido más rentable. El generador usa esto para mostrarte primero los mejores.")

            # Ordenar por ROI (rentabilidad) como criterio principal
            filas_t = sorted(_stats_t.items(), key=lambda x: (x[1].get("roi", 0), x[1].get("win_rate", 0)), reverse=True)

            for tipo_t, s_t in filas_t:
                color_roi = "#22c55e" if s_t.get("roi", 0) >= 0 else "#ef4444"
                color_wr = "#22c55e" if s_t.get("win_rate", 0) >= 50 else "#f59e0b" if s_t.get("win_rate", 0) >= 40 else "#ef4444"

                # Limpiar el nombre del tipo de parlay para que sea más legible
                tipo_lbl = re.sub(r"[^\w\s\-\.]", "", tipo_t).strip()[:30]

                st.markdown(
                    f"<div style='background:#0f172a;border-radius:6px;padding:5px 12px;margin:2px 0'>"
                    f"<b>{tipo_lbl}</b> — "
                    f"<span style='color:{color_wr}'>{s_t['win_rate']:.1f}% acierto</span> "
                    f"({s_t['ganados']}/{s_t['total']}) · "
                    f"ROI <span style='color:{color_roi}; font-weight:700;'>"
                    f"{s_t['roi']:+.1f}%</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            st.caption("⚠️ Se necesitan al menos 4+ parlays resueltos por tipo para que el aprendizaje sea estadísticamente significativo.")
    except Exception as e:
        logger.warning(f"Error al renderizar stats por tipo de parlay: {e}")


# ──────────────────────────────────────────────────────────────────────────
# PARLAY SOLO FÚTBOL — usa las predicciones de fútbol que AUDITAMOS (backtest)
# y arma un parlay independiente; estas mismas legs siguen entrando al pool
# cross-deporte, así que "se conecta con los demás".
# ──────────────────────────────────────────────────────────────────────────
_AUDIT_FUT = None


def _audit_futbol_rates():
    """Tasa de acierto AUDITADA de fútbol (del backtest) por mercado. Devuelve
    {'global','n','moneyline','over_under','btts','combo'} (los que tengan ≥3
    muestras) o {} si no hay datos. Es la conexión con 'lo que auditamos'."""
    global _AUDIT_FUT
    if _AUDIT_FUT is not None:
        return _AUDIT_FUT
    import os, json
    _AUDIT_FUT = {}
    for ruta in (os.path.join("data", "futbol_backtest_db.json"),
                 os.path.join("data", "futbol_backtest_real.json")):
        try:
            with open(ruta, encoding="utf-8") as f:
                rep = json.load(f)
        except Exception:
            continue
        mk = rep.get("mercados", {})
        res = {"global": rep.get("precision_global", 0), "n": rep.get("evaluados", 0)}
        for k in ("moneyline", "over_under", "btts", "combo"):
            d = mk.get(k, {})
            if d.get("total", 0) >= 3:
                res[k] = d.get("precision", 0)
        if res.get("n"):
            _AUDIT_FUT = res
            break
    return _AUDIT_FUT


def _audit_rate_de_mercado(mercado):
    """Mapea el mercado del leg (1X2/OVER/UNDER/BTTS/COMBINADO) al mercado
    auditado y devuelve su % de acierto (o None si no hay dato)."""
    rates = _audit_futbol_rates()
    if not rates:
        return None
    m = (mercado or "").lower()
    if "btts" in m or "ambos" in m:
        key = "btts"
    elif "combinad" in m or "combo" in m:
        key = "combo"
    elif "over" in m or "under" in m or "gol" in m:
        key = "over_under"
    else:
        key = "moneyline"
    return rates.get(key)


def _parlay_solo_futbol(pool, n_legs=4, min_prob=55):
    """Parlay de SOLO fútbol con las predicciones que auditamos. Toma la MEJOR
    leg por partido (1 por evento), ordenada por prob calibrada con la tasa
    auditada del backtest, y muestra una escalera para elegir riesgo. Estas
    mismas legs siguen disponibles para los parlays cross-deporte."""
    fut = [p for p in pool if "FÚTBOL" in (p.get("sport", "") or "").upper()
           or "FUTBOL" in (p.get("sport", "") or "").upper()]
    st.markdown("---")
    st.subheader("⚽ PARLAY SOLO FÚTBOL")
    aud = _audit_futbol_rates()
    if aud:
        _lbl = {"moneyline": "ML", "over_under": "O/U", "btts": "BTTS", "combo": "Combo"}
        partes = [f"{lb} {aud[k]:.0f}%" for k, lb in _lbl.items() if k in aud]
        st.caption(f"📊 Auditado (backtest, {aud.get('n', 0)} picks): global "
                   f"{aud.get('global', 0):.0f}%" + (" · " + " · ".join(partes) if partes else "") +
                   ". Estas legs también se combinan en los parlays cross-deporte.")
    if not fut:
        # Diagnóstico: explicar POR QUÉ no hay picks (no solo "no hay").
        _fp = st.session_state.get("futbol_partidos", {}) or {}
        _todos = [p for ps in _fp.values() for p in (ps or [])]
        def _ya_inicio(p):
            return bool(p.get("en_vivo") or p.get("completado") or p.get("marcador")
                        or any(x in str(p.get("status", "")).lower()
                               for x in ("ft", "vivo", "final", "progress", "terminad")))
        _iniciados = sum(1 for p in _todos if _ya_inicio(p))
        if not _todos:
            st.info("⚽ No hay partidos de fútbol cargados. Carga una liga en el sidebar (⚽ FÚTBOL).")
        else:
            _resto = len(_todos) - _iniciados
            st.info(
                f"⚽ {len(_todos)} partido(s) de fútbol cargado(s), pero **0 picks para este día**: "
                f"{_iniciados} ya iniciaron/terminaron (no apostables)"
                + (f" y {_resto} son de otro día o sin datos suficientes para analizar" if _resto else "")
                + ".  👉 Pon el filtro de día en **'Todos'** para combinar los de otros días, "
                "o espera a que carguen partidos próximos.")
        return

    # ── TODAS las apuestas de fútbol generadas (lista completa por partido) ──
    _lista_apuestas_futbol(fut)

    def _prob_cal_fut(l):
        real = _rate_real_mercado(l.get("sport", ""), l.get("mercado", ""))
        aud_r = _audit_rate_de_mercado(l.get("mercado", ""))
        p = l["prob"]
        if real is not None and aud_r is not None:
            cal = 0.34 * p + 0.33 * real + 0.33 * aud_r
        elif real is not None:
            cal = 0.4 * p + 0.6 * real
        elif aud_r is not None:
            cal = 0.5 * p + 0.5 * aud_r
        else:
            cal = p * 0.7 + PRIOR_SIN_CALIBRAR * 0.3   # sin datos: descuenta sobreconfianza
        return min(cal, REALISMO_CAP)                  # techo realista (≤90%)

    vistos, legs = set(), []
    for p in sorted(fut, key=_prob_cal_fut, reverse=True):
        if p["evento"] in vistos:
            continue
        vistos.add(p["evento"])
        legs.append(p)
    if len(legs) < 2:
        st.info("Solo hay 1 partido de fútbol disponible; se necesitan ≥2 para un parlay.")
        return

    legs_top = [l for l in legs if _prob_cal_fut(l) >= min_prob][:n_legs] or legs[:n_legs]
    if len(legs_top) >= 2:
        _tarjeta_parlay(f"⚽ PARLAY SOLO FÚTBOL ({len(legs_top)} legs)", "#16a34a", # Green color
                        "La mejor leg por partido (1 por evento), solo fútbol — priorizado por la "
                        "tasa que auditamos. También entra a los parlays cross-deporte.",
                        _armar_parlay(legs_top))
    _escalera_solo_futbol(legs, _prob_cal_fut)


def _escalera_solo_futbol(legs, prob_fn):
    """Escalera 2→N de SOLO fútbol con probabilidad real (Monte Carlo corrige
    legs correlacionadas del mismo partido). Para elegir entre 'no perder'
    (pocas legs) y 'gran ganancia' (muchas)."""
    try:
        from motors.montecarlo_parlay import prob_combinada_mc
        _mc = True
    except Exception:
        _mc = False
    st.markdown("##### 🪜 Escalera solo fútbol — elige tu riesgo")
    for n in range(2, min(len(legs), 8) + 1):
        sub = legs[:n]
        par = _armar_parlay(sub)
        prob = par["prob"]
        if _mc:
            prob = round(prob_combinada_mc(
                [{"prob": prob_fn(l), "evento": l.get("evento", "")} for l in sub],
                n_sims=3000) * 100, 1)
        color = "#22c55e" if prob >= 25 else "#fbbf24" if prob >= 10 else "#ef4444"
        gan = round((par["cuota"] - 1) * 100)
  