# -*- coding: utf-8 -*-
"""
VISUALIZADOR MLB INTEGRADO - Usa el Motor MLB Completo
Integra: Lanzadores + Lineups + Alertas HR + Proyección K en tiempo real
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from motors.motor_mlb_completo import motor_mlb
from visualizers.hr_panel_pro import hr_panel_pro

class VisualMLBIntegrado:
    """Visualizador MLB que integra el motor completo"""
    
    def __init__(self):
        self.colores = {
            'elite': '#FFD700',  # Oro
            'alta': '#4CAF50',   # Verde
            'media': '#FF9800',  # Naranja
            'baja': '#f44336',   # Rojo
            'local': '#3b82f6',  # Azul
            'visitante': '#ef4444'  # Rojo
        }
        
    def render_partido_completo(self, partido, idx, clima_engine=None):
        """
        Renderiza un partido MLB completo con todos los datos integrados
        
        Args:
            partido: Diccionario con datos del partido
            idx: Índice del partido
            clima_engine: Motor de clima (opcional)
        """
        with st.container():
            # Obtener datos del motor completo
            home = partido.get('local', '')
            away = partido.get('visitante', '')
            
            # Obtener análisis de lanzadores
            pitchers_data = motor_mlb.obtener_analisis_lanzadores_hoy()
            home_pitcher = pitchers_data.get(home, {})
            away_pitcher = pitchers_data.get(away, {})
            
            # Obtener proyección de K
            proyeccion_k = motor_mlb.obtener_proyeccion_k_para_partido(home, away)
            
            # Obtener lineups
            lineups_data = motor_mlb.obtener_lineups_hoy()
            partido_lineup = None
            for p in lineups_data.get('partidos', []):
                if p['home'] == home and p['away'] == away:
                    partido_lineup = p
                    break
            
            # Renderizar encabezado
            self._render_header(partido, home_pitcher, away_pitcher, proyeccion_k)
            
            st.markdown("---")
            
            # Tabs principales
            tab1, tab2, tab3, tab4 = st.tabs(["📊 Análisis", "🧤 Pitchers", "💣 HR Alerts", "📋 Lineup"])
            
            with tab1:
                self._render_analisis_tab(partido, home_pitcher, away_pitcher, proyeccion_k)
            
            with tab2:
                self._render_pitchers_tab(home_pitcher, away_pitcher, proyeccion_k)
            
            with tab3:
                self._render_hr_alerts_tab(home, away, partido_lineup)
            
            with tab4:
                self._render_lineup_tab(partido_lineup)
            
            # Botones de acción
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("🔍 Analizar Detallado", key=f"analizar_{idx}", use_container_width=True):
                    st.session_state[f'analisis_detallado_{idx}'] = True
            
            with col2:
                if st.button("➕ Agregar al Parlay", key=f"parlay_{idx}", use_container_width=True):
                    self._agregar_al_parlay(partido, home_pitcher, away_pitcher, proyeccion_k)
            
            with col3:
                if st.button("🔄 Actualizar Datos", key=f"refresh_{idx}", use_container_width=True):
                    st.rerun()
    
    def _render_header(self, partido, home_pitcher, away_pitcher, proyeccion_k):
        """Renderiza el encabezado del partido con un diseño mejorado."""
        home = partido.get('local', '')
        away = partido.get('visitante', '')
        home_odds = partido.get('odds_local', 'N/A')
        home_logo = partido.get('local_logo', '')
        away_odds = partido.get('odds_visitante', 'N/A')
        away_logo = partido.get('visitante_logo', '')
        
        # Información de pitchers
        home_p_name = home_pitcher.get('lanzador', 'TBD')
        away_p_name = away_pitcher.get('lanzador', 'TBD')
        home_era = home_pitcher.get('era', 4.50)
        away_era = away_pitcher.get('era', 4.50)
        
        # Proyección K
        home_k_proy = proyeccion_k.get('home_k_proy', 5.0)
        away_k_proy = proyeccion_k.get('away_k_proy', 5.0)
        
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #0f172a, #1e293b); padding: 20px; border-radius: 15px; margin: 10px 0; border: 1px solid #3b82f6; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                
                <!-- Away Team -->
                <div style="text-align: center; flex: 1;">
                    <div style="display: flex; justify-content: center; align-items: center; gap: 10px; margin-bottom: 10px;">
                        <img src="{away_logo}" width="40" style="object-fit: contain; background: rgba(255,255,255,0.1); border-radius: 50%;">
                        <h3 style="color: {self.colores['local']}; margin: 0; font-size: 1.2rem;">{away}</h3>
                    </div>
                    <div style="font-size: 0.9rem; color: #94a3b8; text-align: left; padding-left: 15%;">
                        <p style="margin: 2px 0;">🧤 <strong>Pitcher:</strong> {away_p_name}</p>
                        <p style="margin: 2px 0;">⚾ <strong>Stats:</strong> ERA {away_era:.2f} | Proy. K {away_k_proy:.1f}</p>
                        <p style="margin: 2px 0;">📈 <strong>Odds:</strong> {away_odds}</p>
                    </div>
                </div>
                
                <!-- VS Separator -->
                <div style="text-align: center; margin: 0 10px; padding-top: 20px;">
                    <h2 style="color: #fff; margin: 0;">VS</h2>
                    <p style="color: #94a3b8; margin: 5px 0; font-size: 0.8rem;">⚾ MLB</p>
                </div>

                <!-- Home Team -->
                <div style="text-align: center; flex: 1;">
                    <div style="display: flex; justify-content: center; align-items: center; gap: 10px; margin-bottom: 10px;">
                        <img src="{home_logo}" width="40" style="object-fit: contain; background: rgba(255,255,255,0.1); border-radius: 50%;">
                        <h3 style="color: {self.colores['visitante']}; margin: 0; font-size: 1.2rem;">{home}</h3>
                    </div>
                    <div style="font-size: 0.9rem; color: #94a3b8; text-align: left; padding-left: 15%;">
                        <p style="margin: 2px 0;">🧤 <strong>Pitcher:</strong> {home_p_name}</p>
                        <p style="margin: 2px 0;">⚾ <strong>Stats:</strong> ERA {home_era:.2f} | Proy. K {home_k_proy:.1f}</p>
                        <p style="margin: 2px 0;">📈 <strong>Odds:</strong> {home_odds}</p>
                    </div>
                </div>
                
            </div>
            
            <div style="margin-top: 15px; text-align: center;">
                <span style="background: linear-gradient(90deg, #3b82f6, #9333ea); color: white; padding: 5px 15px; border-radius: 20px; font-size: 0.9rem;">
                    🎯 Proyección Total: {home_k_proy + away_k_proy:.1f} K | Recomendación: {proyeccion_k.get('recomendacion_k', 'N/A')}
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    def _render_analisis_tab(self, partido, home_pitcher, away_pitcher, proyeccion_k):
        """Renderiza la pestaña de análisis"""
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("##### 📊 Estadísticas Pitchers")
            
            # Home pitcher stats
            if home_pitcher:
                st.metric("🧤 Home Pitcher", home_pitcher.get('lanzador', 'N/A'))
                st.metric("K/9", f"{home_pitcher.get('k9', 0):.1f}")
                st.metric("ERA", f"{home_pitcher.get('era', 0):.2f}")
                st.metric("WHIP", f"{home_pitcher.get('whip', 0):.2f}")
            else:
                st.info("⏳ Esperando datos del pitcher local")
        
        with col2:
            st.markdown("##### ⚡ Comparación")
            
            # Comparación de stats
            home_k9 = home_pitcher.get('k9', 8.0) if home_pitcher else 8.0
            away_k9 = away_pitcher.get('k9', 8.0) if away_pitcher else 8.0
            
            diff_k9 = abs(home_k9 - away_k9)
            ventaja_k = "Local" if home_k9 > away_k9 else "Visitante" if away_k9 > home_k9 else "Igual"
            
            st.metric("📈 Diferencia K/9", f"{diff_k9:.1f}")
            st.metric("🏆 Ventaja K", ventaja_k)
            st.metric("🎯 Proyección Total K", f"{proyeccion_k.get('home_k_proy', 0) + proyeccion_k.get('away_k_proy', 0):.1f}")
            
            # Recomendación
            total_proy = proyeccion_k.get('home_k_proy', 0) + proyeccion_k.get('away_k_proy', 0)
            if total_proy > 12:
                st.success("🔥 OVER K recomendado")
            elif total_proy > 9:
                st.info("✅ K moderados esperados")
            else:
                st.warning("📊 K bajos esperados")
        
        with col3:
            st.markdown("##### 📊 Away Pitcher Stats")
            
            # Away pitcher stats
            if away_pitcher:
                st.metric("🧤 Away Pitcher", away_pitcher.get('lanzador', 'N/A'))
                st.metric("K/9", f"{away_pitcher.get('k9', 0):.1f}")
                st.metric("ERA", f"{away_pitcher.get('era', 0):.2f}")
                st.metric("WHIP", f"{away_pitcher.get('whip', 0):.2f}")
            else:
                st.info("⏳ Esperando datos del pitcher visitante")
        
        # Gráfico de comparación
        if home_pitcher and away_pitcher:
            fig_data = {
                'Metric': ['K/9', 'ERA', 'WHIP', 'HR/9'],
                'Home': [
                    home_pitcher.get('k9', 0),
                    home_pitcher.get('era', 0),
                    home_pitcher.get('whip', 0),
                    home_pitcher.get('hr9', 0)
                ],
                'Away': [
                    away_pitcher.get('k9', 0),
                    away_pitcher.get('era', 0),
                    away_pitcher.get('whip', 0),
                    away_pitcher.get('hr9', 0)
                ]
            }
            
            df = pd.DataFrame(fig_data)
            fig = px.bar(df, x='Metric', y=['Home', 'Away'], barmode='group',
                        title='Comparación de Pitchers',
                        color_discrete_map={'Home': self.colores['local'], 'Away': self.colores['visitante']})
            
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
    
    def _render_pitchers_tab(self, home_pitcher, away_pitcher, proyeccion_k):
        """Renderiza la pestaña de análisis de pitchers"""
        st.markdown("##### 🧤 ANÁLISIS DETALLADO DE PITCHERS")
        
        if not home_pitcher and not away_pitcher:
            st.info("⏳ Esperando datos de pitchers...")
            return
        
        col1, col2 = st.columns(2)
        
        with col1:
            if home_pitcher:
                st.markdown(f"""
                <div style="background: rgba(59, 130, 246, 0.1); padding: 15px; border-radius: 10px; border-left: 4px solid {self.colores['local']};">
                    <h4 style="color: {self.colores['local']}; margin: 0 0 10px 0;">🏠 {home_pitcher.get('lanzador', 'N/A')}</h4>
                    <p style="margin: 5px 0;"><strong>K/9:</strong> {home_pitcher.get('k9', 0):.1f}</p>
                    <p style="margin: 5px 0;"><strong>ERA:</strong> {home_pitcher.get('era', 0):.2f}</p>
                    <p style="margin: 5px 0;"><strong>WHIP:</strong> {home_pitcher.get('whip', 0):.2f}</p>
                    <p style="margin: 5px 0;"><strong>HR/9:</strong> {home_pitcher.get('hr9', 0):.2f}</p>
                    <p style="margin: 5px 0;"><strong>Proyección K:</strong> {proyeccion_k.get('home_k_proy', 0):.1f}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Evaluación del pitcher
                era = home_pitcher.get('era', 4.50)
                whip = home_pitcher.get('whip', 1.35)
                
                if era < 3.50 and whip < 1.20:
                    st.success("✅ Pitcher de élite")
                elif era < 4.00 and whip < 1.30:
                    st.info("👍 Pitcher sólido")
                else:
                    st.warning("⚠️ Pitcher vulnerable")
        
        with col2:
            if away_pitcher:
                st.markdown(f"""
                <div style="background: rgba(239, 68, 68, 0.1); padding: 15px; border-radius: 10px; border-left: 4px solid {self.colores['visitante']};">
                    <h4 style="color: {self.colores['visitante']}; margin: 0 0 10px 0;">✈️ {away_pitcher.get('lanzador', 'N/A')}</h4>
                    <p style="margin: 5px 0;"><strong>K/9:</strong> {away_pitcher.get('k9', 0):.1f}</p>
                    <p style="margin: 5px 0;"><strong>ERA:</strong> {away_pitcher.get('era', 0):.2f}</p>
                    <p style="margin: 5px 0;"><strong>WHIP:</strong> {away_pitcher.get('whip', 0):.2f}</p>
                    <p style="margin: 5px 0;"><strong>HR/9:</strong> {away_pitcher.get('hr9', 0):.2f}</p>
                    <p style="margin: 5px 0;"><strong>Proyección K:</strong> {proyeccion_k.get('away_k_proy', 0):.1f}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Evaluación del pitcher
                era = away_pitcher.get('era', 4.50)
                whip = away_pitcher.get('whip', 1.35)
                
                if era < 3.50 and whip < 1.20:
                    st.success("✅ Pitcher de élite")
                elif era < 4.00 and whip < 1.30:
                    st.info("👍 Pitcher sólido")
                else:
                    st.warning("⚠️ Pitcher vulnerable")
        
        # Recomendación de apuesta K
        st.markdown("---")
        st.markdown("##### 🎯 RECOMENDACIÓN DE APUESTA K")
        
        total_k_proy = proyeccion_k.get('home_k_proy', 0) + proyeccion_k.get('away_k_proy', 0)
        
        if total_k_proy > 12:
            st.markdown(f"""
            <div style="background: linear-gradient(90deg, rgba(76, 175, 80, 0.2), rgba(76, 175, 80, 0.1)); padding: 15px; border-radius: 10px; border-left: 4px solid #4CAF50;">
                <h4 style="color: #4CAF50; margin: 0;">🔥 OVER K RECOMENDADO</h4>
                <p style="margin: 10px 0; color: #fff;">Proyección total: <strong>{total_k_proy:.1f} K</strong></p>
                <p style="margin: 0; color: #94a3b8;">Ambos pitchers tienen buen K/9. Expectativas altas de strikes.</p>
            </div>
            """, unsafe_allow_html=True)
        elif total_k_proy > 9:
            st.markdown(f"""
            <div style="background: linear-gradient(90deg, rgba(255, 152, 0, 0.2), rgba(255, 152, 0, 0.1)); padding: 15px; border-radius: 10px; border-left: 4px solid #FF9800;">
                <h4 style="color: #FF9800; margin: 0;">✅ K MODERADOS ESPERADOS</h4>
                <p style="margin: 10px 0; color: #fff;">Proyección total: <strong>{total_k_proy:.1f} K</strong></p>
                <p style="margin: 0; color: #94a3b8;">Pitchers con rendimiento promedio en strikes.</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="background: linear-gradient(90deg, rgba(244, 67, 54, 0.2), rgba(244, 67, 54, 0.1)); padding: 15px; border-radius: 10px; border-left: 4px solid #f44336;">
                <h4 style="color: #f44336; margin: 0;">📊 K BAJOS ESPERADOS</h4>
                <p style="margin: 10px 0; color: #fff;">Proyección total: <strong>{total_k_proy:.1f} K</strong></p>
                <p style="margin: 0; color: #94a3b8;">Pitchers con bajo K/9. Considerar UNDER en prop de strikes.</p>
            </div>
            """, unsafe_allow_html=True)
    
    def _render_hr_alerts_tab(self, home, away, partido_lineup):
        """Renderiza la pestaña de alertas HR"""
        st.markdown("##### 💣 ALERTAS DE HOME RUN")
        
        # Obtener alertas HR para este partido
        alertas_df = motor_mlb.generar_alertas_hr_hoy()
        
        if isinstance(alertas_df, pd.DataFrame) and not alertas_df.empty:
            # Filtrar alertas para este partido
            partido_matchup = f"{away} @ {home}"
            alertas_partido = alertas_df[alertas_df['Partido'] == partido_matchup]
            
            if not alertas_partido.empty:
                for _, alerta in alertas_partido.iterrows():
                    conf_color = self.colores['elite'] if "ELITE" in str(alerta['Confianza']) else self.colores['alta']
                    
                    st.markdown(f"""
                    <div style="background: rgba(255, 215, 0, 0.1); padding: 15px; border-radius: 10px; border-left: 4px solid {conf_color}; margin: 10px 0;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <h4 style="color: {conf_color}; margin: 0;">💣 {alerta['Bateador']}</h4>
                                <p style="margin: 5px 0; color: #94a3b8;">vs {alerta['Pitcher_Rival']} (WHIP: {alerta['WHIP_Rival']}, HR/9: {alerta['HR9_Rival']})</p>
                            </div>
                            <span style="background: {conf_color}; color: #000; padding: 3px 10px; border-radius: 15px; font-weight: bold;">
                                {alerta['Confianza']}
                            </span>
                        </div>
                        <p style="margin: 10px 0 0 0; color: #fff;">{alerta['Recomendacion']}</p>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("ℹ️ No hay alertas HR específicas para este partido")
        else:
            st.info("⏳ Generando alertas HR...")
            
            if partido_lineup and partido_lineup.get('confirmed'):
                st.warning("⚠️ Lineups confirmados pero no hay alertas HR. Los pitchers pueden no ser vulnerables.")
            else:
                st.info("🔍 Esperando lineups oficiales para generar alertas HR")
    
    def _render_lineup_tab(self, partido_lineup):
        """Renderiza la pestaña de lineup"""
        if not partido_lineup:
            st.info("⏳ Esperando datos de lineup...")
            return
        
        confirmed = partido_lineup.get('confirmed', False)
        
        if confirmed:
            st.success(f"✅ LINEUP CONFIRMADO ({partido_lineup.get('total_players', 0)} jugadores)")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"##### ✈️ {partido_lineup.get('away', 'Visitante')}")
                for player in partido_lineup.get('away_players', []):
                    st.markdown(f"• {player.get('nombre', 'N/A')} ({player.get('posicion', 'N/A')})")
            
            with col2:
                st.markdown(f"##### 🏠 {partido_lineup.get('home', 'Local')}")
                for player in partido_lineup.get('home_players', []):
                    st.markdown(f"• {player.get('nombre', 'N/A')} ({player.get('posicion', 'N/A')})")
        else:
            st.warning("⚠️ LINEUP NO CONFIRMADO")
            st.info("Esperando el reporte oficial del manager. Los lineups se actualizan aproximadamente 1-2 horas antes del partido.")
    
    def _agregar_al_parlay(self, partido, home_pitcher, away_pitcher, proyeccion_k):
        """Agrega el partido al parlay"""
        home = partido.get('local', '')
        away = partido.get('visitante', '')
        
        pick_data = {
            'deporte': 'MLB',
            'partido': f"{away} @ {home}",
            'home': home,
            'away': away,
            'home_pitcher': home_pitcher.get('lanzador', 'TBD'),
            'away_pitcher': away_pitcher.get('lanzador', 'TBD'),
            'proyeccion_k': proyeccion_k.get('recomendacion_k', 'N/A'),
            'total_k_proy': proyeccion_k.get('home_k_proy', 0) + proyeccion_k.get('away_k_proy', 0),
            'timestamp': datetime.now().isoformat()
        }
        
        if 'parlay_mlb' not in st.session_state:
            st.session_state.parlay_mlb = []
        
        st.session_state.parlay_mlb.append(pick_data)
        st.success(f"✅ {away} @ {home} agregado al parlay")


# Instancia global para uso fácil
visual_mlb_integrado = VisualMLBIntegrado()

if __name__ == "__main__":
    # Test del visualizador
    print("🧪 Test Visualizador MLB Integrado")
    
    # Datos de prueba
    partido_prueba = {
        'local': 'New York Yankees',
        'visitante': 'Boston Red Sox',
        'odds_local': '-150',
        'odds_visitante': '+130'
    }
    
    # En un entorno Streamlit, esto se ejecutaría automáticamente
    print("✅ Visualizador MLB Integrado creado correctamente")
    print("📋 Métodos disponibles:")
    print("   • render_partido_completo() - Renderiza partido completo")
    print("   • Integra con motor_mlb.obtener_analisis_lanzadores_hoy()")
    print("   • Integra con motor_mlb.generar_alertas_hr_hoy()")
    print("   • Integra con motor_mlb.obtener_lineups_hoy()")