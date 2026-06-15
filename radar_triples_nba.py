# radar_triples_nba.py
"""Radar de Triples NBA — DB local primero, fallback a datos estáticos 2024-25."""
import streamlit as st
from database_manager import db

# --- NUEVO: Integración con API dinámica ---
try:
    from balldontlie_client import balldontlie
    BALLDONTLIE_AVAILABLE = True
except ImportError:
    BALLDONTLIE_AVAILABLE = False


def _cargar_fallback_3pm():
    """Datos estáticos 2024-25 (top tiradores por equipo) si la DB está vacía."""
    try:
        from visualizers.visual_nba_mejorado import VisualNBAMejorado as _V
        return getattr(_V, "_3PM_FALLBACK", {})
    except Exception:
        try:
            from visual_nba_mejorado import VisualNBAMejorado as _V
            return getattr(_V, "_3PM_FALLBACK", {})
        except Exception:
            return {}


@st.cache_data(ttl=900, show_spinner="Buscando stats de triples...") # Cache de 15 min
def _fetch_tripleros_data(team_name: str, limit: int = 3):
    """
    Orquestador de datos de tripleros con cascada de fuentes:
    1. API (balldontlie)
    2. Base de datos local
    3. Fallback estático
    """
    # 1. Intento con API en vivo
    if BALLDONTLIE_AVAILABLE:
        try:
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
            
            if team_id:
                players_data = balldontlie.get_players(team_id=team_id)
                players = players_data.get('data', [])
                tripleros = []
                for player in players:
                    player_id = player.get('id')
                    if player_id:
                        stats = balldontlie.get_player_props(player_id)
                        if stats and stats.get('fg3a', 0) >= 2: # Mínimo 2 intentos de triple
                            tripleros.append({
                                "nombre": f"{player.get('first_name')} {player.get('last_name')}",
                                "triples_por_partido": stats.get('fg3a', 0),
                                "porcentaje_triples": stats.get('fg3_pct', 0) * 100
                            })
                if tripleros:
                    tripleros.sort(key=lambda x: x["triples_por_partido"], reverse=True)
                    return tripleros[:limit], "api"
        except Exception:
            pass # Si la API falla, pasamos a la siguiente fuente

    # 2. Intento con DB local
    try:
        players = db.get_top_player_stat(team_name, "three_pm", limit=limit, deporte="nba")
        if players:
            if not isinstance(players, list):
                players = [players]
            return players, "db"
    except Exception:
        pass

    # 3. Fallback estático
    fb = _cargar_fallback_3pm()
    for key, jugadores in fb.items():
        if key.lower() in team_name.lower() or team_name.lower() in key.lower():
            return jugadores[:limit], "fallback"
            
    return [], "fallback"


class RadarTriplesNBA:
    """Detecta jugadores con alta probabilidad de anotar triples."""

    def get_top_tripleros(self, team_name, limit=3):
        resultado, _ = _fetch_tripleros_data(team_name, limit)
        return resultado

    def _render_columna(self, equipo, color_equipo):
        st.markdown(f"**{color_equipo} {equipo}**")
        tripleros, fuente = _fetch_tripleros_data(equipo)
        if tripleros:
            for t in tripleros:
                triples = t.get("triples_por_partido", 0.0)
                porcentaje = t.get("porcentaje_triples", t.get("porcentaje_triple", 0.0))
                color = "#10b981" if triples >= 3 else "#f59e0b"
                st.markdown(f"""
                <div style="border-left: 3px solid {color}; padding-left: 10px; margin: 8px 0;">
                    <span style="color: {color}; font-weight: bold;">🎯 {t.get('nombre', 'N/A')}</span>
                    <br><span style="font-size: 12px;">📊 {triples} triples/partido | {porcentaje}% 3P</span>
                </div>
                """, unsafe_allow_html=True)
            
            fuente_map = {"api": "🌐 API en vivo", "db": "🗃️ DB Local", "fallback": "📋 Estático"}
            st.caption(f"Fuente: {fuente_map.get(fuente, 'Desconocida')}")
        else:
            st.caption("Sin datos de tripleros.")

    def render(self, equipo_local, equipo_visitante):
        """Renderiza el radar de triples en la UI."""
        st.markdown("### 🏀 RADAR DE TRIPLES")
        col1, col2 = st.columns(2)
        with col1:
            self._render_columna(equipo_local, "🔵")
        with col2:
            self._render_columna(equipo_visitante, "🔴")


radar_triples = RadarTriplesNBA()
