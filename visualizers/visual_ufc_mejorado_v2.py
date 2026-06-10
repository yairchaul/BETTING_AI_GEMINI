# -*- coding: utf-8 -*-
"""
VISUAL UFC MEJORADO V2 - Muestra TODAS las stats extraídas del scraper
Optimizado para mostrar: SLpM, Str.Acc, TD Avg, TD Def, Sub Avg, etc.
"""

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
                st.markdown(f"## 🔴 {p1.get('nombre', 'Desconocido')}")
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
                stats1 = p1.get('estadisticas_carrera', {})
                if stats1:
                    with st.expander("📊 ESTADÍSTICAS DE CARRERA COMPLETAS", expanded=False):
                        col_s1, col_s2, col_s3 = st.columns(3)
                        
                        with col_s1:
                            st.metric("SLpM", f"{stats1.get('sig_strikes_landed_per_min', 0):.2f}")
                            st.metric("Precisión", f"{stats1.get('sig_strike_accuracy', 0):.1f}%")
                            st.metric("Defensa Golpes", f"{stats1.get('sig_strike_defense', 0):.1f}%")
                        
                        with col_s2:
                            st.metric("TD Avg/15min", f"{stats1.get('td_avg_per_15min', 0):.2f}")
                            st.metric("TD Defensa", f"{stats1.get('td_defense', 0):.1f}%")
                            st.metric("TD Precisión", f"{stats1.get('td_accuracy', 0):.1f}%")
                        
                        with col_s3:
                            st.metric("Sub Avg/15min", f"{stats1.get('sub_avg_per_15min', 0):.2f}")
                            st.metric("Control Avg", f"{stats1.get('control_avg_time', 0):.2f} min")
                            st.metric("Tiempo Pelea", f"{stats1.get('avg_fight_time', 0):.2f} min")
            
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
                st.markdown(f"## 🔵 {p2.get('nombre', 'Desconocido')}")
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
                stats2 = p2.get('estadisticas_carrera', {})
                if stats2:
                    with st.expander("📊 ESTADÍSTICAS DE CARRERA COMPLETAS", expanded=False):
                        col_s1, col_s2, col_s3 = st.columns(3)
                        
                        with col_s1:
                            st.metric("SLpM", f"{stats2.get('sig_strikes_landed_per_min', 0):.2f}")
                            st.metric("Precisión", f"{stats2.get('sig_strike_accuracy', 0):.1f}%")
                            st.metric("Defensa Golpes", f"{stats2.get('sig_strike_defense', 0):.1f}%")
                        
                        with col_s2:
                            st.metric("TD Avg/15min", f"{stats2.get('td_avg_per_15min', 0):.2f}")
                            st.metric("TD Defensa", f"{stats2.get('td_defense', 0):.1f}%")
                            st.metric("TD Precisión", f"{stats2.get('td_accuracy', 0):.1f}%")
                        
                        with col_s3:
                            st.metric("Sub Avg/15min", f"{stats2.get('sub_avg_per_15min', 0):.2f}")
                            st.metric("Control Avg", f"{stats2.get('control_avg_time', 0):.2f} min")
                            st.metric("Tiempo Pelea", f"{stats2.get('avg_fight_time', 0):.2f} min")
            
            st.markdown("---")
            
            # Análisis de los motores
            col_a1, col_a2, col_a3 = st.columns(3)
            
            with col_a1:
                st.markdown("<h4 style='color: #FFD700;'>📊 HEURÍSTICO</h4>", unsafe_allow_html=True)
                if analisis_ufc:
                    apuesta = analisis_ufc.get('apuesta', 'N/A')
                    confianza = analisis_ufc.get('confianza', 0)
                    metodo = analisis_ufc.get('metodo', 'N/A')
                    
                    color_conf = '#4CAF50' if confianza >= 70 else '#FF9800' if confianza >= 50 else '#f44336'
                    
                    st.markdown(f"""
                    <div style="background-color: #2A2A2A; padding: 10px; border-radius: 5px;">
                        <p style='color: #FFF; font-weight: bold;'>{apuesta}</p>
                        <p style='color: {color_conf};'>Confianza: {confianza}%</p>
                        <p style='color: #888; font-size: 12px;'>{metodo}</p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown("<p style='color: #888;'>Pendiente de análisis</p>", unsafe_allow_html=True)
            
            with col_a2:
                st.markdown("<h4 style='color: #FFD700;'>🔬 PREMIUM ANALYTICS</h4>", unsafe_allow_html=True)
                if analisis_premium:
                    edge = analisis_premium.get('edge_rating', 0)
                    razones = analisis_premium.get('razones', [])
                    
                    # Estrellas coloridas
                    estrellas_llegas = min(10, int(edge))
                    estrellas = "★" * estrellas_llegas + "☆" * (10 - estrellas_llegas)
                    
                    st.markdown(f"""
                    <div style="background-color: #2A2A2A; padding: 10px; border-radius: 5px;">
                        <p style='color: #FFD700; font-weight: bold; font-size: 18px;'>{estrellas}</p>
                        <p style='color: #FFF;'>Edge Rating: {edge}/10</p>
                        <div style='max-height: 100px; overflow-y: auto;'>
                    """, unsafe_allow_html=True)
                    
                    for razon in razones[:3]:  # Mostrar solo 3 razones
                        st.markdown(f"<p style='color: #888; font-size: 11px; margin: 2px 0;'>• {razon[:60]}</p>", unsafe_allow_html=True)
                    
                    st.markdown("</div></div>", unsafe_allow_html=True)
                else:
                    st.markdown("<p style='color: #888;'>Pendiente de análisis</p>", unsafe_allow_html=True)
            
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
    
    def _completar_datos(self, peleador):
        """Completa datos faltantes con valores por defecto"""
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