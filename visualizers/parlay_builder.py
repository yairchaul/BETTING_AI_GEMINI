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
except Exception:
    pick_memory = None

logger = logging.getLogger(__name__)


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


def _recolectar_picks(dia_filtro=None):
    """Corre los motores sobre todo lo cargado y devuelve un pool de picks.

    dia_filtro: 'YYYY-MM-DD' para quedarte solo con los juegos de ese día
    (recalcula picks frescos del día, útil entre semana por lesiones/cambios).
    """
    ss = st.session_state
    pool = []

    def _es_del_dia(p):
        # Debe ser del día pedido Y no haber empezado/terminado todavía
        if not _no_iniciado(p):
            return False
        return (dia_filtro is None) or (_fecha_iso(p) == dia_filtro)

    # ── NBA ──────────────────────────────────────────────────────────────
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
                })
            # Props de jugador (puntos/asistencias/triples) — la más confiable por equipo
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

    # ── MLB ──────────────────────────────────────────────────────────────
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
                    "prob": mejor.get("confianza", 0), "tipo": "SEGURO",
                    "cuota": _cuota.get(mk, 1.90),
                })

            # HR candidates (props de mayor pago) — para los parlays BOMBA/SLUGGER.
            # SOLO si el bateador está en la alineación del día (oficial o proyectada).
            for hr in r.get("hr_candidates", []):
                if hr.get("en_lineup") is False:
                    continue
                prob_hr = hr.get("probabilidad", hr.get("prob", 0))
                pool.append({
                    "sport": "⚾ MLB", "evento": evento, "mercado": "HOME RUN",
                    "pick": f"{hr.get('jugador', hr.get('nombre','?'))} pega HR",
                    "prob": prob_hr, "tipo": "BOMBA", "cuota": 3.50,
                })
    except Exception as e:
        logger.warning(f"Parlay MLB: {e}")

    # ── UFC ──────────────────────────────────────────────────────────────
    try:
        _ufc_analyzer = ss.get("ufc_analyzer")
        for idx, c in enumerate(ss.get("ufc_combates", []) or []):
            if not _es_del_dia(c):
                continue
            p1 = c.get("peleador1", {})
            p2 = c.get("peleador2", {})
            fight_key = f"{p1.get('nombre','')}_vs_{p2.get('nombre','')}"
            res = ss.get("analisis_ufc", {}).get(fight_key)
            # Si no hay análisis previo, correr el motor UFC on-the-fly
            if not res and _ufc_analyzer:
                try:
                    res = _ufc_analyzer.analizar_combate(p1, p2)
                except Exception as _ue:
                    logger.debug(f"UFC on-the-fly {fight_key}: {_ue}")
            if not res:
                continue
            evento_ufc = f"{c.get('peleador1',{}).get('nombre','?')} vs {c.get('peleador2',{}).get('nombre','?')}"
            mejor = res.get("mejor_apuesta", {})
            if mejor:
                pool.append({
                    "sport": "🥊 UFC", "evento": evento_ufc,
                    "mercado": mejor.get("mercado", "GANADOR"),
                    "pick": mejor.get("apuesta", ""),
                    "prob": mejor.get("confianza", 0),
                    "tipo": "SEGURO" if mejor.get("confianza", 0) >= 55 else "VALOR",
                    "cuota": CUOTA_DEFAULT.get("MÉTODO" if "MÉTODO" in mejor.get("mercado", "") else "MONEYLINE", 2.0),
                })
            # Total de rounds más probable
            rt = sorted(res.get("rounds_totales", []), key=lambda x: x.get("confianza", 0), reverse=True)
            if rt and rt[0].get("confianza", 0) >= 58:
                pool.append({
                    "sport": "🥊 UFC", "evento": evento_ufc, "mercado": "ROUNDS",
                    "pick": rt[0].get("etiqueta", ""), "prob": rt[0].get("confianza", 0),
                    "tipo": "VALOR", "cuota": 1.85,
                })
            # Gana por KO/TKO (cuando el poder de KO del ganador es alto)
            mp = res.get("metodo_probs", {})
            ganador = res.get("ganador", "")
            prob_ko = mp.get("KO/TKO", 0)
            if ganador and prob_ko >= 40:
                pool.append({
                    "sport": "🥊 UFC", "evento": evento_ufc, "mercado": "GANA POR KO",
                    "pick": f"{ganador} gana por KO/TKO",
                    "prob": prob_ko, "tipo": "BOMBA", "cuota": 2.60,
                })
            # Gana por Sumisión (si el ganador tiene alta amenaza de sumisión)
            prob_sub = mp.get("Sumisión", 0)
            if ganador and prob_sub >= 40:
                pool.append({
                    "sport": "🥊 UFC", "evento": evento_ufc, "mercado": "GANA POR SUB",
                    "pick": f"{ganador} gana por Sumisión",
                    "prob": prob_sub, "tipo": "BOMBA", "cuota": 3.20,
                })
    except Exception as e:
        logger.warning(f"Parlay UFC: {e}")

    # ── FÚTBOL ───────────────────────────────────────────────────────────
    # Cuotas REALES: The Odds API (moneyline WC, 44 partidos) como fuente
    # principal + Caliente como respaldo. Para OVER/UNDER/BTTS se usan cuotas
    # de mercado típicas (the-odds-api free solo da moneyline).
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
                )
                pick = r.get("pick", "")
                if not pick or "revisar" in pick.lower():
                    continue
                evento_f = f"{home_f or '?'} vs {away_f or '?'}"
                cuota_real = _cuota_real_futbol(pick, home_f, away_f)
                pool.append({
                    "sport": "⚽ FÚTBOL", "evento": evento_f,
                    "mercado": "1X2/Goles", "pick": pick,
                    "prob": r.get("confianza", 0),
                    "tipo": "SEGURO" if r.get("confianza", 0) >= 55 else "VALOR",
                    "cuota": cuota_real or 1.90,
                    "cuota_real": bool(cuota_real),
                })
                for op in r.get("todas_opciones", []):
                    if op.get("combo") and op.get("confianza", 0) >= 38:
                        pool.append({
                            "sport": "⚽ FÚTBOL", "evento": evento_f,
                            "mercado": "COMBINADO", "pick": op["pick"],
                            "prob": op["confianza"], "tipo": "VALOR",
                            "cuota": op.get("cuota", 2.4),
                        })
    except Exception as e:
        logger.warning(f"Parlay fútbol: {e}")

    # ── FASE 3 (Evolución): ponderar cada pick por su rendimiento histórico ──
    # El selector se vuelve más inteligente: penaliza mercados que históricamente
    # fallan y premia los que aciertan (factor_confianza desde la memoria).
    if pick_memory is not None:
        for pk in pool:
            try:
                pk["prob_base"] = pk["prob"]
                factor = pick_memory.factor_confianza(_deporte_code(pk.get("sport", "")), pk.get("mercado", ""))
                pk["factor_hist"] = factor
                pk["prob"] = max(1, min(99, round(pk["prob"] * factor, 1)))
            except Exception:
                pass

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


