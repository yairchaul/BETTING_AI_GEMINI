# radar_triples_nba.py
import streamlit as st
from balldontlie_client import balldontlie

class RadarTriplesNBA:
    """Detecta jugadores con alta probabilidad de anotar triples"""
    
    # IDs de equipos comunes (obtener con get_teams())
    TEAM_IDS = {
        "Lakers": 14,
        "Warriors": 15,
        "Celtics": 2,
        "Bucks": 16,
        "Nets": 17,
        "Suns": 21,
        "76ers": 20,
        "Mavericks": 6,
        "Nuggets": 7,
        "Heat": 12
    }
    
    def get_top_tripleros(self, team_name, limit=3):
        """Obtiene los mejores tripleros de un equipo"""
        team_id = self.TEAM_IDS.get(team_name)
        if not team_id:
            return []
        
        # Obtener jugadores del equipo
        players_data = balldontlie.get_players(team_id=team_id)
        players = players_data.get('data', [])
        
        tripleros = []
        for player in players:
            player_id = player.get('id')
            if player_id:
                stats = balldontlie.get_player_props(player_id)
                if stats and stats.get('fg3a', 0) > 2:
                    tripleros.append({
                        "nombre": player.get('first_name', '') + ' ' + player.get('last_name', ''),
                        "triples_por_partido": round(stats.get('fg3a', 0), 1),
                        "porcentaje_triple": round(stats.get('fg3_pct', 0) * 100, 1),
                        "puntos": round(stats.get('pts', 0), 1)
                    })
        
        # Ordenar por intentos de triple
        tripleros.sort(key=lambda x: x["triples_por_partido"], reverse=True)
        return tripleros[:limit]
    
    def render(self, equipo_local, equipo_visitante):
        """Renderiza el radar de triples en la UI"""
        st.markdown("### 🏀 RADAR DE TRIPLES")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"**🔵 {equipo_local}**")
            tripleros_local = self.get_top_tripleros(equipo_local)
            if tripleros_local:
                for t in tripleros_local:
                    color = "#10b981" if t["triples_por_partido"] >= 3 else "#f59e0b"
                    st.markdown(f"""
                    <div style="border-left: 3px solid {color}; padding-left: 10px; margin: 8px 0;">
                        <span style="color: {color}; font-weight: bold;">🎯 {t['nombre']}</span>
                        <br><span style="font-size: 12px;">📊 {t['triples_por_partido']} triples/partido | {t['porcentaje_triple']}% 3P</span>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.caption("Sin datos de tripleros")
        
        with col2:
            st.markdown(f"**🔴 {equipo_visitante}**")
            tripleros_visit = self.get_top_tripleros(equipo_visitante)
            if tripleros_visit:
                for t in tripleros_visit:
                    color = "#10b981" if t["triples_por_partido"] >= 3 else "#f59e0b"
                    st.markdown(f"""
                    <div style="border-left: 3px solid {color}; padding-left: 10px; margin: 8px 0;">
                        <span style="color: {color}; font-weight: bold;">🎯 {t['nombre']}</span>
                        <br><span style="font-size: 12px;">📊 {t['triples_por_partido']} triples/partido | {t['porcentaje_triple']}% 3P</span>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.caption("Sin datos de tripleros")

radar_triples = RadarTriplesNBA()
