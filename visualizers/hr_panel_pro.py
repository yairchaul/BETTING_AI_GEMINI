# -*- coding: utf-8 -*-
"""
HR PANEL PRO - Visualizador de Home Runs Integrado

Este módulo integra el Predictor HR Pro con el visualizador MLB principal.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
from motors.predictor_hr_pro import PredictorHRPro

class HRPanelPro:
    def __init__(self):
        self.predictor = PredictorHRPro()
        self.cache_key = "hr_analisis_cache"
    
    def render_panel(self, partido, idx, clima_engine=None):
        """
        Renderiza el panel completo de predicciones HR para un partido.
        
        Args:
            partido: Dict con información del partido
            idx: Índice del partido (para keys únicos)
            clima_engine: Instancia de motor de clima (opcional)
        """
        local = partido.get('local', 'Local')
        visitante = partido.get('visitante', 'Visitante')
        game_pk = partido.get('game_pk')
        estadio = partido.get('venue', '')
        
        # Obtener clima si está disponible
        clima = None
        if clima_engine and estadio:
            clima = clima_engine.obtener_clima(estadio)
        
        # Generar clave única para caché
        cache_key = f"{self.cache_key}_{local}_{visitante}_{game_pk}"
        
        # Verificar caché (< 15 minutos)
        use_cache = False
        if cache_key in st.session_state:
            cache_data = st.session_state[cache_key]
            cache_time = datetime.fromisoformat(cache_data.get('timestamp', '2023-01-01'))
            if datetime.now() - cache_time < pd.Timedelta(minutes=15):
                analisis_partido = cache_data.get('analisis')
                use_cache = True
                st.caption(f"📊 Datos HR cacheados ({cache_time.strftime('%H:%M')})")
        
        if not use_cache:
            # Ejecutar análisis
            with st.spinner(f"Analizando HR para {local} vs {visitante}..."):
                analisis_partido = self.predictor.analizar_partido_completo(
                    local, visitante, game_pk, estadio, clima
                )
                
                # Guardar en caché
                st.session_state[cache_key] = {
                    'analisis': analisis_partido,
                    'timestamp': datetime.now().isoformat()
                }
        
        # Renderizar panel
        self._render_analisis_panel(analisis_partido, partido)
        
        # Opcional: botón para forzar recálculo
        col1, col2, col3 = st.columns([2, 3, 2])
        with col2:
            if st.button("🔄 Actualizar Análisis HR", key=f"hr_refresh_{idx}", use_container_width=True):
                # Limpiar caché y recargar
                if cache_key in st.session_state:
                    del st.session_state[cache_key]
                st.rerun()
    
    def _render_analisis_panel(self, analisis_partido, partido_info):
        """Renderiza el análisis en formato visual"""
        local = partido_info.get('local', 'Local')
        visitante = partido_info.get('visitante', 'Visitante')
        
        # Encabezado
        st.markdown(f"""
        <div style='background: linear-gradient(90deg, #1e3a8a, #1e1b4b); padding: 15px; border-radius: 10px; margin-bottom: 15px; text-align: center;'>
            <h3 style='margin: 0; color: #60a5fa;'>💣 PREDICTOR HR PRO - POWER RADAR</h3>
            <p style='margin: 0; color: #94a3b8; font-size: 14px;'>{local} 🆚 {visitante}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Columnas para equipos
        col_local, col_visit = st.columns(2)
        
        # Bateadores locales
        with col_local:
            st.markdown(f"<h4 style='color: #3b82f6; text-align: center;'>{local}</h4>", unsafe_allow_html=True)
            
            if not analisis_partido.get('local'):
                st.info("⏳ Esperando datos de lineup")
            else:
                for bateador in analisis_partido['local']:
                    self._render_bateador_card(bateador, "local")
        
        # Bateadores visitantes
        with col_visit:
            st.markdown(f"<h4 style='color: #ef4444; text-align: center;'>{visitante}</h4>", unsafe_allow_html=True)
            
            if not analisis_partido.get('visitante'):
                st.info("⏳ Esperando datos de lineup")
            else:
                for bateador in analisis_partido['visitante']:
                    self._render_bateador_card(bateador, "visitante")
        
        # Resumen estadístico
        self._render_resumen_estadistico(analisis_partido)
        
        # Gráfico comparativo (opcional)
        if analisis_partido.get('local') and analisis_partido.get('visitante'):
            self._render_grafico_comparativo(analisis_partido)
    
    def _render_bateador_card(self, bateador, equipo_tipo):
        """Renderiza una tarjeta individual para cada bateador"""
        color_fondo = "rgba(59, 130, 246, 0.1)" if equipo_tipo == "local" else "rgba(239, 68, 68, 0.1)"
        color_borde = bateador.get('color', '#3b82f6')
        
        html = f"""
        <div style='background: {color_fondo}; padding: 12px; margin: 8px 0; border-radius: 10px; border-left: 4px solid {color_borde};'>
            <div style='display: flex; justify-content: space-between; align-items: center;'>
                <div style='flex: 1;'>
                    <strong style='color: #fff; font-size: 14px;'>{bateador['icono']} {bateador['nombre']}</strong><br>
                    <span style='color: #94a3b8; font-size: 11px;'>
                        vs {bateador['pitcher_rival']} ({bateador['mano_pitcher']})<br>
                        HR/9 pitcher: {bateador['hr9_pitcher']:.1f}
                    </span>
                </div>
                <div style='text-align: right;'>
                    <span style='color: {color_borde}; font-size: 20px; font-weight: bold;'>{bateador['probabilidad']}%</span><br>
                    <span style='color: #fbbf24; font-size: 12px; font-weight: bold;'>{bateador['stake']}</span>
                </div>
            </div>
            <div style='margin-top: 8px;'>
                <div style='display: flex; justify-content: space-between;'>
                    <span style='color: #94a3b8; font-size: 11px;'>
                        📊 {bateador['hr_total']} HR ({bateador['hr_por_juego']}/juego)
                    </span>
                    <span style='color: #fbbf24; font-size: 11px; font-weight: bold;'>
                        {bateador['recomendacion']}
                    </span>
                </div>
                <div style='margin-top: 5px;'>
                    <span style='color: #60a5fa; font-size: 10px;'>
                        {' • '.join(bateador.get('factores', [])[:2])}
                    </span>
                </div>
            </div>
        </div>
        """
        
        st.markdown(html, unsafe_allow_html=True)
        
        # Botón de acción rápida
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("📊", key=f"hr_detail_{bateador['nombre']}_{equipo_tipo}", 
                        help="Ver análisis detallado", use_container_width=True):
                self._mostrar_detalle_bateador(bateador)
    
    def _mostrar_detalle_bateador(self, bateador):
        """Muestra detalles expandidos del bateador"""
        with st.expander(f"📈 Análisis detallado: {bateador['nombre']}", expanded=False):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("HR Últimos 15 días", bateador['hr_total'])
            
            with col2:
                st.metric("HR por Juego", f"{bateador['hr_por_juego']}")
            
            with col3:
                st.metric("Probabilidad HR", f"{bateador['probabilidad']}%")
            
            # Factores de ajuste
            st.markdown("**🎯 Factores de Ajuste:**")
            for factor in bateador.get('factores', []):
                st.markdown(f"• {factor}")
            
            # Recomendación final
            st.markdown(f"""
            <div style='background: rgba(0, 255, 65, 0.1); padding: 10px; border-radius: 8px; margin-top: 10px; border: 1px solid #00ff41;'>
                <strong style='color: #00ff41;'>🎯 RECOMENDACIÓN FINAL:</strong><br>
                <span style='color: #fff;'><strong>{bateador['stake']} en {bateador['nombre']} para HR</strong></span><br>
                <span style='color: #94a3b8; font-size: 12px;'>vs {bateador['pitcher_rival']} ({bateador['mano_pitcher']})</span>
            </div>
            """, unsafe_allow_html=True)
    
    def _render_resumen_estadistico(self, analisis_partido):
        """Renderiza resumen estadístico del partido"""
        local_bateadores = analisis_partido.get('local', [])
        visit_bateadores = analisis_partido.get('visitante', [])
        
        if not local_bateadores and not visit_bateadores:
            return
        
        # Calcular estadísticas
        total_hr_local = sum(b['hr_total'] for b in local_bateadores)
        total_hr_visit = sum(b['hr_total'] for b in visit_bateadores)
        
        avg_prob_local = sum(b['probabilidad'] for b in local_bateadores) / max(len(local_bateadores), 1)
        avg_prob_visit = sum(b['probabilidad'] for b in visit_bateadores) / max(len(visit_bateadores), 1)
        
        elite_picks_local = sum(1 for b in local_bateadores if b['stake'] in ["3u", "4u"])
        elite_picks_visit = sum(1 for b in visit_bateadores if b['stake'] in ["3u", "4u"])
        
        # Mostrar estadísticas en columnas
        st.markdown("---")
        st.markdown("### 📊 RESUMEN ESTADÍSTICO")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("HR Total Local", total_hr_local, 
                     delta=f"{len(local_bateadores)} bateadores")
        
        with col2:
            st.metric("HR Total Visitante", total_hr_visit,
                     delta=f"{len(visit_bateadores)} bateadores")
        
        with col3:
            st.metric("Prob. Promedio", f"{max(avg_prob_local, avg_prob_visit):.1f}%",
                     delta=f"Local: {avg_prob_local:.1f}% | Visit: {avg_prob_visit:.1f}%")
        
        with col4:
            st.metric("Picks Élite", elite_picks_local + elite_picks_visit,
                     delta=f"Local: {elite_picks_local} | Visit: {elite_picks_visit}")
    
    def _render_grafico_comparativo(self, analisis_partido):
        """Renderiza gráfico comparativo de probabilidades"""
        try:
            # Preparar datos para gráfico
            datos = []
            
            for bateador in analisis_partido['local']:
                datos.append({
                    "Jugador": bateador['nombre'],
                    "Probabilidad": bateador['probabilidad'],
                    "Equipo": "Local",
                    "HR": bateador['hr_total']
                })
            
            for bateador in analisis_partido['visitante']:
                datos.append({
                    "Jugador": bateador['nombre'],
                    "Probabilidad": bateador['probabilidad'],
                    "Equipo": "Visitante",
                    "HR": bateador['hr_total']
                })
            
            if datos:
                df = pd.DataFrame(datos)
                
                # Crear gráfico de barras
                fig = px.bar(df, 
                           x="Jugador", 
                           y="Probabilidad", 
                           color="Equipo",
                           text="Probabilidad",
                           title="📈 Probabilidades de HR por Bateador",
                           color_discrete_map={"Local": "#3b82f6", "Visitante": "#ef4444"},
                           template="plotly_dark")
                
                fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                fig.update_layout(
                    yaxis_title="Probabilidad (%)",
                    xaxis_title="Bateador",
                    height=400,
                    showlegend=True
                )
                
                st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Error generando gráfico: {e}")
    
    def render_estadisticas_globales(self):
        """Renderiza estadísticas globales del predictor"""
        stats = self.predictor.obtener_estadisticas_pro()
        
        st.markdown("### 📈 ESTADÍSTICAS GLOBALES HR PRO")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Picks Totales", stats['total'])
        
        with col2:
            st.metric("Aciertos", stats['aciertos'])
        
        with col3:
            st.metric("Tasa de Acierto", f"{stats['tasa']}%")
        
        with col4:
            st.metric("ROI Estimado", f"+{(stats['tasa'] - 50) * 2:.1f}%")
        
        # Mostrar estadísticas por stake
        if stats.get('stake_stats'):
            st.markdown("#### 📊 Estadísticas por Stake")
            
            stake_data = []
            for stake, stake_stats in stats['stake_stats'].items():
                if stake_stats['total'] > 0:
                    tasa = (stake_stats['aciertos'] / stake_stats['total']) * 100
                    stake_data.append({
                        "Stake": stake,
                        "Total": stake_stats['total'],
                        "Aciertos": stake_stats['aciertos'],
                        "Tasa": round(tasa, 1)
                    })
            
            if stake_data:
                df_stake = pd.DataFrame(stake_data)
                st.dataframe(df_stake, use_container_width=True, hide_index=True)


# Instancia global para uso rápido
hr_panel_pro = HRPanelPro()