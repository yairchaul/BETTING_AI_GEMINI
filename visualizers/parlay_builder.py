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
            if mejor:
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
            # Moneyline
            pool.append({
                "sport": "⚾ MLB", "evento": evento, "mercado": "MONEYLINE",
                "pick": f"Gana {r.get('pick','')}", "prob": r.get("confianza", 0),
                "tipo": "SEGURO", "cuota": cuota_ml,
            })
            # Over/Under
            if r.get("ou_pick"):
                pool.append({
                    "sport": "⚾ MLB", "evento": evento, "mercado": "TOTAL",
                    "pick": f"{r['ou_pick']} {r.get('ou_linea_ajustada','')}",
                    "prob": r.get("ou_confianza", 0), "tipo": "SEGURO", "cuota": 1.90,
                })
            # Strikeouts del lanzador (Over/Under)
            for kp in r.get("k_picks", []):
                pool.append({
                    "sport": "⚾ MLB", "evento": evento, "mercado": "PONCHES (K)",
                    "pick": f"{kp.get('pitcher','?')} {kp.get('prediccion','')} {kp.get('linea','')} K",
                    "prob": kp.get("confianza", 0), "tipo": "SEGURO", "cuota": 1.85,
                })
            # Total de bases (Over 1.5) — props de mediana probabilidad
            for tb in r.get("tb_picks", [])[:3]:
                if tb.get("prediccion") == "OVER" and tb.get("confianza", 0) >= 55:
                    pool.append({
                        "sport": "⚾ MLB", "evento": evento, "mercado": "TOTAL BASES",
                        "pick": f"{tb.get('jugador','?')} {tb.get('pick','')}",
                        "prob": tb.get("confianza", 0), "tipo": "VALOR", "cuota": 1.95,
                    })
            # HR candidates (props de mayor pago)
            for hr in r.get("hr_candidates", []):
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
        for idx, c in enumerate(ss.get("ufc_combates", []) or []):
            if not _es_del_dia(c):
                continue
            res = ss.get("analisis_ufc", {}).get(f"{c.get('peleador1',{}).get('nombre','')}_vs_{c.get('peleador2',{}).get('nombre','')}")
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
    try:
        from motors.futbol_analyzer_jerarquico import analizar_futbol_jerarquico
        for liga, partidos in (ss.get("futbol_partidos", {}) or {}).items():
            for p in partidos or []:
                if not _es_del_dia(p):
                    continue
                r = analizar_futbol_jerarquico(
                    p.get("home") or p.get("local", ""),
                    p.get("away") or p.get("visitante", ""),
                    es_torneo=p.get("es_torneo", False), fase=p.get("fase", ""),
                )
                pick = r.get("pick", "")
                if not pick or "revisar" in pick.lower():
                    continue
                evento_f = f"{p.get('home', p.get('local','?'))} vs {p.get('away', p.get('visitante','?'))}"
                # Pick primario (el más seguro de la jerarquía)
                pool.append({
                    "sport": "⚽ FÚTBOL", "evento": evento_f,
                    "mercado": "1X2/Goles", "pick": pick,
                    "prob": r.get("confianza", 0),
                    "tipo": "SEGURO" if r.get("confianza", 0) >= 55 else "VALOR",
                    "cuota": 2.0,
                })
                # Pick COMBINADO (gana + Over) — mayor pago, para el parlay agresivo
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


def _armar_parlay(legs):
    """Calcula prob combinada, cuota y EV de un conjunto de legs."""
    prob = 1.0
    cuota = 1.0
    for l in legs:
        prob *= max(0.01, l["prob"] / 100.0)
        cuota *= l.get("cuota", 1.9)
    ev = prob * cuota - 1.0
    return {
        "legs": legs,
        "prob": round(prob * 100, 2),
        "cuota": round(cuota, 2),
        "ev_pct": round(ev * 100, 1),
    }


def _tarjeta_parlay(titulo, color, descripcion, parlay):
    momio = _decimal_a_americano(parlay['cuota'])
    ganancia = round((parlay['cuota'] - 1) * 100)   # ganancia por cada $100 apostados
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
        f"<div style='color:#64748b;font-size:0.8rem;margin-top:6px'>💵 $100 → <b style='color:#22c55e'>${ganancia:,}</b> de ganancia ({len(parlay['legs'])} legs)</div>"
        f"</div>",
        unsafe_allow_html=True,
    )
    for l in parlay["legs"]:
        st.markdown(
            f"<div style='background:#0f172a;border-radius:6px;padding:6px 12px;margin:3px 0'>"
            f"{l['sport']} · <b>{l['pick']}</b> "
            f"<span style='color:#64748b'>({l['mercado']} · {l['evento']})</span> "
            f"<span style='float:right;color:#22c55e'>{l['prob']:.0f}%</span></div>",
            unsafe_allow_html=True,
        )


def render_parlay_tab():
    """Renderiza la pestaña de parlays cross-deporte."""
    st.header("🎰 PARLAYS — Lo mejor de todos los deportes")
    st.caption("Combina los picks más probables de NBA, MLB, UFC y Fútbol en parlays estructurados.")

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

    # ── Parlay SEGURO: top picks de alta prob, máx 1 por evento ──────────
    seguros = [p for p in pool if p["prob"] >= min_prob and p["mercado"] != "HOME RUN"]
    vistos_evento = set()
    legs_seguro = []
    for p in seguros:
        if p["evento"] in vistos_evento:
            continue
        vistos_evento.add(p["evento"])
        legs_seguro.append(p)
        if len(legs_seguro) >= n_legs:
            break

    if len(legs_seguro) >= 2:
        _tarjeta_parlay("🟢 PARLAY SEGURO", "#22c55e",
                        f"{len(legs_seguro)} picks de mayor probabilidad, distintos eventos",
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

    # ── Tabla completa del pool ──────────────────────────────────────────
    st.markdown("---")
    with st.expander(f"📋 Ver los {len(pool)} picks analizados", expanded=False):
        st.table([
            {"Deporte": p["sport"], "Pick": p["pick"], "Mercado": p["mercado"],
             "Prob": f"{p['prob']:.0f}%", "Evento": p["evento"]}
            for p in pool
        ])
