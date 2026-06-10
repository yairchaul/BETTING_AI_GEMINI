# -*- coding: utf-8 -*-
"""MLB ANALYZER - Over/Under dinámico"""
class MLBAnalyzer:
    def __init__(self):
        pass
    
    def analyze_game(self, game):
        away = game.get('away', 'Visitante')
        home = game.get('home', 'Local')
        away_record = game.get('away_record', '0-0')
        home_record = game.get('home_record', '0-0')
        odds = game.get('odds', {})
        hr_hitters = game.get('hr_hitters', [])
        
        def get_win_pct(record):
            try:
                wins, losses = map(int, record.split('-'))
                total = wins + losses
                return wins / total if total > 0 else 0.5
            except:
                return 0.5
        
        home_wr = get_win_pct(home_record)
        away_wr = get_win_pct(away_record)
        win_prob = home_wr / (home_wr + away_wr) if (home_wr + away_wr) > 0 else 0.5
        
        # Over/Under DINÁMICO
        total_runs = 7.5 + (home_wr + away_wr) * 3
        ou_line = odds.get('total', 8.5)
        
        if total_runs > ou_line:
            over_prob = min(75, 55 + int((total_runs - ou_line) * 8))
            ou_pick = f"OVER {ou_line}"
        else:
            over_prob = min(75, 55 + int((ou_line - total_runs) * 8))
            ou_pick = f"UNDER {ou_line}"
        
        best_hr = hr_hitters[0] if hr_hitters else None
        
        return {
            'resultado': {
                'over_under': f"{ou_pick} ({over_prob}%)",
                'moneyline': home if win_prob > 0.5 else away,
                'hr': {'player': best_hr.get('name', 'N/A'), 'confidence': best_hr.get('hr_prob', 0)} if best_hr else 'N/A'
            },
            'type': 'MONEYLINE',
            'pick': home if win_prob > 0.5 else away,
            'confidence': int(max(win_prob, 1-win_prob) * 100)
        }
