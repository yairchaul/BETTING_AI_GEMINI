# visual_mlb_base.py
# -*- coding: utf-8 -*-
import streamlit as st
import plotly.express as px
import pandas as pd
import os
import json
from abc import ABC, abstractmethod
from utils.equipo_trampa_loader import EquipoTrampaLoader

class VisualMLBBase(ABC):
    """
    Clase base abstracta para renderizar partidos de MLB en Streamlit.
    Contiene la lógica común y define la estructura que las subclases deben implementar.
    """
    def __init__(self, ou_motor, era_threshold=5.0):
        self.ou_motor = ou_motor
        self.era_threshold = era_threshold
        self._load_recent_results()
        self.equipo_trampa_loader = EquipoTrampaLoader()

    def _load_daily_ou_factor(self):
        """Carga el factor de ajuste diario para Over/Under desde un archivo."""
        try:
            with open("data/factor_ou_diario.json", "r", encoding="utf-8") as f:
                return json.load(f).get("factor_ou", 0.0)
        except (FileNotFoundError, json.JSONDecodeError):
            return 0.0

    def render(self, partido, idx, tracker, analisis_mlb=None, clima_engine=None, **kwargs):
        """
        Método principal que orquesta el renderizado de un partido.
        """
        # 1. Extracción y preparación de datos comunes
        common_data = self._extract_common_data(partido)
        
        # 2. Lógica común: Detección de equipos trampa
        common_data['local_label'], common_data['visit_label'] = self._get_team_labels(
            common_data['local'], common_data['visitante']
        )

        # 3. Lógica específica (subclase): Predicción de strikes
        strike_local, strike_visitante = self._predict_strikes(
            common_data['pitcher_local'], common_data['pitcher_visitante'],
            common_data['local'], common_data['visitante']
        )
        common_data['strike_local'] = strike_local
        common_data['strike_visitante'] = strike_visitante

        # 4. Lógica común: Cálculo de Over/Under
        res_ou = self.ou_motor.calcular_total(partido)
        
        # Aplicar factor de ajuste de tendencia diaria (NUEVO)
        daily_ou_factor = self._load_daily_ou_factor()
        if daily_ou_factor != 0.0 and 'total_proyectado' in res_ou and isinstance(res_ou['total_proyectado'], (int, float)):
            res_ou['total_proyectado'] = round(res_ou['total_proyectado'] + daily_ou_factor, 2)
        
        common_data['res_ou'] = res_ou

        # 5. Lógica común: Alertas de vulnerabilidad de Pitcher
        self._render_vulnerable_pitcher_alerts(
            common_data['pitcher_local'], common_data['pitcher_visitante']
        )

        # --- RENDERIZADO DE COMPONENTES (Implementado por subclases) ---

        # Encabezado del partido
        self._render_header(partido=partido, common_data=common_data, **kwargs)

        # Alertas y recomendaciones si el análisis está disponible
        if analisis_mlb:
            self._render_alerts_and_recommendations(analisis_mlb)
        else:
            self._render_pre_analysis_placeholder(analisis_mlb)

        # Total proyectado (Over/Under)
        self._render_projected_total(res_ou)

        # Proyección de Strikes
        self._render_strike_projection(strike_local, strike_visitante, common_data['pitcher_local'], common_data['pitcher_visitante'])

        # Panel de Home Runs
        self._render_hr_panel(partido, idx, analisis_mlb, clima_engine, **kwargs)

        # Historial reciente
        self._render_recent_history(common_data['local'], common_data['visitante'])

        # Botón de análisis
        return self._render_analysis_button(idx, partido, analisis_mlb)

    def _extract_common_data(self, partido):
        """Extrae datos comunes del diccionario del partido."""
        pitchers = partido.get('pitchers', {}) or {}
        local_pitcher_info = pitchers.get('local', {}) or {}
        visitante_pitcher_info = pitchers.get('visitante', {}) or {}

        return {
            'local': partido.get('local', 'Local'),
            'visitante': partido.get('visitante', 'Visitante'),
            'local_rec': partido.get('local_record', '0-0'),
            'visit_rec': partido.get('visit_record') or partido.get('visitante_record') or '0-0',
            'odds': partido.get('odds', {}),
            'local_streak': partido.get('local_streak', ''),
            'visitante_streak': partido.get('visitante_streak', ''),
            'local_logo': partido.get('local_logo', ''),
            'visitante_logo': partido.get('visitante_logo', ''),
            'pitcher_local': local_pitcher_info.get('nombre', 'TBD'),
            'pitcher_visitante': visitante_pitcher_info.get('nombre', 'TBD'),
        }

    def _load_recent_results(self):
        """Carga los resultados recientes desde el archivo JSON al inicializar."""
        self.recent_results = []
        path_res = "data/resultados_reales_15dias.json"
        try:
            if not os.path.exists(path_res):
                path_res = "resultados_reales_15dias.json" # Fallback
            with open(path_res, "r", encoding="utf-8") as f:
                self.recent_results = json.load(f)
        except Exception:
            self.recent_results = []

    def _get_team_history(self, team_name):
        """Filtra y devuelve el historial reciente de un equipo desde los datos cargados."""
        hist = [r for r in self.recent_results if r.get('home') == team_name or r.get('away') == team_name]
        return sorted(hist, key=lambda x: x.get('fecha', ''), reverse=True)[:5]

    def _get_team_labels(self, local, visitante):
        """Genera etiquetas para los equipos, marcando los 'equipos trampa' usando el loader sin estado."""
        equipos_trampa = self.equipo_trampa_loader.load()
        local_label = f"⚠️ {local}" if any(local.lower() in t.lower() for t in equipos_trampa) else local
        visit_label = f"⚠️ {visitante}" if any(visitante.lower() in t.lower() for t in equipos_trampa) else visitante
        return local_label, visit_label

    def _render_vulnerable_pitcher_alerts(self, pitcher_local, pitcher_visitante):
        """Muestra una alerta si un pitcher tiene una ERA reciente > 5.0."""
        datos_k = st.session_state.get("datos_k", {})
        for p_name, side_label in [(pitcher_local, "Local"), (pitcher_visitante, "Visitante")]:
            if p_name != 'TBD':
                for info in datos_k.values():
                    if info.get("lanzador", "").lower() == p_name.lower():
                        era = info.get("era_reciente", 0.0)
                        if era > self.era_threshold:
                            st.error(f"🎯 **PITCHER VULNERABLE:** {p_name} ({side_label}) tiene una ERA reciente de **{era:.2f}**. ¡Oportunidad para OVER o Bateo!")
                            st.toast(f"Riesgo detectado: {p_name}", icon="🔥")
                        break
    
    @abstractmethod
    def _predict_strikes(self, pitcher_local, pitcher_visitante, local, visitante): pass
    @abstractmethod
    def _render_header(self, partido, common_data, **kwargs): pass
    @abstractmethod
    def _render_alerts_and_recommendations(self, analisis_mlb): pass
    def _render_pre_analysis_placeholder(self, analisis_mlb): pass
    @abstractmethod
    def _render_projected_total(self, res_ou): pass
    def _render_strike_projection(self, strike_local, strike_visitante, pitcher_local, pitcher_visitante):
        """Renderiza proyección de strikes unificada (estilo Pro)."""
        st.markdown("### ⚡ PROYECCIÓN DE STRIKES (K) - ANÁLISIS PITCHER")
        
        col1, col2 = st.columns(2)
        
        for i, (strike, pitcher, equipo_tipo) in enumerate([
            (strike_local, pitcher_local, "Local"),
            (strike_visitante, pitcher_visitante, "Visitante")
        ]):
            with [col1, col2][i]:
                color_fondo = "rgba(59, 130, 246, 0.1)" if i == 0 else "rgba(239, 68, 68, 0.1)"
                color_borde = "#3b82f6" if i == 0 else "#ef4444"
                
                if strike:
                    # Determinar color de recomendación
                    if "OVER" in strike['recomendacion']:
                        color_rec = "#00ff41"
                        icono_rec = "📈"
                    elif "UNDER" in strike['recomendacion']:
                        color_rec = "#ef4444"
                        icono_rec = "📉"
                    else:
                        color_rec = "#94a3b8"
                        icono_rec = "📊"
                    
                    html = f"""
                    <div style='background: {color_fondo}; padding: 15px; border-radius: 10px; border-left: 4px solid {color_borde}; margin-bottom: 10px;'>
                        <div style='display: flex; justify-content: space-between; align-items: center;'>
                            <div>
                                <h4 style='color:#fff; margin:0; font-size: 16px;'>🥎 {pitcher}</h4>
                                <p style='color:#94a3b8; font-size:12px; margin:5px 0;'>{equipo_tipo}</p>
                            </div>
                            <div style='text-align: right;'>
                                <h3 style='color:{color_rec}; margin:0; font-size: 24px;'>{strike['k_proyectados']}</h3>
                                <p style='color:#f59e0b; font-size:12px; margin:0;'>K Proyectados</p>
                            </div>
                        </div>
                        
                        <div style='margin-top: 10px;'>
                            <div style='display: flex; justify-content: space-between;'>
                                <span style='color:#94a3b8; font-size:12px;'>K/9: <b style='color:#f59e0b;'>{strike.get('k9', 0)}</b></span>
                                <span style='color:#94a3b8; font-size:12px;'>Confianza: <b style='color:{color_rec};'>{strike['confianza']}%</b></span>
                            </div>
                            <div style='margin-top: 8px; padding: 8px; background: rgba(0,0,0,0.2); border-radius: 5px;'>
                                <p style='color:{color_rec}; margin:0; font-weight:bold; font-size:14px;'>{icono_rec} {strike['recomendacion']}</p>
                            </div>
                        </div>
                    </div>
                    """
                    st.markdown(html, unsafe_allow_html=True)
                else:
                    st.warning(f"🥎 {pitcher} - Datos de pitcher no disponibles")

    def _render_hr_panel(self, partido, idx, analisis_mlb, clima_engine, **kwargs):
        """Renderiza el panel de HR estándar."""
        st.markdown("### 💣 RADAR DE JONRONES (POWER RADAR)")
        
        hr_l = analisis_mlb.get('top_hr_local', []) if analisis_mlb else partido.get('hr_candidates_local', [])
        hr_v = analisis_mlb.get('top_hr_visit', []) if analisis_mlb else partido.get('hr_candidates_visit', [])
        
        pitcher_local = partido.get('pitchers', {}).get('local', {}).get('nombre', 'TBD')
        pitcher_visitante = partido.get('pitchers', {}).get('visitante', {}).get('nombre', 'TBD')
        local = partido.get('local', 'Local')
        visitante = partido.get('visitante', 'Visitante')

        if (hr_l or hr_v):
            if analisis_mlb:
                self._mostrar_grafico_hr(analisis_mlb, partido.get('venue'), clima_engine)
            
            c_hr1, c_hr2 = st.columns(2)
            with c_hr1:
                st.markdown(f"**🚀 {local}**")
                for b in (hr_l[:3] if hr_l else []):
                    nombre = b.get('nombre') or b.get('bateador')
                    st.markdown(f"**{nombre}**")
                    prob = b.get('probabilidad', 0)
                    st.markdown(f"<span style='color:#00ff41;'>{prob}%</span> vs {pitcher_visitante}", unsafe_allow_html=True)
            with c_hr2:
                st.markdown(f"**🚀 {visitante}**")
                for b in (hr_v[:3] if hr_v else []):
                    nombre = b.get('nombre') or b.get('bateador')
                    st.markdown(f"**{nombre}**")
                    prob = b.get('probabilidad', 0)
                    st.markdown(f"<span style='color:#00ff41;'>{prob}%</span> vs {pitcher_local}", unsafe_allow_html=True)
        else:
            st.info("⏳ Esperando carga de Lineups oficiales para Radar de Poder.")

    def _mostrar_grafico_hr(self, analisis_mlb, venue, clima_engine):
        """Crea un gráfico interactivo de barras para las probabilidades de HR."""
        multiplier = 1.0
        weather_info = "Condiciones Normales"
        
        if clima_engine and venue:
            clima = clima_engine.obtener_clima(venue)
            if clima.get('wind_speed', 0) > 10 and clima.get('wind_dir') == 'Out':
                multiplier += 0.15
                weather_info = f"💨 Viento Out ({clima['wind_speed']} mph) | +15% Poder"
            if clima.get('temp', 70) > 85:
                multiplier += 0.10
                weather_info += " | 🌡️ Calor extremo (+10%)"

        hr_list = []
        for p in analisis_mlb.get('top_hr_local', []):
            prob_ajustada = min(98, p['probabilidad'] * multiplier)
            hr_list.append({"Jugador": p['nombre'], "Probabilidad": prob_ajustada, "Equipo": "Local"})
        for p in analisis_mlb.get('top_hr_visit', []):
            prob_ajustada = min(98, p['probabilidad'] * multiplier)
            hr_list.append({"Jugador": p['nombre'], "Probabilidad": prob_ajustada, "Equipo": "Visitante"})
        
        if hr_list:
            df_hr = pd.DataFrame(hr_list)
            fig = px.bar(df_hr, x="Jugador", y="Probabilidad", color="Equipo", 
                         text_auto='.1f', title=f"📊 Radar de Poder (Ajustado por Clima: {weather_info})",
                         color_discrete_map={"Local": "#3b82f6", "Visitante": "#ef4444"},
                         template="plotly_dark")
            fig.update_layout(yaxis_range=[0, 100], height=350, margin=dict(l=20, r=20, t=40, b=20))
            fig.update_traces(textposition='outside')
            st.plotly_chart(fig, use_container_width=True)

    def _render_recent_history(self, local, visitante):
        """Muestra historial reciente mejorado (unificado)."""
        st.markdown("### 🕒 Historial Reciente (Últimos 5 Juegos)")
        
        try:
            col1, col2 = st.columns(2)
            
            for i, team in enumerate([local, visitante]):
                with [col1, col2][i]:
                    color_equipo = "#3b82f6" if i == 0 else "#ef4444"
                    st.markdown(f"<h4 style='color:{color_equipo};'>{team}</h4>", unsafe_allow_html=True)
                    
                    history = self._get_team_history(team)
                    if history:
                        html = "<div style='overflow-x: auto;'>"
                        html += "<table style='width: 100%; border-collapse: collapse; font-size: 12px;'>"
                        html += "<thead><tr style='background: rgba(0,0,0,0.3);'><th style='padding: 5px; color:#94a3b8;'>Fecha</th><th style='padding: 5px; color:#94a3b8;'>Res</th><th style='padding: 5px; color:#94a3b8;'>Rival</th><th style='padding: 5px; color:#94a3b8;'>Score</th></tr></thead>"
                        html += "<tbody>"
                        
                        for g in history:
                            es_home = g.get('home') == team
                            score_home = g.get('home_score', 0)
                            score_away = g.get('away_score', 0)
                            
                            is_win = (es_home and score_home > score_away) or (not es_home and score_away > score_home)
                            
                            if is_win:
                                resultado_html = "<span style='color:#00ff41; font-weight:bold;'>✅ W</span>"
                            else:
                                resultado_html = "<span style='color:#ef4444; font-weight:bold;'>❌ L</span>"
                            
                            rival = g.get('away') if es_home else g.get('home')
                            score = f"{score_home}-{score_away}"
                            
                            html += f"<tr style='border-bottom: 1px solid rgba(255,255,255,0.1);'>"
                            html += f"<td style='padding: 5px; color:#94a3b8;'>{g.get('fecha', 'N/A')}</td>"
                            html += f"<td style='padding: 5px; text-align:center;'>{resultado_html}</td>"
                            html += f"<td style='padding: 5px; color:#fff;'>{rival}</td>"
                            html += f"<td style='padding: 5px; color:#fbbf24; font-weight:bold;'>{score}</td>"
                            html += "</tr>"
                        
                        html += "</tbody></table></div>"
                        st.markdown(html, unsafe_allow_html=True)
                    else:
                        st.caption("No hay historial disponible.")
        except Exception as e:
            st.caption(f"⚠️ Historial temporalmente no disponible: {e}")

    @abstractmethod
    def _render_analysis_button(self, idx, partido, analisis_mlb): pass
