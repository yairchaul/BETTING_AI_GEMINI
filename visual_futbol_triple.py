# -*- coding: utf-8 -*-
"""VISUAL FÚTBOL — Streamlit nativo (logos, cuotas, récords, fase) V25."""
import streamlit as st


def _hora_cdmx(iso, fecha_fallback=""):
    """Convierte un datetime ISO (UTC, de ESPN) a hora de Ciudad de México."""
    try:
        from datetime import datetime
        from zoneinfo import ZoneInfo
        s = str(iso).replace("Z", "").replace(" ", "T")   # acepta 'YYYY-MM-DD HH:MM' y con 'T'
        dt = datetime.strptime(s[:16], "%Y-%m-%dT%H:%M").replace(tzinfo=ZoneInfo("UTC"))
        meses = ["", "ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
        d = dt.astimezone(ZoneInfo("America/Mexico_City"))
        return f"{d.day} {meses[d.month]} {d.strftime('%H:%M')} (CDMX)"
    except Exception:
        return str(fecha_fallback)[:10]


def _signo_momio(v):
    """Formatea momio americano: positivos con '+', negativos con '-', vacío '—'."""
    s = str(v).strip()
    if s in ("N/A", "None", "", "—"):
        return "—"
    if s.startswith(("+", "-")):
        return s
    try:
        n = float(s)
        return f"+{int(n)}" if n > 0 else str(int(n))
    except Exception:
        return s


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
        ml_loc = _signo_momio(moneyline.get('home', moneyline.get('local', 'N/A')))
        ml_emp = _signo_momio(moneyline.get('draw', 'N/A'))
        ml_vis = _signo_momio(moneyline.get('away', moneyline.get('visitante', 'N/A')))
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
                _clock = partido.get('clock', '')
                _min_disp = f"<div style='color:#ef4444;font-weight:900;font-size:1.05rem'>{_clock}</div>" if _clock else ""
                st.markdown(
                    f"<div style='text-align:center;color:#fff;font-weight:800;font-size:1.6rem;margin-top:12px'>{marcador}</div>"
                    f"<div style='text-align:center;color:#ef4444;font-size:0.72rem'>🔴 EN VIVO</div>"
                    f"<div style='text-align:center'>{_min_disp}</div>",
                    unsafe_allow_html=True)
            else:
                st.markdown("<div style='text-align:center;color:#9ca3af;font-weight:800;font-size:1.3rem;margin-top:26px'>VS</div>",
                            unsafe_allow_html=True)
            _fh = partido.get('fecha_hora') or partido.get('date') or fecha
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

            # ── Motor 1 (pre-calibración) — sólo si difiere del pick actual ───
            pick_m1 = analisis_heuristico.get('pick_motor_1', '')
            conf_m1 = analisis_heuristico.get('conf_motor_1', 0)
            regla_m1 = analisis_heuristico.get('regla_motor_1', '')
            if pick_m1 and pick_m1 not in (pick, 'SIN DATOS', 'REVISAR DATOS'):
                st.markdown(
                    "<div style='background:#0f172a;border:1px solid #334155;border-left:3px solid #fbbf24;"
                    "border-radius:7px;padding:7px 12px;margin-top:4px;font-size:0.82rem'>"
                    f"<span style='color:#fbbf24;font-weight:700'>📐 Motor 1 (sin calibración):</span> "
                    f"<span style='color:#f1f5f9;font-weight:700'>{pick_m1}</span>"
                    f"<span style='color:#94a3b8'> · {conf_m1:.0f}%"
                    + (f" · Regla #{regla_m1}" if regla_m1 and regla_m1 != 99 else "")
                    + "</span></div>",
                    unsafe_allow_html=True)
            elif pick_m1 and pick_m1 == pick:
                st.caption(f"📐 Motor 1 = mismo pick ({pick_m1} · {conf_m1:.0f}%)")

            # ── Nota de forma reciente (avg goles actuales, NO histórico) ──────
            avg_l = analisis_heuristico.get('avg_goles_local', 0)
            avg_v = analisis_heuristico.get('avg_goles_visit', 0)
            liga_nota_banner = analisis_heuristico.get('liga_nota', '')
            if avg_l or avg_v:
                forma_txt = (f"📊 Forma reciente · {local[:10]}: avg {avg_l:.1f} goles · "
                             f"{visitante[:10]}: avg {avg_v:.1f} goles")
                if avg_l + avg_v > 3.0:
                    forma_txt += " — partido de ALTA anotación"
                elif avg_l + avg_v < 2.0:
                    forma_txt += " — partido DEFENSIVO esperado"
                st.caption(forma_txt)
            elif nota and 'ranking' in nota.lower():
                # Fallback FIFA ranking (torneos sin historial en DB)
                st.caption(f"ℹ️ {nota}")

            # ── H2H histórico (martj42/international_results) ────────────────
            h2h = analisis_heuristico.get('h2h_historico', {})
            if h2h and h2h.get('total', 0) >= 5:
                ult = h2h.get('ultimos', [])
                ult_str = "  ".join(
                    f"<span style='color:#94a3b8'>{u['fecha'][:7]} {u['resultado']}</span>"
                    for u in ult[:4]
                ) if ult else ""
                wc_l = h2h.get('wc_local', {})
                wc_v = h2h.get('wc_visita', {})
                wc_str = ""
                if wc_l.get('total_wc', 0) and wc_v.get('total_wc', 0):
                    wc_str = (
                        f" · <span style='color:#fbbf24'>WC: {local[:8]} "
                        f"W{wc_l.get('ganados',0)} "
                        f"vs {visitante[:8]} W{wc_v.get('ganados',0)}</span>"
                    )
                st.markdown(
                    f"<div style='background:#0f172a;border-radius:7px;padding:8px 12px;"
                    f"margin-top:5px;font-size:0.78rem'>"
                    f"<span style='color:#475569;font-size:0.7rem'>📜 HISTORIAL (no forma actual) — {h2h['total']} partidos hist.: </span>"
                    f"<span style='color:#22c55e'>{local[:10]} {h2h['pct_local']}%</span> · "
                    f"<span style='color:#fbbf24'>Empate {h2h['pct_empate']}%</span> · "
                    f"<span style='color:#ef4444'>{visitante[:10]} {h2h['pct_visita']}%</span> · "
                    f"<span style='color:#94a3b8'>avg {h2h['avg_goles']} gol/partido</span>"
                    f"{wc_str}"
                    f"{(' &nbsp;·&nbsp; ' + ult_str) if ult_str else ''}"
                    f"</div>", unsafe_allow_html=True)

            # ── Motor V2 (momentum/form) en paralelo ─────────────────────────
            motor_v2 = analisis_heuristico.get('motor_v2')
            if motor_v2 and motor_v2.get('pick') not in ('SIN DATOS', None):
                pick_v2 = motor_v2['pick']
                conf_v2 = motor_v2.get('confianza', 0)
                razon_v2 = motor_v2.get('razon', '')
                coinciden = pick_v2.lower().strip() == pick.lower().strip()
                if coinciden:
                    # Ambos motores de acuerdo → mostrar pick unificado con boost
                    st.markdown(
                        "<div style='background:#14532d33;border-left:4px solid #22c55e;"
                        "border-radius:7px;padding:7px 12px;margin-top:4px;font-size:0.82rem'>"
                        f"<span style='color:#22c55e;font-weight:700'>✅ Calibrado + Momentum coinciden: {pick_v2}</span>"
                        f"<span style='color:#94a3b8'> · Calibrado {conf:.0f}% · Momentum {conf_v2:.0f}%</span>"
                        "</div>", unsafe_allow_html=True)
                else:
                    # Discrepancia: mostrar ambos picks
                    st.markdown(
                        "<div style='background:#1e1b4b;border-left:4px solid #818cf8;"
                        "border-radius:7px;padding:7px 12px;margin-top:4px;font-size:0.82rem'>"
                        f"<span style='color:#818cf8;font-weight:700'>⚡ 2 OPCIONES:</span>"
                        f"<br><span style='color:#a5f3fc'>🔷 Calibrado (jerarquía+liga): <b>{pick}</b> · {conf:.0f}%</span>"
                        f"<br><span style='color:#fcd34d'>🔶 Momentum (forma reciente): <b>{pick_v2}</b> · {conf_v2:.0f}%</span>"
                        + (f"<br><span style='color:#64748b;font-size:0.75rem'>{razon_v2[:90]}</span>" if razon_v2 else "")
                        + "</div>", unsafe_allow_html=True)

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

            # ── PICKS MÚLTIPLES: todos los markets que califican independientemente ─
            picks_multi = analisis_heuristico.get('picks_multiples', [])
            # Deduplicar por tipo de mercado (ej: "OVER 1.5" y "OVER 1.5 goles" = mismo)
            def _tipo_mercado(p_str):
                pl = (p_str or '').lower()
                if "over 1.5 ht" in pl: return "over1.5ht"
                if "over 1.5" in pl:    return "over1.5"
                if "over 2.5" in pl:    return "over2.5"
                if "over 3.5" in pl:    return "over3.5"
                if "btts" in pl or "ambos" in pl: return "btts"
                if "under" in pl:       return "under"
                if "local (" in pl:     return "local"
                if "visitante (" in pl: return "visitante"
                return pl[:15]
            primary_tipo = _tipo_mercado(pick)
            picks_extra = [pm for pm in picks_multi
                           if _tipo_mercado(pm.get('pick', '')) != primary_tipo]
            if picks_extra:
                st.markdown(
                    "<div style='color:#94a3b8;font-size:0.72rem;margin:8px 0 4px 0'>"
                    "📋 <b>TAMBIÉN CALIFICAN</b> para este partido:</div>",
                    unsafe_allow_html=True)
                for pm in picks_extra:
                    _pc = pm.get('confianza', 0)
                    _pp = pm.get('pick', '')
                    _acc2 = "#22c55e" if _pc >= 65 else "#fbbf24" if _pc >= 55 else "#94a3b8"
                    st.markdown(
                        f"<div style='background:#0f172a;border-left:3px solid {_acc2};"
                        f"border-radius:7px;padding:7px 12px;margin:3px 0;display:flex;"
                        f"justify-content:space-between;align-items:center'>"
                        f"<span style='color:{_acc2};font-weight:700'>📌 {_pp}</span>"
                        f"<span style='color:#64748b;font-size:0.82rem'>{_pc:.0f}% confianza</span>"
                        f"</div>",
                        unsafe_allow_html=True)

            # ── MARCADOR CORRECTO (Dixon-Coles) ──────────────────────────────
            # Top-3 marcadores + heatmap de la matriz Poisson corregida (τ),
            # igual que los paneles del modelo profesional. Solo selecciones.
            mc = analisis_heuristico.get('marcador_correcto')
            if mc and mc.get('disponible'):
                top = mc.get('marcador_top', [])
                xgl, xgv = mc.get('xg_local'), mc.get('xg_visit')
                st.markdown(
                    f"<div style='color:#94a3b8;font-size:0.72rem;margin:12px 0 5px 0'>"
                    f"🎯 <b>MARCADOR CORRECTO</b> · modelo Dixon-Coles "
                    f"<span style='color:#64748b'>(xG {xgl} - {xgv})</span></div>",
                    unsafe_allow_html=True)
                _col = {"LOCAL": "#3b82f6", "EMPATE": "#94a3b8", "VISITANTE": "#ef4444"}
                chips = []
                for i, t in enumerate(top[:3]):
                    c = _col.get(t.get('resultado'), "#94a3b8")
                    borde = "border:2px solid #fbbf24;" if i == 0 else f"border:1px solid {c};"
                    chips.append(
                        f"<div style='background:#0f172a;{borde}border-radius:9px;"
                        f"padding:8px 16px;text-align:center;min-width:66px'>"
                        f"<div style='color:#fff;font-weight:900;font-size:1.25rem'>{t['marcador']}</div>"
                        f"<div style='color:{c};font-size:0.78rem;font-weight:700'>{t['pct']}%</div></div>")
                st.markdown(
                    f"<div style='display:flex;gap:8px;margin-bottom:8px'>{''.join(chips)}</div>",
                    unsafe_allow_html=True)
                # Heatmap 0-5 (filas = goles local, columnas = goles visitante)
                matriz = mc.get('matriz', [])
                if matriz:
                    N = min(6, len(matriz))
                    mx = max((matriz[i][j] for i in range(N) for j in range(N)), default=0) or 1
                    enc = "".join(
                        f"<td style='color:#64748b;font-size:0.6rem;text-align:center;padding:2px 6px'>{j}</td>"
                        for j in range(N))
                    filas_html = [f"<tr><td></td>{enc}</tr>"]
                    for i in range(N):
                        celdas = [f"<td style='color:#64748b;font-size:0.6rem;padding:2px 6px'>{i}</td>"]
                        for j in range(N):
                            p = matriz[i][j]
                            inten = p / mx
                            r = int(30 + inten * 225)
                            g = int(35 + inten * 25)
                            b = max(0, int(55 - inten * 45))
                            txt = "#fff" if inten > 0.35 else "#475569"
                            celdas.append(
                                f"<td style='background:rgb({r},{g},{b});color:{txt};"
                                f"font-size:0.62rem;font-weight:700;text-align:center;"
                                f"padding:4px 6px;border-radius:3px'>{p*100:.0f}</td>")
                        filas_html.append(f"<tr>{''.join(celdas)}</tr>")
                    st.markdown(
                        f"<div style='color:#64748b;font-size:0.6rem;margin-bottom:3px'>"
                        f"↓ {local} &nbsp;·&nbsp; → {visitante} &nbsp;·&nbsp; % por marcador</div>"
                        f"<table style='border-collapse:separate;border-spacing:2px;margin-bottom:4px'>"
                        f"{''.join(filas_html)}</table>",
                        unsafe_allow_html=True)
                st.caption("ℹ️ Ningún marcador exacto pasa de ~15-20%: el fútbol es así de aleatorio. "
                           "Es guía de escenarios, no certeza.")

            # ── Debug: ¿Por qué se eligió este mercado? ─────────────────────
            debug_reglas = analisis_heuristico.get('debug_reglas', [])
            wc_nota_debug = analisis_heuristico.get('wc_nota', '')
            liga_nota_debug = analisis_heuristico.get('liga_nota', '')
            if debug_reglas or wc_nota_debug or liga_nota_debug:
                with st.expander("🔍 ¿Por qué este pick? — Explicación de pesos", expanded=False):
                    if liga_nota_debug:
                        st.warning(f"📊 Calibración liga: {liga_nota_debug.split('| PICK CAMBIADO:')[0].strip()}")
                    if wc_nota_debug:
                        st.info(f"🌍 Calibración WC: {wc_nota_debug}")
                    if debug_reglas:
                        st.markdown("**Todas las reglas evaluadas:**")
                        for dr in sorted(debug_reglas, key=lambda x: (0 if x.get('es_principal') else 1, -x['confianza'])):
                            marca = "✅ **ELEGIDA**" if dr['es_principal'] else "⬜"
                            st.markdown(
                                f"{marca} Regla #{dr['regla']} — **{dr['pick']}** "
                                f"({dr['confianza']:.0f}%) · _{dr['descripcion']}_"
                            )
                    if motor_v2:
                        st.markdown("---")
                        st.markdown(f"**Motor V2 (momentum):** {motor_v2.get('pick','')} · {motor_v2.get('confianza',0):.0f}%")
                        st.caption(motor_v2.get('razon', ''))
                        v2_debug = motor_v2.get('debug', {})
                        if v2_debug:
                            cols = st.columns(4)
                            for i, (k, v) in enumerate(list(v2_debug.items())[:8]):
                                cols[i % 4].metric(k.replace('_', ' '), v)

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

        # ── 🔮 RESULTADO DEL PARTIDO (1X2 con empate) — ventana independiente ──
        try:
            from motors.predictor_1x2 import predecir_1x2
            r1x2 = predecir_1x2(local, visitante,
                                es_torneo=partido.get("es_torneo", False),
                                fase=partido.get("fase", ""))
            if r1x2:
                p = r1x2["prob_1x2"]
                emp_flag = " ⚠️ riesgo de empate" if r1x2.get("riesgo_empate") else ""
                st.markdown("##### 🔮 Resultado probable (1X2)")
                r1, r2, r3 = st.columns(3)
                r1.metric(f"🏠 {local[:10]}", f"{p['local']}%")
                r2.metric("🤝 Empate", f"{p['empate']}%")
                r3.metric(f"✈️ {visitante[:10]}", f"{p['visitante']}%")
                do = r1x2["doble_oportunidad"]
                st.info(f"🎯 Sugerencia: **{r1x2['sugerencia']}** "
                        f"· Doble oportunidad {do['mercado']} ({do['prob']}%)" + emp_flag)
        except Exception:
            pass

        # ── Análisis IA ─────────────────────────────────────────────────────
        if analisis_ia and not analisis_ia.get('error') and analisis_ia.get('pick') not in (None, '', 'N/A'):
            pick_ia = analisis_ia.get('pick', '')
            conf_ia = analisis_ia.get('confianza', 0)
            razon_ia = analisis_ia.get('razon', '')
            alerta_ia = analisis_ia.get('alerta', '')
            st.success(f"🤖 **IA:** {pick_ia} ({conf_ia}%)" + (f" — {razon_ia}" if razon_ia else ""))
            if alerta_ia:
                st.info(f"⚡ {alerta_ia}")
        elif analisis_ia and analisis_ia.get('error'):
            prov = analisis_ia.get('proveedor', '')
            razon_err = analisis_ia.get('razon', analisis_ia.get('error', ''))
            st.warning(f"⚠️ IA{' (' + prov + ')' if prov else ''}: {razon_err[:100]}")

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
