# -*- coding: utf-8 -*-
"""VISUAL FÚTBOL — Streamlit nativo (logos, cuotas, récords, fase) V25."""
import streamlit as st


def _hora_cdmx(iso, fecha_fallback=""):
    """Convierte un datetime ISO (UTC, de ESPN) a hora de Ciudad de México."""
    try:
        from datetime import datetime
        from zoneinfo import ZoneInfo
        s = str(iso).replace("Z", "")
        dt = datetime.strptime(s[:16], "%Y-%m-%dT%H:%M").replace(tzinfo=ZoneInfo("UTC"))
        meses = ["", "ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
        d = dt.astimezone(ZoneInfo("America/Mexico_City"))
        return f"{d.day} {meses[d.month]} {d.strftime('%H:%M')} (CDMX)"
    except Exception:
        return str(fecha_fallback)[:10]


class VisualFutbolTriple:
    def __init__(self):
        pass

    def render(self, partido, idx, liga, tracker=None,
               analisis_heuristico=None, analisis_ia=None, mercados=None, **kwargs):
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

        # ── Encabezado (centrado, banderas grandes + momio debajo de cada equipo) ─
        def _bloque_equipo(nombre, logo, record, momio=None):
            flag = (f"<img src='{logo}' width='68' height='68' "
                    "style='object-fit:contain;display:block;margin:0 auto 8px auto;"
                    "filter:drop-shadow(0 2px 6px rgba(0,0,0,0.4));border-radius:6px'>") if logo else \
                   "<div style='font-size:48px;text-align:center;margin-bottom:8px'>⚽</div>"
            rec_html = (f"<div style='color:#94a3b8;font-size:0.8rem'>{record}</div>"
                        if record and record != '0-0-0' else "")
            if momio and str(momio) not in ('N/A', 'None', '', '—'):
                momio_html = ("<div style='margin-top:6px;display:inline-block;padding:2px 14px;border-radius:14px;"
                              "background:rgba(34,197,94,0.15);border:1px solid rgba(34,197,94,0.55);"
                              f"color:#22c55e;font-weight:800;font-size:1.05rem'>{momio}</div>")
            else:
                momio_html = "<div style='margin-top:6px;color:#64748b;font-size:0.95rem'>—</div>"
            return (f"<div style='text-align:center'>{flag}"
                    f"<div style='font-weight:800;font-size:1.1rem;color:#f1f5f9;line-height:1.2'>{nombre}</div>"
                    f"{rec_html}{momio_html}</div>")

        left, mid, right = st.columns([5, 2, 5])
        with left:
            st.markdown(_bloque_equipo(local, logo_l, rec_l, ml_loc), unsafe_allow_html=True)
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
            _fh = partido.get('fecha_hora') or partido.get('date') or ''
            _fecha_disp = _hora_cdmx(_fh, fecha) if _fh else fecha
            if _fecha_disp:
                st.markdown(f"<div style='text-align:center;color:#94a3b8;font-size:0.72rem;margin-top:4px'>📅 {_fecha_disp}</div>",
                            unsafe_allow_html=True)
            if fase:
                st.markdown(f"<div style='text-align:center;color:#94a3b8;font-size:0.72rem'>🏆 {fase}</div>",
                            unsafe_allow_html=True)
        with right:
            st.markdown(_bloque_equipo(visitante, logo_v, rec_v, ml_vis), unsafe_allow_html=True)

        # Estadio
        venue = partido.get('venue', '')
        if venue:
            st.markdown(f"<div style='text-align:center;color:#94a3b8;font-size:0.75rem;margin-top:4px'>🏟️ {venue}</div>",
                        unsafe_allow_html=True)

        # ── Cuotas (1X2 + O/U) como chips con estilo ────────────────────────
        def _fmt(v):
            return str(v) if v not in ('N/A', None, '') else '—'

        # O/U: si el pick del motor es OVER/UNDER, mostrar el lado; si no, la línea
        _pick_txt = ""
        if analisis_heuristico:
            _pick_txt = str(analisis_heuristico.get('pick') or analisis_heuristico.get('recomendacion', '')).upper()
        if "OVER" in _pick_txt:
            import re as _re
            _m = _re.search(r"OVER\s*(\d+\.?\d*)", _pick_txt)
            ou_label, ou_val = "⚽ Recom.", f"OVER {_m.group(1)}" if _m else f"OVER {_fmt(ou)}"
        elif "UNDER" in _pick_txt:
            import re as _re
            _m = _re.search(r"UNDER\s*(\d+\.?\d*)", _pick_txt)
            ou_label, ou_val = "⚽ Recom.", f"UNDER {_m.group(1)}" if _m else f"UNDER {_fmt(ou)}"
        else:
            ou_label, ou_val = "⚽ Línea O/U", _fmt(ou)

        chip = lambda titulo, valor, color: (
            f"<div style='flex:1;background:linear-gradient(160deg,#1e293b,#0f172a);"
            f"border:1px solid #334155;border-top:3px solid {color};border-radius:10px;"
            f"padding:8px 6px;text-align:center;margin:3px'>"
            f"<div style='color:#94a3b8;font-size:0.68rem;text-transform:uppercase;letter-spacing:.5px'>{titulo}</div>"
            f"<div style='color:#f1f5f9;font-size:1.15rem;font-weight:800;margin-top:2px'>{valor}</div></div>")

        # Los momios 1X2 de local/visita ya van debajo de cada equipo; aquí solo
        # el empate y el O/U (evita duplicar).
        st.markdown(
            "<div style='display:flex;justify-content:center;gap:8px;margin-top:6px'>"
            + chip("🤝 Empate", _fmt(ml_emp), "#fbbf24")
            + chip(ou_label, ou_val, "#22c55e")
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

            # ── Combinada de MAYOR PAGO (gana + Over) si el favorito es claro ──
            for _op in (analisis_heuristico.get('todas_opciones') or []):
                if _op.get('combo'):
                    st.markdown(
                        "<div style='margin-top:4px;background:linear-gradient(90deg,#e11d4822,transparent);"
                        "border-left:4px solid #e11d48;border-radius:8px;padding:8px 14px'>"
                        f"<span style='color:#fb7185;font-weight:800'>💰 Combinada (más pago): {_op['pick']}</span>"
                        f"<span style='color:#cbd5e1;font-size:0.85rem'>  ·  {_op.get('confianza',0):.0f}%</span></div>",
                        unsafe_allow_html=True)
                    break

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

        # ── 📊 Mercados completos (al pulsar "Analizar IA") ──────────────────
        if mercados:
            ml = mercados.get("moneyline", {})
            ou = mercados.get("over_under", {})
            bt = mercados.get("btts", {})
            st.markdown("##### 📊 Mercados (análisis IA)")
            m1, m2, m3 = st.columns(3)
            m1.metric(f"🏠 {local[:10]}", f"{ml.get('local',0)}%")
            m2.metric("🤝 Empate", f"{ml.get('empate',0)}%")
            m3.metric(f"✈️ {visitante[:10]}", f"{ml.get('visitante',0)}%")
            n1, n2, n3, n4 = st.columns(4)
            n1.metric("⚽ Over 2.5", f"{ou.get('over_2.5',0)}%")
            n2.metric("🧊 Under 2.5", f"{ou.get('under_2.5',0)}%")
            n3.metric("🤝 BTTS Sí", f"{bt.get('si',0)}%")
            n4.metric("🚫 BTTS No", f"{bt.get('no',0)}%")
            # Goleadores
            gol = mercados.get("goleadores", {})
            golead = (gol.get("local", []) + gol.get("visitante", []))
            if golead:
                top = sorted(golead, key=lambda x: x.get("prob", 0), reverse=True)[:4]
                chips = "  ".join(f"🎯 {g['jugador']} {g['prob']}%" for g in top)
                st.markdown(f"<div style='color:#cbd5e1;font-size:0.85rem;margin-top:4px'>"
                            f"<b>Posibles goleadores:</b> {chips}</div>", unsafe_allow_html=True)
            st.caption(f"Modelo Poisson · xG {mercados.get('xg_local','?')} - {mercados.get('xg_visitante','?')} "
                       f"· fuente: {mercados.get('fuente','')}")

        # ── Análisis IA ─────────────────────────────────────────────────────
        if analisis_ia:
            pick_ia = analisis_ia.get('pick', 'N/A')
            conf_ia = analisis_ia.get('confianza', 0)
            razon_ia = analisis_ia.get('razon', '')
            st.success(f"🤖 **IA:** {pick_ia} ({conf_ia}%)" + (f" — {razon_ia}" if razon_ia else ""))

        # ── ⚽ Goleadores probables (anota en el partido) ────────────────────
        try:
            from motors.futbol_props import obtener_goleadores_partido
            gol = obtener_goleadores_partido(local, visitante)
            if gol["local"] or gol["visitante"]:
                with st.expander("⚽ ¿Quién puede anotar? (goleadores probables)", expanded=False):
                    gc1, gc2 = st.columns(2)
                    for col, lado, eq in ((gc1, "local", local), (gc2, "visitante", visitante)):
                        with col:
                            st.markdown(f"**{eq}**")
                            if gol[lado]:
                                for g in gol[lado]:
                                    color = "#22c55e" if g["prob"] >= 55 else "#fbbf24" if g["prob"] >= 45 else "#94a3b8"
                                    st.markdown(
                                        f"🎯 **{g['jugador']}** — Anota "
                                        f"<span style='color:{color};font-weight:800'>{g['prob']}%</span>",
                                        unsafe_allow_html=True)
                            else:
                                st.caption("Sin goleadores destacados en la base.")
        except Exception as _gpe:
            pass

        # ── Botón IA ────────────────────────────────────────────────────────
        col_btn, _ = st.columns([2, 3])
        with col_btn:
            lbl = "🔄 Actualizar análisis IA" if (analisis_ia or mercados) else "🤖 Analizar IA"
            if st.button(lbl, key=f"futbol_btn_{liga}_{idx}", use_container_width=True):
                return "analizar"

        return None
