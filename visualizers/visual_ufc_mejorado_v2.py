# -*- coding: utf-8 -*-
"""
VISUAL UFC MEJORADO V2 - Muestra TODAS las stats extraídas del scraper
Optimizado para mostrar: SLpM, Str.Acc, TD Avg, TD Def, Sub Avg, etc.
"""

import re
import streamlit as st

class VisualUFCMejoradoV2:
    def __init__(self):
        self.colores = {
            'local': '#FF6B35',
            'visitante': '#0066CC',
            'green': '#4CAF50',
            'orange': '#FF9800',
            'blue': '#2196F3',
            'red': '#f44336',
            'gold': '#FFD700',
            'yellow': '#FFC107'
        }
    
    def render(self, combate, idx, tracker=None, 
                datos_peleador1=None, datos_peleador2=None,
                analisis_ufc=None, analisis_gemini=None, analisis_premium=None):
        
        with st.container():
            if idx > 0:
                st.markdown("---")
            
            evento = combate.get('evento', 'UFC Event')
            fecha = combate.get('fecha', 'Próximamente')
            
            # Usar datos del scraper si están disponibles
            if datos_peleador1 and datos_peleador2:
                p1 = datos_peleador1
                p2 = datos_peleador2
            else:
                p1 = combate.get('peleador1', {})
                p2 = combate.get('peleador2', {})
            
            p1_photo = p1.get('photo', '')
            p2_photo = p2.get('photo', '')
            # Asegurar que tenemos todas las stats necesarias
            p1 = self._completar_datos(p1)
            p2 = self._completar_datos(p2)
            
            p1_ko_rate = p1.get('ko_rate', 0.0) * 100
            p2_ko_rate = p2.get('ko_rate', 0.0) * 100
            
            # Encabezado
            st.markdown(f"""
            <div style="background-color: #1E1E1E; padding: 20px; border-radius: 10px; border-left: 5px solid #FFD700;">
                <span style="color: #FFD700; font-weight: bold; font-size: 24px;">🥊 {evento}</span>
                <span style="color: #888; float: right;">📅 {fecha}</span>
            </div>
            """, unsafe_allow_html=True)
            
            # Peleadores con datos físicos COMPLETOS
            col1, col2, col3 = st.columns([2, 1, 2])
            
            with col1:
                odds1 = p1.get('odds', 'N/A')
                st.markdown(f"## 🔴 {p1.get('nombre', 'Desconocido')}")
                if odds1 and str(odds1) not in ('N/A', 'None', ''):
                    st.markdown(
                        f"<div style='display:inline-block;margin:2px 0 6px 0;padding:3px 14px;border-radius:16px;"
                        f"background:rgba(59,130,246,0.15);border:1px solid rgba(59,130,246,0.45)'>"
                        f"<span style='color:#3b82f6;font-weight:800;font-size:1.0rem'>🎲 {odds1}</span></div>",
                        unsafe_allow_html=True)
                if p1_photo:
                    st.image(p1_photo, width=100) # Display photo
                st.markdown(f"📊 **Récord:** {p1.get('record', '0-0-0')}")
                
                # Datos físicos
                st.markdown(f"""
                <div style="background-color: #2A2A2A; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                    <p style='font-size: 13px; color: #AAA; margin: 2px 0;'>
                    📏 <strong>Altura:</strong> {p1.get('altura', 'N/A')} | 
                    ⚖️ <strong>Peso:</strong> {p1.get('peso', 'N/A')}
                    </p>
                    <p style='font-size: 13px; color: #AAA; margin: 2px 0;'>
                    📏 <strong>Alcance:</strong> {p1.get('alcance', 'N/A')} | 
                    🥊 <strong>Postura:</strong> {p1.get('postura', 'Desconocida')}
                    </p>
                    <p style='font-size: 13px; color: #FFD700; margin: 2px 0;'>
                    💥 <strong>KO Rate:</strong> {p1_ko_rate:.1f}% | 
                    🔥 <strong>Win Rate:</strong> {p1.get('win_rate', 0):.0f}%
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                # Estadísticas de carrera COMPLETAS
                self._render_stats_expander(p1)
            
            with col2:
                st.markdown("<h1 style='text-align: center; color: #666;'>VS</h1>", unsafe_allow_html=True)
                
                # Comparación de stats clave
                st.markdown("""
                <div style="background-color: #2A2A2A; padding: 10px; border-radius: 5px; margin-top: 20px;">
                    <p style='font-size: 12px; color: #AAA; text-align: center; margin: 0;'>
                    📊 COMPARACIÓN
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                # Diferencia de edad
                edad1 = p1.get('edad', 0)
                edad2 = p2.get('edad', 0)
                if edad1 and edad2:
                    diff_edad = abs(edad1 - edad2)
                    ventaja = "P1" if edad1 < edad2 else "P2" if edad2 < edad1 else "Igual"
                    st.markdown(f"<p style='font-size: 11px; text-align: center; color: #888;'>📅 Diff Edad: {diff_edad} años<br>Ventaja: {ventaja}</p>", unsafe_allow_html=True)
                
                # Diferencia de altura
                altura1 = self._parse_height_to_cm(p1.get('altura', '0'))
                altura2 = self._parse_height_to_cm(p2.get('altura', '0'))
                if altura1 > 0 and altura2 > 0:
                    diff_altura = abs(altura1 - altura2)
                    ventaja_alt = p1.get('nombre') if altura1 > altura2 else p2.get('nombre') if altura2 > altura1 else "Igual"
                    st.markdown(f"<p style='font-size: 11px; text-align: center; color: #888;'>📏 Diff Altura: {diff_altura:.1f} cm<br>Ventaja: {ventaja_alt}</p>", unsafe_allow_html=True)

                # Diferencia de alcance
                alcance1 = self._parse_reach_to_cm(p1.get('alcance', '0'))
                alcance2 = self._parse_reach_to_cm(p2.get('alcance', '0'))
                if alcance1 > 0 and alcance2 > 0:
                    diff_alcance = abs(alcance1 - alcance2)
                    ventaja_alc = p1.get('nombre') if alcance1 > alcance2 else p2.get('nombre') if alcance2 > alcance1 else "Igual"
                    st.markdown(f"<p style='font-size: 11px; text-align: center; color: #888;'>📏 Diff Alcance: {diff_alcance:.1f} cm<br>Ventaja: {ventaja_alc}</p>", unsafe_allow_html=True)
            
            with col3:
                odds2 = p2.get('odds', 'N/A')
                st.markdown(f"## 🔵 {p2.get('nombre', 'Desconocido')}")
                if odds2 and str(odds2) not in ('N/A', 'None', ''):
                    st.markdown(
                        f"<div style='display:inline-block;margin:2px 0 6px 0;padding:3px 14px;border-radius:16px;"
                        f"background:rgba(59,130,246,0.15);border:1px solid rgba(59,130,246,0.45)'>"
                        f"<span style='color:#3b82f6;font-weight:800;font-size:1.0rem'>🎲 {odds2}</span></div>",
                        unsafe_allow_html=True)
                if p2_photo:
                    st.image(p2_photo, width=100) # Display photo
                st.markdown(f"📊 **Récord:** {p2.get('record', '0-0-0')}")
                
                # Datos físicos
                st.markdown(f"""
                <div style="background-color: #2A2A2A; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                    <p style='font-size: 13px; color: #AAA; margin: 2px 0;'>
                    📏 <strong>Altura:</strong> {p2.get('altura', 'N/A')} | 
                    ⚖️ <strong>Peso:</strong> {p2.get('peso', 'N/A')}
                    </p>
                    <p style='font-size: 13px; color: #AAA; margin: 2px 0;'>
                    📏 <strong>Alcance:</strong> {p2.get('alcance', 'N/A')} | 
                    🥊 <strong>Postura:</strong> {p2.get('postura', 'Desconocida')}
                    </p>
                    <p style='font-size: 13px; color: #FFD700; margin: 2px 0;'>
                    💥 <strong>KO Rate:</strong> {p2_ko_rate:.1f}% | 
                    🔥 <strong>Win Rate:</strong> {p2.get('win_rate', 0):.0f}%
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                # Estadísticas de carrera COMPLETAS
                self._render_stats_expander(p2)
            
            st.markdown("---")

            # ── MEJOR APUESTA (mercado más fuerte: ganador / método / distancia) ──
            if analisis_ufc and analisis_ufc.get('mejor_apuesta'):
                mb = analisis_ufc['mejor_apuesta']
                mercados = analisis_ufc.get('mercados', [])
                conf_mb = mb.get('confianza', 0)
                col_mb = '#4CAF50' if conf_mb >= 65 else '#FF9800' if conf_mb >= 52 else '#f44336'
                chips = "".join(
                    f"<span style='background:#1E1E1E;border:1px solid #444;border-radius:6px;"
                    f"padding:3px 8px;margin-right:6px;font-size:11px;color:#bbb;'>"
                    f"{m['mercado'].split()[0]}: <b style='color:#fff'>{m['confianza']}%</b></span>"
                    for m in mercados
                )
                st.markdown(f"""
                <div style="background:linear-gradient(135deg,#1b2a1b,#0f1a0f);
                            border:2px solid {col_mb};border-radius:10px;padding:14px;margin-bottom:14px;">
                    <div style="color:{col_mb};font-weight:bold;font-size:13px;">🎯 MEJOR APUESTA — {mb.get('mercado','')}</div>
                    <div style="color:#fff;font-size:20px;font-weight:800;margin:4px 0;">{mb.get('apuesta','')}</div>
                    <div style="color:{col_mb};font-size:14px;margin-bottom:8px;">Confianza: {conf_mb}%</div>
                    <div>{chips}</div>
                </div>
                """, unsafe_allow_html=True)

            # ── MÁS MERCADOS (método, totales de rounds, se va a la distancia) ──
            if analisis_ufc and (analisis_ufc.get('metodo_probs') or analisis_ufc.get('rounds_totales')):
                with st.expander("📋 Más mercados (método · rounds · distancia)", expanded=False):
                    mp = analisis_ufc.get('metodo_probs', {})
                    if mp:
                        st.markdown("**🥊 Método de victoria (probabilidad):**")
                        cmp1, cmp2, cmp3 = st.columns(3)
                        iconos = {"KO/TKO": "💥", "Sumisión": "🥋", "Decisión": "📊"}
                        for col, (met, p) in zip([cmp1, cmp2, cmp3], mp.items()):
                            col.metric(f"{iconos.get(met, '')} {met}", f"{p}%")
                    rt = analisis_ufc.get('rounds_totales', [])
                    if rt:
                        st.markdown("**⏱️ Totales de Rounds:**")
                        for r in rt:
                            color_r = "#4CAF50" if r['pick'] == "OVER" else "#f44336"
                            st.markdown(
                                f"<span style='color:#aaa'>Over/Under {r['linea']} rounds →</span> "
                                f"<b style='color:{color_r}'>{r['pick']} {r['linea']}</b> "
                                f"<span style='color:#888'>({r['confianza']}%)</span>",
                                unsafe_allow_html=True)
                    dur = analisis_ufc.get('duracion', {})
                    if dur:
                        va = dur.get('va_a_decision')
                        st.markdown(f"**🎯 ¿Se va a la distancia?** "
                                    f"<b style='color:{'#4CAF50' if va else '#f44336'}'>"
                                    f"{'SÍ' if va else 'NO'}</b> ({dur.get('confianza', 0)}%)",
                                    unsafe_allow_html=True)

            # Análisis de los motores
            col_a1, col_a2, col_a3 = st.columns(3)
            
            with col_a1:
                st.markdown("<h4 style='color: #FFD700;'>📊 HEURÍSTICO</h4>", unsafe_allow_html=True)
                if analisis_ufc:
                    apuesta = analisis_ufc.get('recomendacion') or analisis_ufc.get('apuesta', 'N/A')
                    confianza = analisis_ufc.get('confianza', 0)
                    metodo = analisis_ufc.get('metodo', 'N/A')
                    dur = analisis_ufc.get('duracion', {}) or {}

                    color_conf = '#4CAF50' if confianza >= 70 else '#FF9800' if confianza >= 50 else '#f44336'
                    linea_dur = (
                        f"<p style='color: #64b5f6; font-size: 12px;'>⏱️ {dur.get('pick', '')} "
                        f"({dur.get('prob', 0)}%)</p>"
                    ) if dur else ""

                    st.markdown(f"""
                    <div style="background-color: #2A2A2A; padding: 10px; border-radius: 5px;">
                        <p style='color: #FFF; font-weight: bold;'>{apuesta}</p>
                        <p style='color: {color_conf};'>Confianza: {confianza}%</p>
                        <p style='color: #888; font-size: 12px;'>{metodo}</p>
                        {linea_dur}
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown("<p style='color: #888;'>Pendiente de análisis</p>", unsafe_allow_html=True)
            
            with col_a2:
                st.markdown("<h4 style='color: #FFD700;'>🧠 CLAUDE ANALYST</h4>", unsafe_allow_html=True)
                if analisis_premium:
                    if 'error' in analisis_premium:
                        st.markdown(f"<p style='color:#f44336;font-size:12px;'>Claude: {str(analisis_premium['error'])[:90]}</p>", unsafe_allow_html=True)
                    elif analisis_premium.get('pick') or analisis_premium.get('razon'):
                        # Formato del orquestador de IA (pick/confianza/razon/mercado)
                        pick_c = analisis_premium.get('pick', 'N/A')
                        conf_c = analisis_premium.get('confianza', 0)
                        razon_c = analisis_premium.get('razon', '')
                        mercado_c = analisis_premium.get('mercado', '')
                        st.markdown(f"""
                        <div style="background-color: #2A2A2A; padding: 10px; border-radius: 5px;">
                            <p style='color: #d97aff; font-weight: bold;'>🎯 {pick_c}</p>
                            <p style='color: #4CAF50;'>Confianza: {conf_c}% {('· ' + mercado_c) if mercado_c else ''}</p>
                            <p style='color: #aaa; font-size: 11px;'>{razon_c[:160]}</p>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        # Formato legacy edge/razones
                        edge = analisis_premium.get('edge_rating', 0)
                        estrellas = "★" * min(10, int(edge)) + "☆" * (10 - min(10, int(edge)))
                        st.markdown(f"<p style='color:#FFD700;font-size:18px;'>{estrellas}</p>", unsafe_allow_html=True)
                else:
                    st.markdown("<p style='color: #888;'>Selecciona Claude o pulsa Analizar</p>", unsafe_allow_html=True)
            
            with col_a3:
                st.markdown("<h4 style='color: #FFD700;'>🤖 GEMINI IA</h4>", unsafe_allow_html=True)
                if analisis_ufc:
                    if 'error' in analisis_ufc:
                        st.error(f"IA Falló: {analisis_ufc['error'][:100]}...")
                    else:
                        ganador = analisis_ufc.get('ganador', 'N/A')
                        metodo = analisis_ufc.get('metodo', 'N/A')
                        confianza_ia = analisis_ufc.get('confianza', 0)
                        
                        st.markdown(f"""
                        <div style="background-color: #2A2A2A; padding: 10px; border-radius: 5px;">
                            <p style='color: #2196F3; font-weight: bold;'>Ganador: {ganador}</p>
                            <p style='color: #4CAF50;'>Confianza IA: {confianza_ia}%</p>
                            <p style='color: #888; font-size: 12px;'>{metodo[:80]}...</p>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.markdown("<p style='color: #888;'>Pendiente de análisis</p>", unsafe_allow_html=True)
            
            st.markdown("---")
            
            # --- ALERTA DE FINALIZACIÓN (NUEVO) ---
            if analisis_ufc and analisis_ufc.get('method_detail', {}).get('type') == "KO/TKO":
                prob_ko = analisis_ufc.get('method_detail', {}).get('confidence', 0)
                if prob_ko >= 65: # Solo mostrar para alta confianza
                    self._render_ko_card(prob_ko)
            elif analisis_ufc and analisis_ufc.get('method_detail', {}).get('type') == "Sumisión":
                prob_sub = analisis_ufc.get('method_detail', {}).get('confidence', 0)
                if prob_sub >= 60:
                    self._render_sub_card(prob_sub)

            # Botones de acción
            col_b1, col_b2, col_b3 = st.columns(3)
            with col_b1:
                button_text = "🔄 ACTUALIZAR ANÁLISIS" if analisis_ufc else "🔍 ANALIZAR DETALLADO"
                if st.button(button_text, key=f"analizar_ufc_{idx}", use_container_width=True):
                    return "analizar"
            with col_b2:
                if st.button(f"➕ AGREGAR AL PARLAY", key=f"add_ufc_{idx}", use_container_width=True):
                    st.session_state[f'parlay_ufc_{idx}'] = {
                        'evento': evento,
                        'peleador1': p1.get('nombre'),
                        'peleador2': p2.get('nombre'),
                        'analisis': analisis_ufc
                    }
                    st.success("✓ Agregado al parlay")
            with col_b3:
                if st.button(f"📊 VER DATOS COMPLETOS", key=f"details_ufc_{idx}", use_container_width=True):
                    with st.expander(f"DATOS COMPLETOS - {p1.get('nombre')} vs {p2.get('nombre')}", expanded=True):
                        col_d1, col_d2 = st.columns(2)
                        with col_d1:
                            st.json(p1)
                        with col_d2:
                            st.json(p2)
    
    def _render_stats_expander(self, p):
        """Expander con las estadísticas de carrera reales (fuente ESPN)."""
        ec = p.get('estadisticas_carrera', {}) or {}
        if not any(v for v in ec.values()):
            return
        with st.expander("📊 ESTADÍSTICAS DE CARRERA COMPLETAS", expanded=False):
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("SLpM", f"{ec.get('sig_strikes_landed_per_min', 0):.2f}")
                st.metric("Precisión Golpes", f"{ec.get('sig_strike_accuracy', 0):.1f}%")
                ko = p.get('ko_rate', 0)
                ko = ko * 100 if ko <= 1 else ko
                st.metric("Victorias por KO", f"{ko:.0f}%")
            with c2:
                st.metric("TD Avg/15min", f"{ec.get('td_avg_per_15min', 0):.2f}")
                st.metric("TD Precisión", f"{ec.get('td_accuracy', 0):.1f}%")
                st.metric("Sub Avg/15min", f"{ec.get('sub_avg_per_15min', 0):.2f}")
            with c3:
                st.metric("Tiempo Pelea", f"{ec.get('avg_fight_time', 0):.2f} min")
                st.metric("Racha", f"{p.get('streak', 0)}W")
                st.metric("Victorias Decisión", f"{ec.get('decision_pct', 0):.0f}%")

    def _completar_datos(self, peleador):
        """Completa datos faltantes y traduce claves del scraper UFCStats al formato visual."""
        # ── Adaptador scraper → visual (idempotente) ─────────────────────────
        if peleador.get('stance') and not peleador.get('postura'):
            peleador['postura'] = peleador['stance']

        # altura: scraper la da como int en cm → convertir a formato pies'pulgadas
        alt = peleador.get('altura')
        if isinstance(alt, (int, float)):
            if alt > 0:
                total_in = alt / 2.54
                peleador['altura'] = f"{int(total_in // 12)}' {round(total_in % 12)}\""
            else:
                peleador['altura'] = 'N/A'

        # alcance: int cm → pulgadas
        alc = peleador.get('alcance')
        if isinstance(alc, (int, float)):
            peleador['alcance'] = f"{alc / 2.54:.0f}\"" if alc > 0 else 'N/A'

        # estadisticas_carrera desde las claves planas del scraper
        ec = peleador.get('estadisticas_carrera') or {}
        if not ec.get('sig_strikes_landed_per_min') and peleador.get('slpm_avg'):
            ec['sig_strikes_landed_per_min'] = peleador['slpm_avg']
        if not ec.get('sig_strike_accuracy') and peleador.get('striking_accuracy'):
            acc = peleador['striking_accuracy']
            ec['sig_strike_accuracy'] = acc * 100 if acc <= 1 else acc
        if not ec.get('td_accuracy') and peleador.get('takedown_accuracy'):
            td = peleador['takedown_accuracy']
            ec['td_accuracy'] = td * 100 if td <= 1 else td
        if not ec.get('control_avg_time') and peleador.get('control_time_avg'):
            ec['control_avg_time'] = peleador['control_time_avg']
        if not ec.get('td_avg_per_15min') and peleador.get('td_avg'):
            ec['td_avg_per_15min'] = peleador['td_avg']
        if ec:
            peleador['estadisticas_carrera'] = ec

        defaults = {
            'altura': 'N/A',
            'peso': 'N/A',
            'alcance': 'N/A',
            'postura': 'Desconocida',
            'edad': 0,
            'ko_rate': 0.0,
            'win_rate': 0,
            'record': '0-0-0',
            'estadisticas_carrera': {
                'sig_strikes_landed_per_min': 0,
                'sig_strike_accuracy': 0,
                'sig_strike_defense': 0,
                'td_avg_per_15min': 0,
                'td_defense': 0,
                'td_accuracy': 0,
                'sub_avg_per_15min': 0,
                'control_avg_time': 0,
                'avg_fight_time': 0
            }
        }
        
        for key, value in defaults.items():
            if key not in peleador or not peleador[key]:
                if isinstance(value, dict):
                    peleador[key] = value.copy()
                else:
                    peleador[key] = value
        
        # Calcular win_rate y ko_rate desde el record si no están presentes o son 0
        if peleador.get('win_rate', 0) == 0 and peleador.get('record', '0-0-0') != '0-0-0':
            try:
                record_str = re.split(r'\(', peleador['record'])[0].strip() # "28-1-0 (1 NC)" -> "28-1-0"
                parts = record_str.split('-')
                if len(parts) >= 2:
                    wins = int(parts[0])
                    losses = int(parts[1])
                    draws = int(parts[2]) if len(parts) > 2 else 0
                    total = wins + losses + draws
                    if total > 0:
                        peleador['win_rate'] = round((wins / total) * 100, 1)
                        # Estimar KO rate basado en SLpM (golpes significativos por minuto)
                        slpm = peleador.get('estadisticas_carrera', {}).get('sig_strikes_landed_per_min', 0)
                        if slpm > 5:
                            peleador['ko_rate'] = min(0.75, slpm / 10)  # Estimación
                        elif slpm > 3:
                            peleador['ko_rate'] = min(0.55, slpm / 8)
                        elif wins > 0:
                            peleador['ko_rate'] = 0.35  # Estimación conservadora
            except (ValueError, IndexError):
                pass
        
        return peleador
    
    def _parse_height_to_cm(self, height_str: str) -> float:
        """Convierte altura en formato 'pies\'pulgadas"' a cm."""
        if not isinstance(height_str, str):
            return 0.0
        try:
            height_str = height_str.replace('"', '').strip()
            parts = height_str.split("'")
            feet = float(parts[0]) if parts[0] else 0.0
            inches = float(parts[1]) if len(parts) > 1 and parts[1] else 0.0
            return (feet * 30.48) + (inches * 2.54)
        except (ValueError, IndexError):
            return 0.0

    def _parse_reach_to_cm(self, reach_str: str) -> float:
        """Convierte alcance en formato 'pulgadas"' a cm."""
        if not isinstance(reach_str, str):
            return 0.0
        try:
            # Maneja formatos como '84.5"' o '84.5'
            inches = float(reach_str.replace('"', '').strip())
            return inches * 2.54
        except (ValueError, IndexError):
            return 0.0

    def _render_ko_card(self, probabilidad_ko):
        """Renderiza la tarjeta visual de predicción de KO."""
        st.markdown(f"""
        <div style="padding:15px; border-radius:10px; background: rgba(255, 75, 75, 0.1); border: 1px solid {self.colores['red']}; margin-bottom: 15px;">
            <h4 style="margin:0; color:{self.colores['red']};">🔥 ALERTA DE FINALIZACIÓN POR KO/TKO</h4>
            <p style="margin:5px 0 0 0">Probabilidad de KO/TKO: <strong>{probabilidad_ko}%</strong></p>
            <div style="width:100%; background:#262730; border-radius:5px; margin-top:10px">
                <div style="width:{probabilidad_ko}%; background:{self.colores['red']}; height:10px; border-radius:5px"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    def _render_sub_card(self, probabilidad_sub):
        """Renderiza la tarjeta visual de predicción de Sumisión."""
        st.markdown(f"""
        <div style="padding:15px; border-radius:10px; background: rgba(59, 130, 246, 0.1); border: 1px solid {self.colores['blue']}; margin-bottom: 15px;">
            <h4 style="margin:0; color:{self.colores['blue']};">🥋 ALERTA DE FINALIZACIÓN POR SUMISIÓN</h4>
            <p style="margin:5px 0 0 0">Probabilidad de Sumisión: <strong>{probabilidad_sub}%</strong></p>
            <div style="width:100%; background:#262730; border-radius:5px; margin-top:10px">
                <div style="width:{probabilidad_sub}%; background:{self.colores['blue']}; height:10px; border-radius:5px"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)