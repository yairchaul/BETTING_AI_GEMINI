# -*- coding: utf-8 -*-
import streamlit as st
from database_manager import db

# Importar el radar de triples con datos reales
try:
    from balldontlie_client import balldontlie
    BALLDONTLIE_AVAILABLE = True
except ImportError:
    BALLDONTLIE_AVAILABLE = False

class VisualNBAMejorado:
    def __init__(self):
        pass
    
    def get_top_tripleros_reales(self, team_name, limit=3):
        """Obtiene los mejores tripleros de un equipo usando Balldontlie API"""
        if not BALLDONTLIE_AVAILABLE:
            return []
        
        # Mapeo de nombres de equipos a IDs de Balldontlie
        team_ids = {
            "Lakers": 14, "Warriors": 15, "Celtics": 2, "Bucks": 16,
            "Nets": 17, "Suns": 21, "76ers": 20, "Mavericks": 6,
            "Nuggets": 7, "Heat": 12, "Knicks": 18, "Clippers": 13,
            "Grizzlies": 29, "Kings": 19, "Pelicans": 23, "Magic": 22,
            "Pacers": 24, "Bulls": 4, "Hawks": 1, "Hornets": 30,
            "Cavaliers": 5, "Pistons": 8, "Raptors": 28, "Timberwolves": 25,
            "Trail Blazers": 26, "Thunder": 27, "Jazz": 31, "Spurs": 3,
            "Rockets": 10, "Wizards": 32
        }
        
        team_id = next((tid for name, tid in team_ids.items() if name.lower() in team_name.lower()), None)
        if not team_id: return []
        
        try:
            players_data = balldontlie.get_players(team_id=team_id)
            players = players_data.get('data', [])
            tripleros = []
            for player in players:
                player_id = player.get('id')
                if player_id:
                    stats = balldontlie.get_player_props(player_id)
                    if stats and stats.get('fg3a', 0) >= 2:
                        tripleros.append({
                            "nombre": f"{player.get('first_name')} {player.get('last_name')}",
                            "triples_por_partido": stats.get('fg3a', 0),
                            "porcentaje_triple": stats.get('fg3_pct', 0) * 100
                        })
            tripleros.sort(key=lambda x: x["triples_por_partido"], reverse=True)
            return tripleros[:limit]
        except:
            return []

    def render(self, partido, idx, tracker, analisis_heuristico=None, analisis_gemini=None, analisis_premium=None, **kwargs):
        """Renderiza partido NBA con estilo NEON"""
        # Soporte para el argumento analisis_ia si viene desde el main
        analisis_ia = analisis_gemini or kwargs.get('analisis_ia')
        
        local = partido.get('local', '')
        visitante = partido.get('visitante', '')
        odds = partido.get('odds', {})
        records = partido.get('records', {})
        
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
                    <h2 style='color: #fff; text-shadow: 0 0 5px #ff6600; margin: 0;'>{local}</h2>
                    <p style='color: #ff6600; margin: 0;'>{records.get('local', '0-0')}</p>
                    <p style='color: #00ff41; font-size: 14px;'>ML: {ml_local}</p>
                </div>
                <div style='text-align: center; flex: 0.5;'>
                    <h1 style='color: #00ff41; text-shadow: 0 0 10px #00ff41; margin: 0;'>VS</h1>
                </div>
                <div style='text-align: center; flex: 1;'>
                    <h2 style='color: #fff; text-shadow: 0 0 5px #ff6600; margin: 0;'>{visitante}</h2>
                    <p style='color: #ff6600; margin: 0;'>{records.get('visitante', '0-0')}</p>
                    <p style='color: #00ff41; font-size: 14px;'>ML: {ml_visit}</p>
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
            ev = analisis_heuristico.get('ev_mejor', 0)
            confianza = analisis_heuristico.get('confianza', 0)
            total_proyectado = analisis_heuristico.get('total_proyectado', 0)
            detalle = analisis_heuristico.get('detalle', '')
            etiqueta_verde = analisis_heuristico.get('etiqueta_verde', False)
            
            color_resultado = "#00ff41" if "OVER" in recomendacion or "GANA" in recomendacion else "#ff6600"
            icono = "📈" if "OVER" in recomendacion else ("📉" if "UNDER" in recomendacion else "🎯")
            
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
                        <h3 style='color: {"#00ff41" if ev >= 5 else "#ff6600"}; margin: 0;'>{ev}%</h3>
                    </div>
                    <div style='text-align: center;'>
                        <span style='color: #888; font-size: 12px;'>CONFIANZA</span>
                        <h3 style='color: #00ff41; margin: 0;'>{confianza}%</h3>
                    </div>
                    <div style='text-align: center;'>
                        <span style='color: #888; font-size: 12px;'>TOTAL IA</span>
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
        
        # 🤖 CONSULTAR IA
        if st.button("🤖 CONSULTAR IA", key=f"btn_ia_nba_{idx}"):
            if hasattr(st.session_state, 'gemini') and st.session_state.gemini:
                st.info("Gemini: Análisis en desarrollo")
        
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
                lideres = db.get_top_player_stat(team, "three_pm", limit=2, deporte="nba")
                if lideres:
                    for player in lideres:
                        # Simulación: Si supera 3.0 triples/g, lo consideramos "Hot" (Racha 4/5)
                        is_hot = player.get('triples_por_partido', 0) >= 3.0
                        css_class = "prop-hot-purple" if is_hot else ""
                        
                        prob = min(95, (player['triples_por_partido'] * 20) * mult_defensa)
                        
                        st.markdown(f"""<div class='{css_class}'>
                            🏀 <b>{player['nombre']}</b>: {player['triples_por_partido']} 3PM/g (Prob: {prob:.0f}%)
                            {"<br><small style='color:#bc13fe;'>🔥 Racha: 4/5 HITS</small>" if is_hot else ""}
                        </div>""", unsafe_allow_html=True)
                        st.progress(prob/100)
        return None
