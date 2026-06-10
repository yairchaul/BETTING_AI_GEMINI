# radar_triples_nba.py
import streamlit as st
from scrapers.nba_com_scraper import NBAComScraper

class RadarTriplesNBA:
    def __init__(self):
        self.scraper = NBAComScraper()
        self.players_cache = {}
    
    def get_top_tripleros(self, team_name, limit=3):
        """Obtiene los mejores tripleros"""
        team_abbr = {
            "Lakers": "LAL", "Warriors": "GSW", "Celtics": "BOS", "Bucks": "MIL",
            "Nets": "BKN", "Suns": "PHX", "76ers": "PHI", "Mavericks": "DAL",
            "Nuggets": "DEN", "Heat": "MIA", "Knicks": "NYK", "Clippers": "LAC",
            "Grizzlies": "MEM", "Kings": "SAC", "Pelicans": "NOP", "Magic": "ORL",
            "Pacers": "IND", "Bulls": "CHI", "Hawks": "ATL", "Hornets": "CHA",
            "Cavaliers": "CLE", "Pistons": "DET", "Raptors": "TOR", "Timberwolves": "MIN",
            "Trail Blazers": "POR", "Thunder": "OKC", "Jazz": "UTA", "Spurs": "SAS",
            "Rockets": "HOU", "Wizards": "WAS"
        }
        
        abbr = next((abb for name, abb in team_abbr.items() if name.lower() in team_name.lower()), None)
        if not abbr: return []
        
        if abbr not in self.players_cache:
            players = self.scraper.get_players_stats()
            self.players_cache[abbr] = [p for p in players if p.get('equipo') == abbr]
        
        team_players = self.players_cache[abbr]
        team_players.sort(key=lambda x: x.get('triples', 0), reverse=True)
        return team_players[:limit]
    
    def render(self, local, visitante):
        """Renderiza el radar de triples"""
        st.markdown("### 🎯 RADAR DE TRIPLES (NBA)")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"**🔵 {local}**")
            tripleros = self.get_top_tripleros(local)
            if tripleros:
                for t in tripleros:
                    st.markdown(f"🏀 **{t['nombre']}** — {t['triples']} 3PM ({t['puntos']} PPG)")
            else:
                st.caption("📭 Datos de tripleros no disponibles")
        
        with col2:
            st.markdown(f"**🔴 {visitante}**")
            tripleros = self.get_top_tripleros(visitante)
            if tripleros:
                for t in tripleros:
                    st.markdown(f"🏀 **{t['nombre']}** — {t['triples']} 3PM ({t['puntos']} PPG)")
            else:
                st.caption("📭 Datos de tripleros no disponibles")

radar_triples = RadarTriplesNBA()
