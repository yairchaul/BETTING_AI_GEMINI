# -*- coding: utf-8 -*-
"""VISUAL FÚTBOL — Streamlit nativo (logos, cuotas, récords, fase) V25."""
import streamlit as st


class VisualFutbolTriple:
    def __init__(self):
        pass

    def render(self, partido, idx, liga, tracker=None,
               analisis_heuristico=None, analisis_ia=None, **kwargs):
        # Acepta el nombre con o sin acento (compatibilidad con código viejo)
        if analisis_heuristico is None:
            analisis_heuristico = kwargs.get('analisis_heurístico') or kwargs.get('analisis_gemini')

        local = partido.get('home') or partido.get('local', 'Local')
        visitante = partido.get('away') or partido.get('visitante', 'Visitante')
        fecha = partido.get('fecha_partido', '') or partido.get('fecha', '')
        odds = partido.get('odds', {}) or {}
        moneyline = odds.get('moneyline', {}) if isinstance(odds.get('moneyline'), dict) else {}
        ml_loc = moneyline.get('home', moneyline.get('local', 'N/A'))
        ml_emp = moneyline.get('draw', 'N/A')
        ml_vis = moneyline.get('away', moneyline.get('visitante', 'N/A'))
        ou = odds.get('over_under', 'N/A')
        detalles = odds.get('detalles', '')
        fase = partido.get('fase', '')
        logo_l = partido.get('local_logo', '')
        logo_v = partido.get('visitante_logo', '')
        rec_l = partido.get('local_record', '')
        rec_v = partido.get('visitante_record', '')

        # ── Encabezado ──────────────────────────────────────────────────────
        left, mid, right = st.columns([5, 2, 5])
        with left:
            if logo_l:
                st.image(logo_l, width=34)
            st.markdown(f"**{local}** " + (f"`{rec_l}`" if rec_l and rec_l != '0-0-0' else ""))
        with mid:
            marcador = partido.get('marcador', '')
            if marcador and partido.get('completado'):
                st.markdown(f"<div style='text-align:center;color:#fff;font-weight:800;font-size:1.4rem'>{marcador}</div>"
                            "<div style='text-align:center;color:#22c55e;font-size:0.7rem'>✅ FINAL</div>",
                            unsafe_allow_html=True)
            elif marcador and partido.get('en_vivo'):
                st.markdown(f"<div style='text-align:center;color:#fff;font-weight:800;font-size:1.4rem'>{marcador}</div>"
                            "<div style='text-align:center;color:#ef4444;font-size:0.7rem'>🔴 EN VIVO</div>",
                            unsafe_allow_html=True)
            else:
                st.markdown("<div style='text-align:center;color:#9ca3af;font-weight:700'>vs</div>",
                            unsafe_allow_html=True)
            if fecha:
                st.caption(f"📅 {fecha}")
            if fase:
                st.caption(f"🏆 {fase}")
        with right:
            if logo_v:
                st.image(logo_v, width=34)
            st.markdown(f"**{visitante}** " + (f"`{rec_v}`" if rec_v and rec_v != '0-0-0' else ""))

        # Estadio
        venue = partido.get('venue', '')
        if venue:
            st.caption(f"🏟️ {venue}")

        # ── Cuotas (1X2 + O/U) ──────────────────────────────────────────────
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(f"🏠 {local[:12]}", ml_loc if ml_loc not in ('N/A', None) else '—')
        c2.metric("🤝 Empate", ml_emp if ml_emp not in ('N/A', None) else '—')
        c3.metric(f"✈️ {visitante[:12]}", ml_vis if ml_vis not in ('N/A', None) else '—')
        c4.metric("⚽ O/U goles", str(ou))
        if detalles:
            st.caption(f"📋 {detalles}")

        # ── Análisis heurístico (auto-mostrado) ─────────────────────────────
        if analisis_heuristico:
            pick = analisis_heuristico.get('pick') or analisis_heuristico.get('recomendacion', 'N/A')
            conf = analisis_heuristico.get('confianza', 0)
            regla = analisis_heuristico.get('regla', '')
            nota = analisis_heuristico.get('nota', '')
            if conf >= 60:
                st.success(f"🎯 **Pick:** {pick}  |  Confianza: {conf:.0f}%" + (f"  |  Regla #{regla}" if regla else ""))
            elif conf >= 40:
                st.warning(f"📊 **Pick:** {pick}  |  Confianza: {conf:.0f}%" + (f"  |  Regla #{regla}" if regla else ""))
            else:
                st.info(f"⚪ {pick} (confianza baja: {conf:.0f}%)")
            if nota:
                st.caption(f"ℹ️ {nota}")

            # ── Resultado del pick (si el partido ya terminó) ────────────────
            if partido.get('completado') and partido.get('goles_local') is not None:
                gl = int(partido.get('goles_local', 0))
                gv = int(partido.get('goles_visitante', 0))
                total_g = gl + gv
                pl = str(pick).lower()
                acierto = None
                if 'btts' in pl or 'ambos' in pl:
                    acierto = gl > 0 and gv > 0
                elif 'over 2.5' in pl or 'over 3.5' in pl:
                    linea_g = 2.5 if '2.5' in pl else 3.5
                    acierto = total_g > linea_g
                elif 'over 1.5' in pl:
                    acierto = total_g > 1.5
                elif 'empate' in pl:
                    acierto = gl == gv
                elif local.lower() in pl:
                    acierto = gl > gv
                elif visitante.lower() in pl:
                    acierto = gv > gl
                if acierto is True:
                    st.success(f"✅ PICK ACERTADO — resultado {gl}-{gv}")
                elif acierto is False:
                    st.error(f"❌ Pick fallado — resultado {gl}-{gv}")

        # ── Análisis IA ─────────────────────────────────────────────────────
        if analisis_ia:
            pick_ia = analisis_ia.get('pick', 'N/A')
            conf_ia = analisis_ia.get('confianza', 0)
            razon_ia = analisis_ia.get('razon', '')
            st.success(f"🤖 **IA:** {pick_ia} ({conf_ia}%)" + (f" — {razon_ia}" if razon_ia else ""))

        # ── Botón IA ────────────────────────────────────────────────────────
        col_btn, _ = st.columns([2, 3])
        with col_btn:
            lbl = "🔄 Actualizar IA" if analisis_ia else "🤖 Análisis IA"
            if st.button(lbl, key=f"futbol_btn_{liga}_{idx}", use_container_width=True):
                return "analizar"

        return None
