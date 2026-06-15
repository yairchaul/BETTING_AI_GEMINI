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

        # ── Encabezado (centrado, banderas grandes) ─────────────────────────
        def _bloque_equipo(nombre, logo, record):
            flag = (f"<img src='{logo}' width='68' height='68' "
                    "style='object-fit:contain;display:block;margin:0 auto 8px auto;"
                    "filter:drop-shadow(0 2px 6px rgba(0,0,0,0.4));border-radius:6px'>") if logo else \
                   "<div style='font-size:48px;text-align:center;margin-bottom:8px'>⚽</div>"
            rec_html = (f"<div style='color:#94a3b8;font-size:0.8rem'>{record}</div>"
                        if record and record != '0-0-0' else "")
            return (f"<div style='text-align:center'>{flag}"
                    f"<div style='font-weight:800;font-size:1.1rem;color:#f1f5f9;line-height:1.2'>{nombre}</div>"
                    f"{rec_html}</div>")

        left, mid, right = st.columns([5, 2, 5])
        with left:
            st.markdown(_bloque_equipo(local, logo_l, rec_l), unsafe_allow_html=True)
        with mid:
            marcador = partido.get('marcador', '')
            if marcador and partido.get('completado'):
                st.markdown(f"<div style='text-align:center;color:#fff;font-weight:800;font-size:1.6rem;margin-top:18px'>{marcador}</div>"
                            "<div style='text-align:center;color:#22c55e;font-size:0.72rem'>✅ FINAL</div>",
                            unsafe_allow_html=True)
            elif marcador and partido.get('en_vivo'):
                st.markdown(f"<div style='text-align:center;color:#fff;font-weight:800;font-size:1.6rem;margin-top:18px'>{marcador}</div>"
                            "<div style='text-align:center;color:#ef4444;font-size:0.72rem'>🔴 EN VIVO</div>",
                            unsafe_allow_html=True)
            else:
                st.markdown("<div style='text-align:center;color:#9ca3af;font-weight:800;font-size:1.3rem;margin-top:26px'>VS</div>",
                            unsafe_allow_html=True)
            if fecha:
                st.markdown(f"<div style='text-align:center;color:#94a3b8;font-size:0.72rem;margin-top:4px'>📅 {fecha}</div>",
                            unsafe_allow_html=True)
            if fase:
                st.markdown(f"<div style='text-align:center;color:#94a3b8;font-size:0.72rem'>🏆 {fase}</div>",
                            unsafe_allow_html=True)
        with right:
            st.markdown(_bloque_equipo(visitante, logo_v, rec_v), unsafe_allow_html=True)

        # Estadio
        venue = partido.get('venue', '')
        if venue:
            st.markdown(f"<div style='text-align:center;color:#94a3b8;font-size:0.75rem;margin-top:4px'>🏟️ {venue}</div>",
                        unsafe_allow_html=True)

        # ── Cuotas (1X2 + O/U) como chips con estilo ────────────────────────
        def _fmt(v):
            return str(v) if v not in ('N/A', None, '') else '—'

        chip = lambda titulo, valor, color: (
            f"<div style='flex:1;background:linear-gradient(160deg,#1e293b,#0f172a);"
            f"border:1px solid #334155;border-top:3px solid {color};border-radius:10px;"
            f"padding:8px 6px;text-align:center;margin:3px'>"
            f"<div style='color:#94a3b8;font-size:0.68rem;text-transform:uppercase;letter-spacing:.5px'>{titulo}</div>"
            f"<div style='color:#f1f5f9;font-size:1.15rem;font-weight:800;margin-top:2px'>{valor}</div></div>")

        st.markdown(
            "<div style='display:flex;justify-content:space-between;margin-top:6px'>"
            + chip(f"🏠 {local[:10]}", _fmt(ml_loc), "#3b82f6")
            + chip("🤝 Empate", _fmt(ml_emp), "#fbbf24")
            + chip(f"✈️ {visitante[:10]}", _fmt(ml_vis), "#ef4444")
            + chip("⚽ O/U", _fmt(ou), "#22c55e")
            + "</div>",
            unsafe_allow_html=True)
        if detalles:
            st.markdown(f"<div style='text-align:center;color:#64748b;font-size:0.72rem;margin-top:2px'>📋 {detalles}</div>",
                        unsafe_allow_html=True)

        # ── Análisis heurístico (auto-mostrado, banner estilizado) ──────────
        if analisis_heuristico:
            pick = analisis_heuristico.get('pick') or analisis_heuristico.get('recomendacion', 'N/A')
            conf = analisis_heuristico.get('confianza', 0)
            regla = analisis_heuristico.get('regla', '')
            nota = analisis_heuristico.get('nota', '')
            if conf >= 60:
                acc, ico = "#22c55e", "🎯"
            elif conf >= 40:
                acc, ico = "#fbbf24", "📊"
            else:
                acc, ico = "#64748b", "⚪"
            regla_txt = f" · Regla #{regla}" if regla else ""
            st.markdown(
                f"<div style='margin-top:8px;background:linear-gradient(90deg,{acc}22,transparent);"
                f"border-left:4px solid {acc};border-radius:8px;padding:10px 14px'>"
                f"<span style='color:{acc};font-weight:800;font-size:1.02rem'>{ico} {pick}</span>"
                f"<span style='color:#cbd5e1;font-size:0.85rem'>  ·  Confianza {conf:.0f}%{regla_txt}</span></div>",
                unsafe_allow_html=True)
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