def _armar_parlay(legs):
    """Calcula prob combinada, cuota y EV. La probabilidad de cada leg se
    CALIBRA con la tasa real del mercado (aprendizaje): 60% tasa real + 40%
    modelo, para que la prob combinada refleje lo que de verdad acierta."""
    prob = 1.0
    cuota = 1.0
    for l in legs:
        real = _rate_real_mercado(l.get("sport", ""), l.get("mercado", ""))
        p = l["prob"] if real is None else (l["prob"] * 0.4 + real * 0.6)
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


def _tarjeta_parlay(titulo, color, descripcion, parlay):
    _guardar_parlay(titulo, parlay)   # registra el parlay generado para aprender de él
    momio = _decimal_a_americano(parlay['cuota'])
    ganancia = round((parlay['cuota'] - 1) * 100)   # ganancia por cada $100 apostados
    # Rendimiento HISTÓRICO de este tipo de parlay (el cerebro aprendiendo)
    hist_html = ""
    try:
        from motors.parlay_brain import stats_de_tipo
        _h = stats_de_tipo(titulo)
        if _h and _h.get("total", 0) >= 2:
            _wc = "#22c55e" if _h["win_rate"] >= 50 else "#ef4444"
            hist_html = (f"  ·  <span style='color:{_wc}'>📊 histórico: {_h['win_rate']}% "
                         f"({_h['ganados']}/{_h['total']}) · ROI {_h['roi']:+.0f}%</span>")
    except Exception:
        pass
    st.markdown(
        f"<div style='background:#1e293b;border-left:5px solid {color};border-radius:10px;padding:14px;margin-bottom:6px'>"
        f"<div style='color:{color};font-weight:800;font-size:1.05rem'>{titulo}</div>"
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
        _edge = l["prob"] - _impl                      # valor = prob modelo − prob implícita
        _ecol = "#22c55e" if _edge >= 0 else "#ef4444"
        st.markdown(
            f"<div style='background:#0f172a;border-radius:6px;padding:6px 12px;margin:3px 0'>"
            f"{l['sport']} · <b>{l['pick']}</b> "
            f"<span style='color:#64748b'>({l['mercado']} · {l['evento']})</span> "
            f"<span style='float:right'>"
            f"<span style='color:{_ecol};font-size:0.78rem' title='valor = prob. modelo − prob. del momio'>valor {_edge:+.0f}%</span>  "
            f"<span style='color:#22c55e;font-weight:700'>{l['prob']:.0f}%</span></span></div>",
            unsafe_allow_html=True,
        )


def _sluggers_del_dia(top_n: int = 5) -> list:
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

    if not generar:
        st.caption("Pulsa **Generar** para analizar todo lo cargado y armar los parlays.")
        return

    with st.spinner(f"Analizando juegos ({dia_opt.lower()}) y armando parlays..."):
        pool = _recolectar_picks(dia_filtro)

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

    # ── 🎯 PARLAY ÓPTIMO (4 legs de MAYOR probabilidad real) ──────────────
    # 4 legs: mejor balance prob/pago. Toma la MEJOR leg calibrada por evento
    # (sin HR, 1 por evento), top 4 por probabilidad calibrada.
    def _prob_cal(l):
        real = _rate_real_mercado(l.get("sport", ""), l.get("mercado", ""))
        return l["prob"] if real is None else (l["prob"] * 0.4 + real * 0.6)

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
        _tarjeta_parlay("🔐 PARLAY DOBLE SEGURO", "#22d3ee",
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
        _tarjeta_parlay("🟢 PARLAY SEGURO", "#22c55e",
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
        _tarjeta_parlay("🟡 PARLAY VALOR", "#fbbf24",
                        "Picks seguros + el mejor candidato a Home Run (mayor pago)",
                        _armar_parlay(legs_valor))

    # ── Parlay BOMBA: las 3 mejores props de HR ──────────────────────────
    if len(hrs) >= 2:
        hrs.sort(key=lambda x: x["prob"], reverse=True)
        legs_bomba = hrs[:3]
        st.markdown("")
        _tarjeta_parlay("🔴 PARLAY BOMBA", "#ef4444",
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
        _tarjeta_parlay("🎯 PARLAY HR + FÚTBOL", "#e11d48",
                        "Sluggers top (home run) + mejores picks de fútbol — pago alto, tu combo favorito",
                        _armar_parlay(legs_hrfut))

    # ── ⚡ PARLAY SLUGGER DEL DÍA: basado en datos aprendidos del backtest ─────
    # Usa SOLO la memoria histórica de quién pegó HR en los últimos días,
    # calibrando la probabilidad con la tasa de acierto real (no la del motor).
    sluggers = _sluggers_del_dia(top_n=5)
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
        _tarjeta_parlay("⚡ PARLAY SLUGGER DEL DÍA", "#f59e0b", desc_slug, _armar_parlay(sluggers))

        # Detalle de cada slugger con su racha + datos Statcast
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
        _tarjeta_parlay(f"🟣 PARLAY GIGANTE ({len(legs_gigante)} legs)", "#a855f7",
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
        _tarjeta_parlay("💎 PARLAY MÁXIMO PAGO", "#06b6d4",
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
        _tarjeta_parlay("💎 PARLAY DE VALOR (+EV)", "#14b8a6",
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

    # ── 📊 BACKTEST DE PARLAYS: historial real y resolución ─────────────────
    st.markdown("---")
    st.markdown("#### 📊 Backtest de parlays generados")
    st.caption("Cada parlay que genera esta página se guarda automáticamente. "
               "Al terminar los juegos, resuelve para ver cuántos acertaste.")

    col_bt1, col_bt2 = st.columns(2)
    with col_bt1:
        if st.button("🔄 Auto-resolver parlays pendientes", use_container_width=True, key="bt_parlays_resolve"):
            with st.spinner("Cruzando resultados reales con legs del parlay..."):
                try:
                    from motors.box_score_resolver import resolver_todo
                    rr = resolver_todo()
                    st.success(f"Picks: {rr['mlb']} MLB + {rr['nba']} NBA resueltos")
                except Exception:
                    pass
                try:
                    from motors.parlay_brain import resolver_parlays_pendientes as _res_par
                    n_par = _res_par()
                    if n_par:
                        st.success(f"🎰 {n_par} parlay(s) resueltos")
                    else:
                        st.info("Aún no hay parlays con todas las legs resueltas.")
                except Exception as _ep:
                    st.error(f"Error: {_ep}")
            st.rerun()

    # Stats por tipo
    with col_bt2:
        try:
            from motors.parlay_brain import stats_por_tipo as _spt
            _stats = _spt()
            if _stats:
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
            _gan = sum(1 for h in _recientes if h.get("estado") == "ganado")
            _per = sum(1 for h in _recientes if h.get("estado") == "perdido")
            _pend = _total - _gan - _per
            _wr = round(_gan / (_gan + _per) * 100, 1) if (_gan + _per) > 0 else None
            _resumen = (f"**{_total}** parlays generados en 14 días — "
                        f"✅ {_gan} ganados · ❌ {_per} perdidos · ⏳ {_pend} pendientes"
                        + (f" · **{_wr}% win rate**" if _wr is not None else ""))
            st.markdown(_resumen)

            with st.expander("📅 Ver historial detallado", expanded=False):
                _by_day: dict = {}
                for h in reversed(_recientes):
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
