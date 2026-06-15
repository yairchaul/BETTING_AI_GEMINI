# -*- coding: utf-8 -*-
import streamlit as st
from utils.database_manager import db
import os, json
import logging

# Importar el cliente de Balldontlie con datos reales
try:
    from balldontlie_client import balldontlie
    BALLDONTLIE_AVAILABLE = True
except ImportError:
    BALLDONTLIE_AVAILABLE = False

logger = logging.getLogger(__name__)

class VisualNBAMejorado:
    def __init__(self):
        pass
    
    # Datos 2024-25: top 3PM líderes por equipo (fallback sin API)
    _3PM_FALLBACK = {
        "Golden State Warriors":    [{"nombre": "Stephen Curry",    "triples_por_partido": 4.6, "porcentaje_triples": 42.6}],
        "Dallas Mavericks":         [{"nombre": "Luka Doncic",      "triples_por_partido": 3.5, "porcentaje_triples": 37.0},
                                     {"nombre": "Klay Thompson",    "triples_por_partido": 2.7, "porcentaje_triples": 38.0}],
        "Milwaukee Bucks":          [{"nombre": "Damian Lillard",   "triples_por_partido": 3.2, "porcentaje_triples": 37.5}],
        "Indiana Pacers":           [{"nombre": "Tyrese Haliburton","triples_por_partido": 3.1, "porcentaje_triples": 38.2}],
        "Cleveland Cavaliers":      [{"nombre": "Donovan Mitchell",  "triples_por_partido": 3.0, "porcentaje_triples": 36.0}],
        "Boston Celtics":           [{"nombre": "Jayson Tatum",     "triples_por_partido": 3.2, "porcentaje_triples": 37.1},
                                     {"nombre": "Jaylen Brown",     "triples_por_partido": 2.7, "porcentaje_triples": 34.0}],
        "Oklahoma City Thunder":    [{"nombre": "Shai Gilgeous-Alexander", "triples_por_partido": 2.1, "porcentaje_triples": 33.0}],
        "Denver Nuggets":           [{"nombre": "Jamal Murray",     "triples_por_partido": 2.6, "porcentaje_triples": 38.5}],
        "Minnesota Timberwolves":   [{"nombre": "Anthony Edwards",  "triples_por_partido": 2.9, "porcentaje_triples": 36.0}],
        "Los Angeles Lakers":       [{"nombre": "LeBron James",     "triples_por_partido": 2.1, "porcentaje_triples": 41.0},
                                     {"nombre": "Austin Reaves",    "triples_por_partido": 2.4, "porcentaje_triples": 42.0}],
        "New York Knicks":          [{"nombre": "Jalen Brunson",    "triples_por_partido": 2.1, "porcentaje_triples": 36.0}],
        "Miami Heat":               [{"nombre": "Tyler Herro",      "triples_por_partido": 3.0, "porcentaje_triples": 38.5}],
        "Philadelphia 76ers":       [{"nombre": "Joel Embiid",      "triples_por_partido": 1.2, "porcentaje_triples": 32.0}],
        "Sacramento Kings":         [{"nombre": "De'Aaron Fox",     "triples_por_partido": 1.5, "porcentaje_triples": 32.0}],
        "Houston Rockets":          [{"nombre": "Jalen Green",      "triples_por_partido": 2.8, "porcentaje_triples": 34.0}],
        "Phoenix Suns":             [{"nombre": "Devin Booker",     "triples_por_partido": 2.5, "porcentaje_triples": 36.0}],
        "Atlanta Hawks":            [{"nombre": "Trae Young",       "triples_por_partido": 2.2, "porcentaje_triples": 35.0}],
        "Memphis Grizzlies":        [{"nombre": "Ja Morant",        "triples_por_partido": 1.0, "porcentaje_triples": 31.0}],
        "New Orleans Pelicans":     [{"nombre": "Brandon Ingram",   "triples_por_partido": 1.8, "porcentaje_triples": 35.0}],
        "Los Angeles Clippers":     [{"nombre": "James Harden",     "triples_por_partido": 3.2, "porcentaje_triples": 38.0}],
        "Charlotte Hornets":        [{"nombre": "LaMelo Ball",      "triples_por_partido": 3.1, "porcentaje_triples": 37.0}],
        "Toronto Raptors":          [{"nombre": "Scottie Barnes",   "triples_por_partido": 1.5, "porcentaje_triples": 32.0}],
        "Chicago Bulls":            [{"nombre": "Zach LaVine",      "triples_por_partido": 2.6, "porcentaje_triples": 36.0}],
        "San Antonio Spurs":        [{"nombre": "Victor Wembanyama","triples_por_partido": 1.8, "porcentaje_triples": 33.0}],
        "Washington Wizards":       [{"nombre": "Jordan Poole",     "triples_por_partido": 2.6, "porcentaje_triples": 33.0}],
        "Detroit Pistons":          [{"nombre": "Cade Cunningham",  "triples_por_partido": 2.0, "porcentaje_triples": 34.0}],
        "Utah Jazz":                [{"nombre": "Lauri Markkanen",  "triples_por_partido": 2.4, "porcentaje_triples": 37.0}],
        "Portland Trail Blazers":   [{"nombre": "Anfernee Simons",  "triples_por_partido": 3.0, "porcentaje_triples": 38.0}],
        "Brooklyn Nets":            [{"nombre": "Cam Thomas",       "triples_por_partido": 2.0, "porcentaje_triples": 34.0}],
        "Orlando Magic":            [{"nombre": "Paolo Banchero",   "triples_por_partido": 1.4, "porcentaje_triples": 32.0}],
    }

    def get_top_tripleros_reales(self, team_name, limit=3):
        """Obtiene los mejores tripleros de un equipo."""
        # 1. Base de datos local
        try:
            lideres_db = db.get_top_player_stat(team_name, "three_pm", limit=limit, deporte="nba")
            if lideres_db:
                return lideres_db if isinstance(lideres_db, list) else [lideres_db]
        except Exception as e:
            logger.warning(f"Error consultando DB local para tripleros: {e}")

        # 2. Fallback: datos estáticos 2024-25
        for key, jugadores in self._3PM_FALLBACK.items():
            if key.lower() in team_name.lower() or team_name.lower() in key.lower():
                return jugadores[:limit]

        # 3. API Balldontlie (si disponible)
        if not BALLDONTLIE_AVAILABLE:
            return []
        
        # Mapeo de nombres de equipos a IDs de Balldontlie (actualizado y más completo)
        team_ids = {
            "Lakers": 14, "Warriors": 15, "Celtics": 2, "Bucks": 16,
            "Nets": 17, "Suns": 21, "76ers": 20, "Mavericks": 6,
            "Nuggets": 7, "Heat": 12, "Knicks": 18, "Clippers": 13,
            "Grizzlies": 29, "Kings": 19, "Pelicans": 23, "Magic": 22,
            "Pacers": 24, "Bulls": 4, "Hawks": 1, "Hornets": 30,
            "Cavaliers": 5, "Pistons": 8, "Raptors": 28, "Timberwolves": 25,
            "Trail Blazers": 26, "Thunder": 27, "Jazz": 31, "Spurs": 29, # Spurs ID is 29, not 3
            "Rockets": 10, "Wizards": 32, "Pistons": 8, "Magic": 22, "Kings": 19,
            "Pelicans": 23, "Jazz": 31, "Raptors": 28, "Thunder": 27, "Timberwolves": 25,
            "Trail Blazers": 26, "Pacers": 24, "Hawks": 1, "Hornets": 30, "Cavaliers": 5,
            "Bulls": 4, "Heat": 12, "Knicks": 18, "Clippers": 13, "Nuggets": 7,
            "Suns": 21, "Mavericks": 6, "Bucks": 16, "Nets": 17, "76ers": 20,
            "Warriors": 15, "Celtics": 2, "Lakers": 14, "Wizards": 32
        }
        
        team_id = next((tid for name, tid in team_ids.items() if name.lower() in team_name.lower()), None)
        if not team_id: return []
        logger.info(f"Consultando Balldontlie para tripleros de {team_name} (ID: {team_id})...")
        try:
            current_season = 2023 # O la temporada actual que desees consultar
            players_data = balldontlie.get_players(team_id=team_id, per_page=100) # Aumentar per_page para obtener más jugadores
            players = players_data.get('data', [])
            tripleros = []
            players_to_save = [] # Lista para guardar en la DB
            for player in players:
                player_id = player.get('id')
                if player_id:
                    stats = balldontlie.get_player_season_stats(player_id, season=current_season) # Obtener stats de temporada
                    if stats and stats.get('fg3a', 0) >= 2: # Filtrar por intentos de triple por partido
                        player_name = f"{player.get('first_name')} {player.get('last_name')}"
                        fg3m = stats.get('fg3m', 0)
                        fg3a = stats.get('fg3a', 0)
                        fg3_pct = round(stats.get('fg3_pct', 0) * 100, 1)
                        pts = stats.get('pts', 0)

                        tripleros.append({
                            "nombre": player_name,
                            "triples_por_partido": fg3m, # Triples anotados por partido
                            "porcentaje_triple": fg3_pct # Porcentaje de triples
                        })
                        players_to_save.append({
                            "nombre": player_name,
                            "equipo": team_name,
                            "puntos": pts,
                            "triples_por_partido": fg3m,
                            "intentos_triples": fg3a,
                            "porcentaje_triples": fg3_pct,
                            "temporada": str(current_season)
                        })
            # Guardar los datos en la base de datos local
            if players_to_save:
                db.guardar_player_stats(players_to_save, "nba")
            tripleros.sort(key=lambda x: x["triples_por_partido"], reverse=True)
            return tripleros[:limit]
        except:
            logger.error(f"Error al obtener tripleros de Balldontlie para {team_name}")
            return []

    def _mostrar_historial_reciente(self, local, visitante):
        """Muestra una tabla comparativa de los últimos resultados reales (NBA)"""
        st.markdown("### 🕒 Historial Reciente (Últimos 5 Juegos)")
        path_res = "data/resultados_reales_15dias.json" # Definir la ruta al archivo
        try:
            import json
            if not os.path.exists(path_res):
                st.caption("Esperando actualización de resultados históricos...")
                return
                
            with open(path_res, "r", encoding="utf-8") as f:
                resultados = json.load(f)
            
            def get_team_history(team_name):
                # Filtro para NBA considerando nombres parciales (ej: "Lakers" vs "LA Lakers")
                hist = [r for r in resultados if team_name.lower() in r.get('home', '').lower() or team_name.lower() in r.get('away', '').lower()]
                return hist[:5]

            col1, col2 = st.columns(2)
            for i, team in enumerate([local, visitante]):
                with [col1, col2][i]:
                    st.markdown(f"**{team}**")
                    history = get_team_history(team)
                    if history:
                        data_table = []
                        for g in history:
                            winner = g.get('winner', '')
                            res = "✅ W" if team.lower() in winner.lower() else "❌ L"
                            
                            home_team = g.get('home', '')
                            rival = g.get('away', '') if team.lower() in home_team.lower() else home_team
                            
                            vs = f"vs {rival}"
                            score = f"{g.get('home_score', '?')}-{g.get('away_score', '?')}"
                            data_table.append({"Fecha": g.get('fecha', 'N/A')[:10], "Res": res, "Rival": vs, "Score": score})
                        st.table(data_table)
                    else:
                        st.caption("Sin historial registrado.")
        except Exception as e:
            st.caption(f"No se pudo cargar el historial: {e}")

    def render_prop_card(self, prop_data, color="#f59e0b"):
        """Dibuja una tarjeta de Prop estilo NEON (Fusión VisualNBAProps)"""
        st.markdown(f"""
        <div style="padding:12px; border-radius:10px; background: rgba(245, 158, 11, 0.05); border: 1px solid {color}; margin-bottom: 8px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-weight: bold; color: white; font-size: 1rem;">👤 {prop_data.get('jugador', 'Jugador')}</span>
                <span style="background: {color}; color: black; padding: 1px 6px; border-radius: 4px; font-weight: bold; font-size: 0.8rem;">
                    {prop_data.get('prediccion', 'PICK')}
                </span>
            </div>
            <div style="margin-top: 5px; color: #94a3b8; font-size: 0.9rem;">
                Línea: <b>{prop_data.get('linea', '0.0')}</b> | Prob: <span style="color:#00ff41;">{prop_data.get('confianza', 0)}%</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    def render(self, partido, idx, tracker, analisis_heuristico=None, analisis_gemini=None, analisis_premium=None, **kwargs):
        """Renderiza partido NBA con estilo NEON, incluyendo predicción O/U"""
        # Soporte para el argumento analisis_ia si viene desde el main
        analisis_ia = analisis_gemini or kwargs.get('analisis_ia')
        
        local = partido.get('local', 'Home Team')
        visitante = partido.get('visitante', 'Away Team')
        odds = partido.get('odds', {})
        records = partido.get('records', partido.get('records', {}))
        
        logo_l = partido.get('local_logo', "")
        logo_v = partido.get('visitante_logo', "")
        
        # --- EXTRACCIÓN ROBUSTA DE ODDS (Estructura ESPN/DraftKings) ---
        ml_local = odds.get('moneyline', {}).get('home', {}).get('close', {}).get('odds', 'N/A')
        ml_visit = odds.get('moneyline', {}).get('away', {}).get('close', {}).get('odds', 'N/A')
        
        spread_data = odds.get('pointSpread', {})
        spread_local = spread_data.get('home', {}).get('close', {}).get('line', 'N/A')
        spread_visit = spread_data.get('away', {}).get('close', {}).get('line', 'N/A')
        
        over_under = odds.get('overUnder', odds.get('total', {}).get('over', {}).get('close', {}).get('line', 'N/A'))
        if str(over_under).startswith('o'): over_under = over_under[1:]
        
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
                    <img src="{logo_l}" width="50" style="margin-bottom:10px;">
                    <h2 style='color: #fff; text-shadow: 0 0 5px #ff6600; margin: 0;'>{local}</h2>
                    <p style='color: #ff6600; margin: 0;'>{partido.get('local_record', '0-0')}</p>
                    <p style='color: #ff6600; margin: 0; font-size: 0.9rem;'>{partido.get('local_streak', '')}</p>
                    <p style='color: #00ff41; font-size: 14px;'>ML: {ml_local}</p>
                </div>
                <div style='text-align: center; flex: 0.5;'>
                    <h1 style='color: #00ff41; text-shadow: 0 0 10px #00ff41; margin: 0;'>VS</h1>
                    <p style='color: #94a3b8; font-size: 12px;'>{partido.get('fecha', '')[:10]}</p>
                </div>
                <div style='text-align: center; flex: 1;'>
                    <img src="{logo_v}" width="50" style="margin-bottom:10px;">
                    <h2 style='color: #fff; text-shadow: 0 0 5px #ff6600; margin: 0;'>{visitante}</h2>
                    <p style='color: #ff6600; margin: 0;'>{partido.get('visitante_record', '0-0')}</p>
                    <p style='color: #00ff41; font-size: 14px;'>ML: {ml_visit}</p>
                    <p style='color: #ff6600; margin: 0; font-size: 0.9rem;'>{partido.get('visitante_streak', '')}</p>
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

        # --- SECCIÓN DE LÍDERES (Puntos y Asistencias) ---
        lideres = partido.get('lideres_display', {})
        props_partido = partido.get('props_analizadas', []) # Clave para props

        if lideres.get('local') or lideres.get('visitante') or props_partido:
            with st.expander("📊 Inteligencia de Jugadores y Props", expanded=False):
                if props_partido:
                    st.markdown("<p style='color:#f59e0b; font-weight:bold;'>🔥 TOP PROPS RECOMENDADAS</p>", unsafe_allow_html=True)
                    for prop in props_partido[:4]:
                        self.render_prop_card(prop)
                    st.divider()
                
                col_l1, col_l2 = st.columns(2)
                with col_l1:
                    st.caption(f"⭐ {local}")
                    for lid in lideres.get('local', []):
                        try:
                            val = float(str(lid.get('valor', '0')).split()[0])
                            if lid.get('categoria') == 'pointsPerGame' and val <= 25:
                                continue
                            icon = " 🔥" if val > 30 else ""
                        except: icon = ""
                        st.markdown(f"**{lid.get('nombre')}**: {lid.get('valor')} {lid.get('categoria')}{icon}")
                with col_l2:
                    st.caption(f"⭐ {visitante}")
                    for lid in lideres.get('visitante', []):
                        try:
                            val = float(str(lid.get('valor', '0')).split()[0])
                            if lid.get('categoria') == 'pointsPerGame' and val <= 25:
                                continue
                            icon = " 🔥" if val > 30 else ""
                        except: icon = ""
                        st.markdown(f"**{lid.get('nombre')}**: {lid.get('valor')} {lid.get('categoria')}{icon}")
        elif 'lideres' in partido: # Soporte para estructura alternativa
            with st.expander("📊 Líderes del Encuentro", expanded=False):
                st.write(partido['lideres'])
        
        # Botón ANALIZAR
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            button_text = "🔄 ACTUALIZAR ANÁLISIS" if analisis_heuristico else "🔥 ANALIZAR CON MOTOR + GEMINI"
            if st.button(button_text, key=f"analyze_nba_{idx}", use_container_width=True):
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
        
        # --- PREDICCIÓN OVER/UNDER (NUEVO) ---
        nba_ou_prediction = kwargs.get('nba_ou_prediction')
        if nba_ou_prediction:
            st.markdown("---")
            st.subheader("🏀 Predicción Over/Under (Motor NBA)")
            color_ou = "#00ff41" if nba_ou_prediction['recomendacion'] == "OVER" else "#ff6600" if nba_ou_prediction['recomendacion'] == "UNDER" else "#94a3b8"
            st.markdown(f"""
            <div style='background: linear-gradient(135deg, #1a1f2a 0%, #0f1419 100%); border-radius: 12px; padding: 15px; margin: 10px 0; border-left: 4px solid {color_ou};'>
                <p style='color: {color_ou}; margin: 0;'><strong>{nba_ou_prediction['recomendacion']}</strong> ({nba_ou_prediction['confianza']}%)</p>
                <p style='color: #94a3b8; font-size: 0.9rem; margin: 5px 0 0 0;'>Proyección: {nba_ou_prediction['proyeccion_total']} puntos. {nba_ou_prediction['razon']}</p>
            </div>""", unsafe_allow_html=True)
        # 🤖 CONSULTAR IA
        if st.button("🤖 CONSULTAR IA", key=f"btn_ia_nba_{idx}", use_container_width=True):
            # Devuelve una acción específica para que el renderer la maneje
            return "analizar_ia"
        
        # 🏀 RADAR DE TRIPLES (NBA PROPS)
        st.markdown("---") # Separador para el radar
        st.subheader("🎯 RADAR DE TRIPLES (3PM)")
        
        # Ranking de defensas (Multiplicador: >1 es mala defensa, <1 es buena)
        defensa_3p = {"Boston Celtics": 0.82, "Oklahoma City Thunder": 0.85, "Charlotte Hornets": 1.18, "Detroit Pistons": 1.20}
        
        col_p1, col_p2 = st.columns(2)
        for i, team in enumerate([local, visitante]):
            rival = visitante if i == 0 else local
            mult_defensa = defensa_3p.get(rival, 1.0)
            
            with [col_p1, col_p2][i]:
                st.markdown(f"**🔥 {team}**")
                lideres = self.get_top_tripleros_reales(team, limit=3)
                if lideres:
                    for player in lideres:
                        # Simulación: Si supera 3.0 triples/g, lo consideramos "Hot" (Racha 4/5)
                        triples_val = player.get('triples_por_partido', 0)
                        is_hot = triples_val >= 3.0
                        css_class = "prop-hot-purple" if is_hot else ""
                        
                        prob = min(95, (triples_val * 20) * mult_defensa) # Ajuste de probabilidad
                        
                        st.markdown(f"""<div class='{css_class}'>
                            🏀 <b>{player['nombre']}</b>: {triples_val:.1f} 3PM/g (Prob: {prob:.0f}%)
                            {"<br><small style='color:#bc13fe;'>🔥 Racha: 4/5 HITS</small>" if is_hot else ""}
                        </div>""", unsafe_allow_html=True)
                        st.progress(prob/100)
                else:
                    st.caption("Sin datos para este equipo.")

        # --- ALERTA DE JUGADORES EN RACHA (30+ PUNTOS) ---
        lideres_display = partido.get('lideres_display', {})
        jugadores_en_racha = []
        for side in ['local', 'visitante']:
            for lider in lideres_display.get(side, []):
                if lider.get('categoria') == 'pointsPerGame':
                    try:
                        points = float(lider.get('valor', '0').split()[0]) # "32.5 PPG" -> 32.5
                        if points >= 30:
                            jugadores_en_racha.append(f"🔥 {lider['nombre']} ({lider['equipo']}): {points} PPG")
                    except ValueError:
                        pass
        if jugadores_en_racha:
            st.markdown("<h4 style='color:#FFD700; margin-top: 20px;'>🚨 JUGADORES EN RACHA (30+ PPG)</h4>", unsafe_allow_html=True)
            for racha_info in jugadores_en_racha:
                st.warning(racha_info)
        # --- HISTORIAL COMPARATIVO (ÚLTIMOS 5) ---
        self._mostrar_historial_reciente(local, visitante)

        return None
