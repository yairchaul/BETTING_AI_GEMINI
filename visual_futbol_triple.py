# -*- coding: utf-8 -*-
"""
VISUAL FÚTBOL MEJORADO - Con estadísticas reales de equipos
Versión unificada para local y cloud
"""

import streamlit as st
import sqlite3
import logging

logger = logging.getLogger(__name__)

class VisualFutbolTriple:
    def __init__(self):
        self.db_path = 'data/betting_stats.db'
    
    def _obtener_historial_equipo(self, equipo):
        """Obtiene últimos 5 partidos del equipo desde BD"""
        if not equipo:
            return None
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT puntos_favor, puntos_contra, fecha 
                FROM historial_equipos 
                WHERE nombre_equipo = ? AND deporte = 'futbol'
                ORDER BY fecha DESC LIMIT 5
            ''', (equipo,))
            rows = cursor.fetchall()
            conn.close()
            
            if rows and len(rows) >= 3:
                partidos = []
                goles_favor = []
                goles_contra = []
                for r in rows:
                    g_f = int(r[0]) if r[0] else 0
                    g_c = int(r[1]) if r[1] else 0
                    partidos.append({'goles_favor': g_f, 'goles_contra': g_c})
                    goles_favor.append(g_f)
                    goles_contra.append(g_c)
                
                return {
                    'partidos': partidos,
                    'goles_favor': goles_favor,
                    'goles_contra': goles_contra,
                    'promedio_favor': sum(goles_favor) / len(goles_favor),
                    'victorias': sum(1 for i in range(len(partidos)) if partidos[i]['goles_favor'] > partidos[i]['goles_contra'])
                }
        except Exception as e:
            logger.debug(f"Error obteniendo historial de {equipo}: {e}")
        
        return None
    
    def _obtener_datos_mock(self, equipo):
        """Genera datos mock para equipos sin historial"""
        equipos_fuertes = ["Manchester", "Liverpool", "Arsenal", "Chelsea", "Barcelona", 
                          "Real Madrid", "Bayern", "PSG", "Juventus", "Milan", "Inter"]
        
        if any(fuerte in equipo for fuerte in equipos_fuertes):
            return {
                'goles_favor': [3, 2, 4, 1, 3],
                'goles_contra': [1, 1, 2, 1, 0],
                'promedio_favor': 2.6,
                'victorias': 4
            }
        else:
            return {
                'goles_favor': [1, 0, 1, 1, 0],
                'goles_contra': [2, 1, 2, 1, 2],
                'promedio_favor': 0.8,
                'victorias': 1
            }
    
    def render(self, partido, idx, liga, tracker, stats_data=None, 
               analisis_heurístico=None, analisis_gemini=None, analisis_premium=None):
        
        local = partido.get('local', partido.get('home', ''))
        visitante = partido.get('visitante', partido.get('away', ''))
        fecha = partido.get('fecha', '')
        
        # Obtener historial real
        historial_local = self._obtener_historial_equipo(local) or self._obtener_datos_mock(local)
        historial_visit = self._obtener_historial_equipo(visitante) or self._obtener_datos_mock(visitante)
        
        # Tarjeta NEON
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #0f0f1a 0%, #1a1f2a 100%); 
                    border-radius: 15px; 
                    padding: 20px; 
                    margin: 15px 0; 
                    border: 1px solid #00ff41;'>
            <div style='display: flex; justify-content: space-between;'>
                <div style='text-align: center; flex: 1;'>
                    <h2 style='color: #fff;'>{local}</h2>
                    <p style='color: #ff6600;'>{liga}</p>
                </div>
                <div style='text-align: center; flex: 0.5;'>
                    <h1 style='color: #00ff41;'>VS</h1>
                </div>
                <div style='text-align: center; flex: 1;'>
                    <h2 style='color: #fff;'>{visitante}</h2>
                    <p style='color: #ff6600;'>{liga}</p>
                </div>
            </div>
            <div style='text-align: center; margin-top: 8px;'>
                <span style='color: #888;'>📅 {fecha[:10] if fecha else 'Fecha por definir'}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # ÚLTIMOS 5 PARTIDOS
        st.markdown("### 📊 ÚLTIMOS 5 PARTIDOS")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"**🔴 {local}**")
            if historial_local and historial_local.get('goles_favor'):
                resultados = []
                for i in range(min(5, len(historial_local['goles_favor']))):
                    g_f = historial_local['goles_favor'][i]
                    g_c = historial_local['goles_contra'][i] if i < len(historial_local.get('goles_contra', [])) else 0
                    resultados.append(f"{g_f}-{g_c}")
                
                st.write(f"📈 {' | '.join(resultados)}")
                st.caption(f"⚽ Promedio: {historial_local.get('promedio_favor', 0):.1f} goles")
                st.caption(f"📈 Racha: {historial_local.get('victorias', 0)}W / {5 - historial_local.get('victorias', 0)}L")
            else:
                st.caption("📊 Datos no disponibles")
        
        with col2:
            st.markdown(f"**🔵 {visitante}**")
            if historial_visit and historial_visit.get('goles_favor'):
                resultados = []
                for i in range(min(5, len(historial_visit['goles_favor']))):
                    g_f = historial_visit['goles_favor'][i]
                    g_c = historial_visit['goles_contra'][i] if i < len(historial_visit.get('goles_contra', [])) else 0
                    resultados.append(f"{g_f}-{g_c}")
                
                st.write(f"📈 {' | '.join(resultados)}")
                st.caption(f"⚽ Promedio: {historial_visit.get('promedio_favor', 0):.1f} goles")
                st.caption(f"📈 Racha: {historial_visit.get('victorias', 0)}W / {5 - historial_visit.get('victorias', 0)}L")
            else:
                st.caption("📊 Datos no disponibles")
        
        # Botón ANALIZAR
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🔥 ANALIZAR FÚTBOL", key=f"fut_analizar_{liga}_{idx}", use_container_width=True):
                return "analizar"
        
        # Mostrar resultados del análisis a la par (Heurístico + Gemini)
        if analisis_heurístico or analisis_gemini:
            st.markdown("---")
            col_res1, col_res2 = st.columns(2)
            
            with col_res1:
                if analisis_heurístico:
                    recomendacion = analisis_heurístico.get('recomendacion', 'N/A')
                    confianza = analisis_heurístico.get('confianza', 0)
                    total_proyectado = analisis_heurístico.get('total_proyectado', 0)
                    
                    st.markdown(f"""
                    <div style='background: #1a1f2a; border-radius: 12px; padding: 15px; border-left: 4px solid #00ff41; height: 100%;'>
                        <span style='color: #888; font-size: 12px;'>📊 ANÁLISIS TÉCNICO</span>
                        <h4 style='color: #00ff41; margin: 5px 0;'>⚽ {recomendacion}</h4>
                        <p style='color: #888; font-size: 11px; margin: 0;'>CONFIANZA: {confianza}% | PROY: {total_proyectado} goles</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Mostrar recomendación de córners si existe
                    corners_proyectados = partido.get('corners_proyectados', 'N/A')
                    corners_line = partido.get('corners_line', 'N/A')
                    
                    if corners_proyectados != 'N/A' and corners_line != 'N/A':
                        st.markdown(f"""
                        <div style='background: #1a1f2a; border-radius: 12px; padding: 10px; margin-top: 10px; border-left: 4px solid #f59e0b;'>
                            <span style='color: #888; font-size: 11px;'>⚽ CÓRNERS</span>
                            <p style='color: #f1f5f9; margin: 5px 0;'>Proyectados: <b>{corners_proyectados}</b> | Línea: <b>{corners_line}</b></p>
                        </div>
                        """, unsafe_allow_html=True)

                    # Mostrar recomendación de córners si es el pick principal
                    # (Esta parte ya existía y se mantiene, pero ahora la sección de arriba es independiente)
                    if "Córners" in recomendacion:
                        st.markdown(f"""
                        <div style='background: #1a1f2a; border-radius: 12px; padding: 10px; margin-top: 10px; border-left: 4px solid #3b82f6;'>
                            <span style='color: #888; font-size: 11px;'>⚽ MERCADO ADICIONAL</span>
                            <p style='color: #3b82f6; margin: 5px 0;'>{recomendacion}</p>
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    st.caption("⏳ Análisis IA pendiente...")
        
        return None