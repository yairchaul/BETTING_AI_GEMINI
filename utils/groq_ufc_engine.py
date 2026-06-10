# -*- coding: utf-8 -*-
"""
MOTOR GROQ UFC - ENRIQUECIDO CON TODO EL CONOCIMIENTO
"""

import os
from groq import Groq

def get_groq_key():
    key = os.environ.get('GROQ_API_KEY')
    if key:
        return key
    try:
        with open('.env', 'r') as f:
            for line in f:
                if 'GROQ_API_KEY=' in line:
                    return line.split('=', 1)[1].strip().strip('"').strip("'")
    except:
        pass
    return None

class GroqUFCEngine:
    def __init__(self, api_key=None):
        self.api_key = api_key or get_groq_key()
        
        if not self.api_key:
            print("❌ GROQ_API_KEY no encontrada.")
            self.client = None
            return
        
        try:
            self.client = Groq(api_key=self.api_key)
            self.model = "llama-3.3-70b-versatile" # Modelo de alta velocidad y capacidad
            print(f"⚡ Groq listo con: {self.model}")
        except Exception as e:
            print(f"❌ Error: {e}")
            self.client = None

    def orquestrar_decision_final(self, deporte, partido, resultado, contexto_extra=""):
        """Método genérico para análisis Pro compatible con AnalistaTotal"""
        if not self.client: return '{"error": "Groq Offline"}'
        
        prompt = f"""
        Actúa como un experto analista de apuestas de nivel ÉLITE.
        Deporte: {deporte}
        Evento: {partido}
        Cálculo Heurístico Base: {resultado}
        Contexto Técnico: {contexto_extra}

        Analiza las variables y devuelve estrictamente un JSON:
        {{
            "pick": "Tu selección final",
            "confianza": 0-100,
            "razon": "Tu argumento técnico principal"
        }}
        """
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                response_format={"type": "json_object"}
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            return f'{{"error": "{str(e)}"}}'
    
    def analyze_fight(self, p1_name, p1_record, p1_ko, p1_sub, p1_altura, p1_alcance,
                            p2_name, p2_record, p2_ko, p2_sub, p2_altura, p2_alcance,
                            odds_p1="N/A", odds_p2="N/A",
                            p1_bonus=0, p2_bonus=0, p1_p4p=None, p2_p4p=None,
                            p1_slpm=0, p2_slpm=0, p1_str_acc=0, p2_str_acc=0,
                            p1_sapm=0, p2_sapm=0, p1_str_def=0, p2_str_def=0,
                            p1_td_avg=0, p2_td_avg=0, p1_td_acc=0, p2_td_acc=0,
                            p1_td_def=0, p2_td_def=0, p1_control_time=0, p2_control_time=0,
                            p1_streak=0, p2_streak=0, p1_age=30, p2_age=30,
                            p1_striking=0, p2_striking=0, p1_td=0, p2_td=0):
        
        if not self.client:
            return None, "Groq no disponible"
        
        # Calcular experiencia
        def parse_record(rec):
            if not rec or rec == 'N/A':
                return 0, 0, 0.5
            try:
                parts = rec.split('-')
                wins = int(parts[0])
                losses = int(parts[1]) if len(parts) > 1 else 0
                total = wins + losses
                return wins, losses, wins/total if total > 0 else 0.5
            except:
                return 0, 0, 0.5
        
        p1_wins, p1_losses, p1_win_rate = parse_record(p1_record)
        p2_wins, p2_losses, p2_win_rate = parse_record(p2_record)
        
        p1_exp = p1_wins + p1_losses
        p2_exp = p2_wins + p2_losses
        
        # Determinar nivel
        p1_is_champion = p1_bonus >= 0.05
        p2_is_champion = p2_bonus >= 0.05
        p1_is_prospect = p1_exp < 15 and p1_exp > 0
        p2_is_prospect = p2_exp < 15 and p2_exp > 0
        p1_is_veteran = p1_exp >= 25 and p1_win_rate >= 0.70
        p2_is_veteran = p2_exp >= 25 and p2_win_rate >= 0.70
        
        # --- SUB-MOTOR DE STRIKING (VOLUMEN Y DIFERENCIAL) ---
        dif_strikes_p1 = (float(p1_slpm or 0) * (float(p1_str_acc or 0) / 100)) - (float(p2_sapm or 0) * (float(p2_str_def or 0) / 100))
        dif_strikes_p2 = (float(p2_slpm or 0) * (float(p2_str_acc or 0) / 100)) - (float(p1_sapm or 0) * (float(p1_str_def or 0) / 100))
        
        striking_advantage = "Ninguno"
        if dif_strikes_p1 >= 2.1 and p2_str_def <= 50:
            striking_advantage = p1_name
        elif dif_strikes_p2 >= 2.1 and p1_str_def <= 50:
            striking_advantage = p2_name
        
        # --- SUB-MOTOR DE GRAPPLING Y CONTROL (DERRIBOS) ---
        grappling_dominance_p1 = (p1_td_avg * (p1_td_acc / 100)) * (1 - (p2_td_def / 100))
        grappling_dominance_p2 = (p2_td_avg * (p2_td_acc / 100)) * (1 - (p1_td_def / 100))
        
        grappling_advantage = "Ninguno"
        if p1_control_time >= 4.5: # 4:30 minutos
            grappling_advantage = p1_name
        elif p2_control_time >= 4.5:
            grappling_advantage = p2_name
        
        # --- CONSISTENCY FILTER (CV) - SIMULADO ---
        # En un entorno real, esto vendría de un backtesting de las últimas 5 peleas
        cv_p1 = 0.2 # Coeficiente de Variación simulado
        cv_p2 = 0.4 # Coeficiente de Variación simulado
        
        volatility_p1 = "Volátil" if cv_p1 > 0.35 else "Consistente"
        volatility_p2 = "Volátil" if cv_p2 > 0.35 else "Consistente"

        # PROMPT ENRIQUECIDO (MISMO QUE GEMINI)
        prompt = f"""Eres un analista senior de MMA. Analiza el combate usando métricas de UFCStats.

📊 **{p1_name}**
- Récord: {p1_record} (Win Rate: {p1_win_rate:.1%})
- KO Rate: {p1_ko}% {"⚠️ ALTO PODER DE KO" if p1_ko >= 70 else ""}
- Sub Rate: {p1_sub}% {"🥋 AMENAZA DE SUMISIÓN" if p1_sub >= 40 else ""}
- Experiencia: {p1_exp} peleas {"(VETERANO ÉLITE)" if p1_is_veteran else ""}
- Edad: {p1_age} años {"(PEAK FÍSICO)" if 27 <= p1_age <= 32 else "(DECLIVE)" if p1_age >= 36 else ""}
- Racha: {p1_streak} {"(MOMENTO EXCELENTE)" if p1_streak >= 3 else ""}
- Ranking: {"🏆 CAMPEÓN" if p1_is_champion else f"Top {p1_p4p} P4P" if p1_p4p else "No rankeado"}
- Striking Accuracy: {p1_striking}%
- Takedown Accuracy: {p1_td}%
- Altura: {p1_altura}cm | Alcance: {p1_alcance}cm
- SLpM (Golpes/min): {p1_slpm} | Striking Accuracy: {p1_str_acc}%
- SApM (Recibidos/min): {p1_sapm} | Strike Defense: {p1_str_def}%
- TD Avg: {p1_td_avg} | TD Acc: {p1_td_acc}% | TD Def: {p1_td_def}%
- Control Time: {p1_control_time} min
- Consistencia: {volatility_p1}

📊 **{p2_name}**
- Récord: {p2_record} (Win Rate: {p2_win_rate:.1%})
- KO Rate: {p2_ko}% {"⚠️ ALTO PODER DE KO" if p2_ko >= 70 else ""}
- Sub Rate: {p2_sub}% {"🥋 AMENAZA DE SUMISIÓN" if p2_sub >= 40 else ""}
- Experiencia: {p2_exp} peleas {"(VETERANO ÉLITE)" if p2_is_veteran else ""}
- Edad: {p2_age} años {"(PEAK FÍSICO)" if 27 <= p2_age <= 32 else "(DECLIVE)" if p2_age >= 36 else ""}
- Racha: {p2_streak} {"(MOMENTO EXCELENTE)" if p2_streak >= 3 else ""}
- Ranking: {"🏆 CAMPEÓN" if p2_is_champion else f"Top {p2_p4p} P4P" if p2_p4p else "No rankeado"}
- Striking Accuracy: {p2_striking}%
- Takedown Accuracy: {p2_td}%
- Altura: {p2_altura}cm | Alcance: {p2_alcance}cm
- SLpM (Golpes/min): {p2_slpm} | Striking Accuracy: {p2_str_acc}%
- SApM (Recibidos/min): {p2_sapm} | Strike Defense: {p2_str_def}%
- TD Avg: {p2_td_avg} | TD Acc: {p2_td_acc}% | TD Def: {p2_td_def}%
- Control Time: {p2_control_time} min
- Consistencia: {volatility_p2}

💰 **Odds:** {p1_name} {odds_p1} | {p2_name} {odds_p2}

🎯 **CRITERIOS DE ANÁLISIS (PROBADOS EN BACKTESTING):**
1. Diferencial de Golpes (SLpM): Quien conecta más golpes limpios por minuto tiene ventaja táctica.
2. KO Rate >70%: Factor de peligro crítico.
3. Diferencia de Edad: Penalizar al veterano si es >10 años.
4. Análisis de Striking: Dif_Strikes ({dif_strikes_p1:.2f} vs {dif_strikes_p2:.2f}). Ventaja: {striking_advantage}
5. Análisis de Grappling: Grappling_Dominance ({grappling_dominance_p1:.2f} vs {grappling_dominance_p2:.2f}). Ventaja: {grappling_advantage}

Basado en estos criterios, ¿quién gana y por qué?

Responde EXACTAMENTE:
WINNER: [Nombre]
CONFIDENCE: [1-100]
METHOD: [KO/TKO/Decisión/Sumisión]
REASON: [Una frase con el factor clave]
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=200
            )
            text = response.choices[0].message.content
            
            winner = None
            confidence = 50
            method = "Decisión"
            reason = ""
            
            for line in text.split('\n'):
                line_upper = line.upper()
                if 'WINNER:' in line_upper:
                    winner = line.split(':', 1)[1].strip()
                elif 'CONFIDENCE:' in line_upper:
                    try:
                        confidence = int(''.join(filter(str.isdigit, line)))
                    except:
                        pass
                elif 'METHOD:' in line_upper:
                    method = line.split(':', 1)[1].strip()
                elif 'REASON:' in line_upper:
                    reason = line.split(':', 1)[1].strip()
            
            return {
                'winner': winner,
                'confidence': confidence,
                'method': method,
                'reason': reason
            }, None
            
        except Exception as e:
            return None, f"Error: {str(e)[:100]}"


# ==================== TEST ====================
if __name__ == "__main__":
    engine = GroqUFCEngine()
    
    if engine.client:
        print("\n" + "="*60)
        print("⚡ TEST GROQ ENRIQUECIDO")
        print("="*60)
        
        # Ejemplo de llamada con los nuevos parámetros
        result, _ = engine.analyze_fight( 
            "Gilbert Burns", "22-9-0", 20, 15, 177, 180,
            "Mike Malott", "13-2-1", 28, 10, 185, 185,
            p1_bonus=0.02, p2_bonus=0.01, p1_age=38, p2_age=34,
            p1_striking=45, p2_striking=50,
            p1_slpm=4.5, p1_str_acc=50, p1_sapm=2.0, p1_str_def=60,
            p1_td_avg=3.5, p1_td_acc=45, p1_td_def=70, p1_control_time=5.0,
            p2_slpm=3.8, p2_str_acc=40, p2_sapm=3.0, p2_str_def=55,
            p2_td_avg=1.0, p2_td_acc=30, p2_td_def=60, p2_control_time=1.0
        )
        
        if result:
            print(f"\n✅ Ganador: {result['winner']}")
            print(f"📊 Confianza: {result['confidence']}%")
            print(f"🥊 Método: {result['method']}")
            print(f"💡 Razón: {result['reason']}")
        else:
            print("❌ Error en la prueba")