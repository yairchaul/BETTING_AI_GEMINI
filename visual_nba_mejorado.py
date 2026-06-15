# -*- coding: utf-8 -*-
import streamlit as st
from database_manager import db

try:
    from radar_triples_nba import radar_triples # Importar la instancia unificada
    RADAR_AVAILABLE = True
except ImportError:
    RADAR_AVAILABLE = False

class VisualNBAMejorado:
    def __init__(self):
        pass

    def render(self, partido, idx, tracker, analisis_heuristico=None, analisis_gemini=None, analisis_premium=None, **kwargs):
        """Renderiza partido NBA con estilo NEON"""
        # Soporte para el argumento analisis_ia si viene desde el main
        analisis_ia = analisis_gemini or kwargs.get('analisis_ia')
        
        local = partido.get('local', '')
        visitante = partido.get('visitante', '')
        odds = partido.get('odds', {})
        records = partido.get('records', {})
        rec_l = partido.get('local_record') or records.get('local', '0-0')
        rec_v = partido.get('visitante_record') or records.get('visitante', '0-0')

        # Logos
        logo_l = partido.get('local_logo', '')
        logo_v = partido.get('visitante_logo', '')
        img_l = f'<img src="{logo_l}" width="46" style="margin-bottom:6px;">' if logo_l else ''
        img_v = f'<img src="{logo_v}" width="46" style="margin-bottom:6px;">' if logo_v else ''

        # Extraer datos
        spread_local = odds.get('spread', {}).get('local', 'N/A')
        spread_visit = odds.get('spread', {}).get('visitante', 'N/A')
        over_under = odds.get('over_under', 'N/A')
        ml_local = odds.get('moneyline', {}).get('local', 'N/A')
        ml_visit = odds.get('moneyline', {}).get('visitante', 'N/A')

        # Estilo de tarjeta
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #0f0f1a 0%, #1a1f2a 100%);
                    border-radius: 15px;
                    padding: 20px;
                    margin: 15px 0;
                    border: 1px solid #00ff41;
                    box-shadow: 0 0 15px rgba(0, 255, 65, 0.2);'>
            <div style='display: flex; justify-content: space-between; align-items: center;'>
                <div style='text-align: center; flex: 1;'>
                    {img_l}
                    <h2 style='color: #fff; text-shadow: 0 0 5px #ff6600; margin: 0;'>{local}</h2>
                    <p style='color: #ff6600; margin: 0;'>{rec_l}</p>
                    <div style='display:inline-block;margin-top:6px;padding:2px 12px;border-radius:14px;background:rgba(59,130,246,0.15);border:1px solid rgba(59,130,246,0.45)'>
                        <span style='color:#3b82f6;font-weight:800;font-size:13px;'>🎲 ML {ml_local}</span>
                    </div>
                </div>
                <div style='text-align: center; flex: 0.5;'>
                    <h1 style='color: #00ff41; text-shadow: 0 0 10px #00ff41; margin: 0;'>VS</h1>
                </div>
                <div style='text-align: center; flex: 1;'>
                    {img_v}
                    <h2 style='color: #fff; text-shadow: 0 0 5px #ff6600; margin: 0;'>{visitante}</h2>
                    <p style='color: #ff6600; margin: 0;'>{rec_v}</p>
                    <div style='display:inline-block;margin-top:6px;padding:2px 12px;border-radius:14px;background:rgba(59,130,246,0.15);border:1px solid rgba(59,130,246,0.45)'>
                        <span style='color:#3b82f6;font-weight:800;font-size:13px;'>🎲 ML {ml_visit}</span>
                    </div>
                </div>
            </div>
            <div style='display: flex; justify-content: center; gap: 30px; margin-top: 15px; padding-top: 10px; border-top: 1px solid #333;'>
                <div style='text-align: center;'>
                    <span style='color: #888; font-size: 12px;'>SPREAD</span>
                    <p style='color: #fff; margin: 0;'>{local}: {spread_local} | {visitante}: {spread_visit}</p>
                </div>
                <div style='text-align: center;'>
                    <span style='color: #888; font-size: 12px;'>OVER/UNDER</span>
                    <p style='color: #fff; margin: 0;'>OVER {over_under} / UNDER {over_under}</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Botón ANALIZAR
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🔥 ANALIZAR CON MOTOR + GEMINI", key=f"analyze_nba_{idx}", use_container_width=True):
                return "analizar"
        
        # Mostrar resultados si existen
        if analisis_heuristico:
            st.markdown("---")
            
            recomendacion = analisis_heuristico.get('recomendacion', 'N/A')
            ev = analisis_heuristico.get('ev', analisis_heuristico.get('ev_mejor', 0))
            confianza = analisis_heuristico.get('confianza', 0)
            total_proyectado = analisis_heuristico.get('total_proyectado', 0)
            detalle = analisis_heuristico.get('detalle', '')
            etiqueta_verde = analisis_heuristico.get('etiqueta_verde', False)

            color_resultado = "#00ff41" if "OVER" in recomendacion or "GANA" in recomendacion else "#ff6600"
            icono = "📈" if "OVER" in recomendacion else ("📉" if "UNDER" in recomendacion else "🎯")
            ev_txt = f"{ev}%" if ev else "s/cuota"
            ev_color = "#00ff41" if (isinstance(ev, (int, float)) and ev >= 5) else ("#ff6600" if ev else "#64748b")

            st.markdown(f"""
            <div style='background: linear-gradient(135deg, #1a1f2a 0%, #0f1419 100%); 
                        border-radius: 12px; 
                        padding: 20px; 
                        margin: 15px 0; 
                        border-left: 4px solid {color_resultado};
                        border-right: 1px solid #333;
                        border-top: 1px solid #333;
                        border-bottom: 1px solid #333;'>
                <div style='display: flex; justify-content: space-between; align-items: center;'>
                    <div>
                        <span style='color: #888; font-size: 12px;'>RECOMENDACIÓN</span>
                        <h3 style='color: {color_resultado}; margin: 0; text-shadow: 0 0 5px {color_resultado};'>{icono} {recomendacion}</h3>
                    </div>
                    <div style='text-align: center;'>
                        <span style='color: #888; font-size: 12px;'>VALOR ESPERADO (EV)</span>
                        <h3 style='color: {ev_color}; margin: 0;'>{ev_txt}</h3>
                    </div>
                    <div style='text-align: center;'>
                        <span style='color: #888; font-size: 12px;'>CONFIANZA</span>
                        <h3 style='color: #00ff41; margin: 0;'>{confianza}%</h3>
                    </div>
                    <div style='text-align: center;'>
                        <span style='color: #888; font-size: 12px;'>TOTAL PROYECTADO</span>
                        <h3 style='color: #ff6600; margin: 0;'>{total_proyectado}</h3>
                    </div>
                </div>
                <div style='margin-top: 10px;'>
                    <span style='color: #888; font-size: 11px;'>{detalle}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Barra de progreso de confianza
            st.progress(confianza / 100)

            # ── Los 3 mercados SIEMPRE visibles (Ganador / Hándicap / Total O-U) ──
            mercados = analisis_heuristico.get('mercados', [])
            if mercados:
                st.markdown("<div style='color:#888;font-size:12px;margin:6px 0 4px 0'>📊 MERCADOS PREDICHOS</div>",
                            unsafe_allow_html=True)
                mejor = analisis_heuristico.get('mejor_mercado', {})
                cols_m = st.columns(len(mercados))
                for cm, m in zip(cols_m, mercados):
                    es_mejor = m.get('mercado') == mejor.get('mercado')
                    borde = "#00ff41" if es_mejor else "#334155"
                    estrella = " ⭐" if es_mejor else ""
                    ev_m = m.get('ev', 0)
                    ev_m_txt = (f"<div style='color:{'#00ff41' if ev_m>=0 else '#ef4444'};font-size:10px'>EV {ev_m:+.0f}%</div>"
                                if ev_m else "")
                    cm.markdown(
                        f"<div style='background:#0f1419;border:1px solid {borde};border-radius:8px;padding:8px;text-align:center'>"
                        f"<div style='color:#888;font-size:10px'>{m.get('mercado')}{estrella}</div>"
                        f"<div style='color:#fff;font-weight:700;font-size:13px'>{m.get('pick')}</div>"
                        f"<div style='color:#00ff41;font-size:12px'>{m.get('confianza')}%</div>"
                        f"{ev_m_txt}"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

            if etiqueta_verde or ev >= 8:
                st.success("🔥 PICK DE ALTA CONFIANZA - Valor positivo detectado")
            
            if analisis_gemini:
                st.markdown("---")
                st.markdown("### 🤖 GEMINI - DECISOR FINAL")
                st.info(analisis_gemini)
            
            if analisis_premium:
                st.markdown("---")
                st.markdown("### 🔬 PREMIUM ANALYTICS")
                if isinstance(analisis_premium, dict):
                    st.write(analisis_premium.get('analisis', 'Pendiente'))
                else:
                    st.write(str(analisis_premium))
        
        
        # 🏀 RADAR DE TRIPLES (NBA PROPS)
        st.markdown("---")
        st.subheader("🎯 RADAR DE TRIPLES (3PM)")
        
        # Ranking de defensas (Multiplicador: >1 es mala defensa, <1 es buena)
        defensa_3p = {"Boston Celtics": 0.82, "Oklahoma City Thunder": 0.85, "Charlotte Hornets": 1.18, "Detroit Pistons": 1.20}
        from database_manager import db
        
        col_p1, col_p2 = st.columns(2)
        for i, team in enumerate([local, visitante]):
            rival = visitante if i == 0 else local
            mult_defensa = defensa_3p.get(rival, 1.0)
            
            with [col_p1, col_p2][i]:
                st.markdown(f"**🔥 {team}**")
                if RADAR_AVAILABLE:
                    lideres = radar_triples.get_top_tripleros(team, limit=2)
                else:
                    lideres = db.get_top_player_stat(team, "three_pm", limit=2, deporte="nba")
                if lideres:
                    for player in lideres:
                        tpp = player.get('triples_por_partido', 0)
                        is_hot = tpp >= 3.0
                        prob = min(95, (tpp * 20) * mult_defensa)
                        # Línea de props sugerida: medio triple por debajo del promedio
                        linea = max(0.5, round(tpp - 0.5, 1))
                        nombre = player.get('nombre', 'N/A')
                        hot_txt = " 🔥 Racha caliente" if is_hot else ""
                        # Sin HTML indentado (Markdown lo tomaría como bloque de código)
                        st.markdown(
                            f"🏀 **{nombre}** — {tpp} triples/g · "
                            f"Línea sugerida **OVER {linea}** · Prob: **{prob:.0f}%**{hot_txt}"
                        )
                        st.progress(prob / 100)
                else:
                    st.caption("Sin datos de tripleros para este equipo.")
        return None
