# -*- coding: utf-8 -*-
"""VISUAL FUTBOL TRIPLE — Streamlit nativo (sin raw HTML) V25"""
import streamlit as st


class VisualFutbolTriple:
    def __init__(self):
        pass

    def render(self, partido, idx, liga, tracker=None,
               analisis_heuristico=None, analisis_ia=None, **kwargs):
        local     = partido.get('home') or partido.get('local', 'Local')
        visitante = partido.get('away') or partido.get('visitante', 'Visitante')
        fecha     = partido.get('fecha_partido', '')
        odds      = partido.get('odds', {})
        moneyline = odds.get('moneyline', {})
        ml_loc    = moneyline.get('home', 'N/A')
        ml_emp    = moneyline.get('draw', 'N/A')
        ml_vis    = moneyline.get('away', 'N/A')
        ou        = odds.get('over_under', 'N/A')
        detalles  = odds.get('detalles', '')
        fase      = partido.get('fase', '')
        es_torneo = partido.get('es_torneo', False)

        # ── Encabezado ──────────────────────────────────────────────────────
        left, mid, right = st.columns([5, 2, 5])
        with left:
            logo = partido.get('local_logo', '')
            if logo:
                st.image(logo, width=28)
            rec = partido.get('local_record', '0-0-0')
            st.markdown(f"**{local}** `{rec}`")
        with mid:
            st.markdown(f"<div style='text-align:center;color:#9ca3af'>vs</div>",
                        unsafe_allow_html=True)
            if fecha:
                st.caption(f"📅 {fecha}")
            if fase:
                st.caption(f"🏆 {fase}")
        with right:
            logo2 = partido.get('visitante_logo', '')
            if logo2:
                st.image(logo2, width=28)
            rec2 = partido.get('visitante_record', '0-0-0')
            st.markdown(f"**{visitante}** `{rec2}`")

        # ── Cuotas ──────────────────────────────────────────────────────────
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("🏠 Local", ml_loc if ml_loc != 'N/A' else '—')
        with c2:
            st.metric("🤝 Empate", ml_emp if ml_emp != 'N/A' else '—')
        with c3:
            st.metric("✈️ Visita", ml_vis if ml_vis != 'N/A' else '—')
        with c4:
            st.metric("📊 O/U", str(ou))
        if detalles:
            st.caption(f"📋 {detalles}")

        # ── Análisis (auto-mostrado cuando existe) ───────────────────────────
        if analisis_heuristico:
            pick   = analisis_heuristico.get('pick', 'N/A')
            conf   = analisis_heuristico.get('confianza', 0)
            regla  = analisis_heuristico.get('regla', '')
            nota   = analisis_heuristico.get('nota', '')
            if conf >= 60:
                st.success(f"🎯 **Pick:** {pick}  |  Confianza: {conf:.0f}%  |  Regla #{regla}")
            elif conf >= 40:
                st.warning(f"📊 **Pick:** {pick}  |  Confianza: {conf:.0f}%  |  Regla #{regla}")
            else:
                st.info(f"⚪ {pick} (conf baja: {conf:.0f}%)")
            if nota:
                st.caption(f"ℹ️ {nota}")

        if analisis_ia:
            pick_ia = analisis_ia.get('pick', 'N/A')
            conf_ia = analisis_ia.get('confianza', 0)
            st.success(f"🤖 **IA:** {pick_ia} ({conf_ia}%)")

        # ── Botón IA (solo si no hay análisis IA) ───────────────────────────
        col_btn, _ = st.columns([2, 3])
        with col_btn:
            lbl = "🔄 Actualizar IA" if analisis_ia else "🤖 Análisis IA"
            if st.button(lbl, key=f"futbol_btn_{liga}_{idx}", use_container_width=True):
                return "analizar"

        return None
