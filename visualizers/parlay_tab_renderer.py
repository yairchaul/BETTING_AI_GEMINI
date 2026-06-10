# -*- coding: utf-8 -*-
"""
PARLAY TAB RENDERER
Muestra el pool de picks calificados y los mejores parlays del día.
"""

import streamlit as st
from datetime import datetime
from motors.parlay_engine import ParlayEngine

SPORT_EMOJI = {
    "MLB":    "⚾",
    "NBA":    "🏀",
    "UFC":    "🥊",
    "SOCCER": "⚽",
}

TYPE_LABEL = {
    "HR_PROP":    "HR Prop",
    "MONEYLINE":  "Moneyline",
    "OVER_UNDER": "Over/Under",
    "HANDICAP":   "Handicap",
    "BTTS":       "Ambos anotan",
    "UFC_ML":     "Moneyline UFC",
}

RANK_LABEL = ["🥇", "🥈", "🥉"]


def _conf_color(conf: float) -> str:
    if conf >= 65:
        return "#22c55e"
    if conf >= 50:
        return "#f59e0b"
    return "#ef4444"


def _edge_color(edge: float) -> str:
    return "#22c55e" if edge >= 0 else "#ef4444"


def render_parlay_tab():
    st.header("🎯 PARLAYS DEL DÍA")
    st.caption(
        "Generados automáticamente desde los picks analizados. "
        "Solo se incluyen combinaciones con Expected Value (EV) positivo."
    )

    engine = ParlayEngine(
        min_legs=4,
        max_legs=6,
        min_parlay_prob=3.0,
        top_parlays=3,
        max_pool=15,
    )

    # ── Datos de sesión ───────────────────────────────────────────────────────
    mlb_partidos   = st.session_state.get("mlb_partidos", [])
    analisis_mlb   = st.session_state.get("analisis_mlb", {})
    analisis_nba   = st.session_state.get("analisis_nba", {})
    analisis_ufc   = st.session_state.get("analisis_ufc", {})
    analisis_futbol = st.session_state.get("analisis_futbol", {})

    pool = engine.construir_pool(
        mlb_partidos=mlb_partidos,
        analisis_mlb=analisis_mlb,
        analisis_nba=analisis_nba,
        analisis_ufc=analisis_ufc,
        analisis_futbol=analisis_futbol,
    )

    # ── Métricas resumen ──────────────────────────────────────────────────────
    col_a, col_b, col_c, col_d = st.columns(4)
    hr_picks  = sum(1 for p in pool if p["pick_type"] == "HR_PROP")
    ml_picks  = sum(1 for p in pool if p["pick_type"] in ("MONEYLINE", "UFC_ML"))
    ou_picks  = sum(1 for p in pool if p["pick_type"] in ("OVER_UNDER", "BTTS"))
    hc_picks  = sum(1 for p in pool if p["pick_type"] == "HANDICAP")
    col_a.metric("💣 HR Props", hr_picks)
    col_b.metric("📈 Moneylines", ml_picks)
    col_c.metric("🎯 Over/Under", ou_picks)
    col_d.metric("📊 Handicaps", hc_picks)

    st.divider()

    # ── Pool expandible ───────────────────────────────────────────────────────
    with st.expander(f"📋 Pool de picks calificados ({len(pool)} disponibles)", expanded=False):
        if not pool:
            st.info(
                "El pool está vacío. Carga y analiza los deportes con los botones "
                "de la barra lateral (🏀 NBA, ⚾ MLB, 🥊 UFC, ⚽ Fútbol) y luego "
                "presiona ANALIZAR en cada partido."
            )
        else:
            for p in pool:
                emoji = SPORT_EMOJI.get(p["sport"], "🎯")
                edge_str = f"+{p['edge']:.1f}%" if p["edge"] > 0 else f"{p['edge']:.1f}%"
                type_str = TYPE_LABEL.get(p["pick_type"], p["pick_type"])
                st.markdown(
                    f"{emoji} `{type_str}` **{p['pick']}**  "
                    f"— <span style='color:{_conf_color(p['confidence'])}'>"
                    f"**{p['confidence']:.0f}% conf**</span>  "
                    f"cuota **{p['cuota']:.2f}**  "
                    f"<span style='color:{_edge_color(p['edge'])}'>edge {edge_str}</span>",
                    unsafe_allow_html=True,
                )

    # ── Botón de generación ───────────────────────────────────────────────────
    st.markdown("")
    if st.button(
        "🔄 GENERAR PARLAYS DEL DÍA",
        type="primary",
        use_container_width=True,
        key="btn_generar_parlays",
    ):
        if len(pool) < 4:
            st.warning(
                f"Solo hay {len(pool)} picks calificados. "
                "Se necesitan al menos 4. Analiza más partidos."
            )
        else:
            with st.spinner("Calculando combinaciones óptimas..."):
                parlays = engine.generar_parlays(
                    mlb_partidos=mlb_partidos,
                    analisis_mlb=analisis_mlb,
                    analisis_nba=analisis_nba,
                    analisis_ufc=analisis_ufc,
                    analisis_futbol=analisis_futbol,
                )
            st.session_state["parlays_generados"] = parlays
            st.session_state["parlays_ts"] = datetime.now().strftime("%H:%M")

    parlays = st.session_state.get("parlays_generados", [])
    ts = st.session_state.get("parlays_ts", "")

    if ts:
        st.caption(f"Última generación: {ts}")

    if not parlays and pool:
        st.info(
            "Presiona el botón para calcular los mejores parlays con EV positivo. "
            f"Pool actual: {len(pool)} picks calificados."
        )
        return

    if not parlays:
        return

    st.markdown("")
    st.subheader(f"Top {len(parlays)} Parlays con EV Positivo")

    # ── Renderizar cada parlay ────────────────────────────────────────────────
    for i, parlay in enumerate(parlays):
        rank = RANK_LABEL[i] if i < 3 else f"#{i+1}"
        sports_icons = " · ".join(SPORT_EMOJI.get(s, s) for s in parlay["sports"])

        # Card header
        st.markdown(
            f"""
            <div style='
                background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%);
                border: 1px solid #4f46e5;
                border-radius: 14px;
                padding: 18px 22px;
                margin-bottom: 6px;
            '>
                <div style='
                    display: flex;
                    justify-content: space-between;
                    align-items: flex-start;
                    margin-bottom: 14px;
                '>
                    <div>
                        <span style='font-size:1.25rem; font-weight:800; color:white;'>
                            {rank} PARLAY {parlay['n_legs']} LEGS
                        </span>
                        &nbsp;
                        <span style='color:#a5b4fc; font-size:0.82rem;'>{sports_icons}</span>
                    </div>
                    <div style='text-align:right;'>
                        <div style='color:#fbbf24; font-size:1.7rem; font-weight:800; line-height:1;'>
                            {parlay['cuota_combinada']:.2f}x
                        </div>
                        <div style='color:#86efac; font-size:0.78rem; margin-top:2px;'>
                            EV +{parlay['ev_pct']:.1f}%
                        </div>
                    </div>
                </div>
            """,
            unsafe_allow_html=True,
        )

        # Legs
        for leg in parlay["legs"]:
            emoji = SPORT_EMOJI.get(leg["sport"], "🎯")
            type_lbl = TYPE_LABEL.get(leg["pick_type"], leg["pick_type"])
            conf_c = _conf_color(leg["confidence"])
            st.markdown(
                f"""
                <div style='
                    background: rgba(255,255,255,0.06);
                    border-radius: 8px;
                    padding: 9px 14px;
                    margin-bottom: 7px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                '>
                    <div>
                        <div style='color:#a5b4fc; font-size:0.72rem; margin-bottom:2px;'>
                            {emoji} {leg['sport']} · {type_lbl}
                        </div>
                        <div style='color:white; font-weight:600; font-size:0.95rem;'>
                            {leg['pick']}
                        </div>
                        <div style='color:#94a3b8; font-size:0.7rem; margin-top:1px;'>
                            {leg['evento']}
                        </div>
                    </div>
                    <div style='text-align:right; flex-shrink:0; margin-left:12px;'>
                        <div style='color:{conf_c}; font-weight:700; font-size:1rem;'>
                            {leg['confidence']:.0f}%
                        </div>
                        <div style='color:#94a3b8; font-size:0.75rem;'>
                            {leg['cuota']:.2f}x
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Footer stats
        st.markdown(
            f"""
                <div style='
                    margin-top: 12px;
                    padding-top: 10px;
                    border-top: 1px solid rgba(255,255,255,0.12);
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                '>
                    <div>
                        <div style='color:#a5b4fc; font-size:0.72rem;'>Prob. combinada</div>
                        <div style='color:white; font-weight:700;'>{parlay['prob_combinada']:.1f}%</div>
                    </div>
                    <div style='text-align:center;'>
                        <div style='color:#a5b4fc; font-size:0.72rem;'>Cuota total</div>
                        <div style='color:#fbbf24; font-size:1.3rem; font-weight:800;'>
                            {parlay['cuota_combinada']:.2f}x
                        </div>
                    </div>
                    <div style='text-align:right;'>
                        <div style='color:#a5b4fc; font-size:0.72rem;'>Expected Value</div>
                        <div style='color:#86efac; font-weight:700; font-size:1rem;'>
                            +{parlay['ev_pct']:.1f}%
                        </div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Botón guardar
        col_save, _ = st.columns([1, 3])
        with col_save:
            if st.button(
                f"💾 Guardar parlay #{i+1}",
                key=f"save_parlay_{i}",
                use_container_width=True,
            ):
                tracker = st.session_state.get("tracker")
                if tracker:
                    for leg in parlay["legs"]:
                        tracker.agregar_pick({
                            "partido": leg["evento"],
                            "pick": leg["pick"],
                            "cuota": leg["cuota"],
                            "deporte": leg["sport"],
                            "confianza": leg["confidence"],
                        })
                    nombre = f"Auto-Parlay {i+1} — {datetime.now().strftime('%d/%m/%Y')}"
                    tracker.guardar_parlay(nombre=nombre)
                    st.success(f"✅ '{nombre}' guardado en el tracker")
                    st.rerun()
                else:
                    st.error("Tracker no disponible")

        st.markdown("<br>", unsafe_allow_html=True)

    # ── Advertencia informativa ───────────────────────────────────────────────
    st.info(
        "📌 **Nota**: El EV se calcula con las probabilidades estimadas por los motores "
        "heurísticos del sistema. A mayor número de deportes analizados, mejor calidad "
        "del parlay. Las cuotas mostradas son estimadas — verifica las reales en tu "
        "sportsbook antes de apostar."
    )
