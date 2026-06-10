# import re

with open('cerebro_gemini_pro.py', 'r', encoding='utf-8') as f:
    content = f.read()

# NUEVO SYSTEM PROMPT PROFESIONAL
new_prompt = '''def _build_mlb_json_prompt(self, partido, resultado):
        away = partido.get("visitante", partido.get("away", "TBD"))
        home = partido.get("local", partido.get("home", "TBD"))
        p_away = partido.get("pitcher_v", partido.get("pitchers", {}).get("visitante", {}).get("nombre", "TBD"))
        p_home = partido.get("pitcher_l", partido.get("pitchers", {}).get("local", {}).get("nombre", "TBD"))
        whip_v = partido.get("whip_v", "N/A")
        whip_l = partido.get("whip_l", "N/A")
        k_v = partido.get("k_proy_v", "N/A")
        k_l = partido.get("k_proy_l", "N/A")
        ou = partido.get("odds", {}).get("over_under", partido.get("ou_calculado", "N/A"))
        pick = resultado.get("pick", "N/A")
        conf = resultado.get("confianza", 50)
        venue = partido.get("venue", "TBD")
        
        if p_away in ["TBD", "None", None, ""]: p_away = "Por anunciar"
        if p_home in ["TBD", "None", None, ""]: p_home = "Por anunciar"
        
        return f"""Eres un analista senior de MLB especializado en apuestas deportivas.
Tu tarea es recibir datos estadisticos y devolver un analisis visual en Markdown.

REGLAS DE FORMATO:
1. Usa tablas de Markdown para las metricas principales.
2. Usa bloques de cita (>) para las conclusiones tecnicas.
3. Usa emojis funcionales: 🟢 valor, 🔴 riesgo, 📈 OVER, 📉 UNDER, ⭐ elite, 🏟️ estadio.
4. Si un dato es 0 (como K/9), indica: "Dato insuficiente para proyeccion".
5. NO digas "None vs None" o "falta informacion". Usa los datos proporcionados.

DATOS DEL PARTIDO:
- 🏟️ {away} @ {home} | Estadio: {venue}
- 🥎 Lanzadores: {p_away} vs {p_home}
- 📊 WHIP: {whip_v} / {whip_l}
- ⚡ K Proyectados: {k_v} / {k_l}
- 📈 O/U: {ou}
- 🎯 Pick Heuristico: {pick} (Confianza: {conf}%)

ESTRUCTURA OBLIGATORIA DE RESPUESTA:

## 🏟️ ANALISIS: {away} @ {home}

### 🎯 DETERMINACION DE APUESTA
| Categoria | Seleccion | Detalle |
|-----------|-----------|---------|
| Pick Principal | [ML/HANDICAP/OVER/UNDER/K/HR] | [Nombre equipo/jugador] |
| Confianza | [0-100]% | Stake: [1u-5u] |
| Valor Detectado | [SI/NO] | [Breve explicacion] |

### 🥎 DUELO DE LANZADORES
> **{p_away}**: WHIP {whip_v}. [Analisis breve]
> **{p_home}**: WHIP {whip_l}. [Analisis breve]

### 📊 PROYECCION DE CARRERAS (O/U)
- Linea Casino: {ou}
- Proyeccion Modelo: [TU PROYECCION]
- Veredicto: 📈 OVER / 📉 UNDER / ➡️ NEUTRAL

### 💣 RADAR DE HOME RUNS
| Jugador | Equipo | Prob. HR | Analisis |
|---------|--------|----------|----------|
| [Nombre] | [Eq] | [%] | [Breve] |

### 🎲 VEREDICTO FINAL
> [Conclusion en una frase con la mejor apuesta recomendada]"""'''

# Reemplazar la función vieja
old_func = r'def _build_mlb_json_prompt\(self, partido, resultado\):.*?(?=\n    def |\n    def _|\Z)'
content = re.sub(old_func, new_prompt, content, flags=re.DOTALL)

with open('cerebro_gemini_pro.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ cerebro_gemini_pro.py actualizado con SYSTEM PROMPT PROFESIONAL')
print()
print('📋 NUEVO FORMATO DE RESPUESTA:')
print('   🏟️ Título con equipos')
print('   🎯 Tabla de Determinación de Apuesta')
print('   🥎 Duelo de Lanzadores')
print('   📊 Proyección de Carreras (O/U)')
print('   💣 Radar de Home Runs (tabla)')
print('   🎲 Veredicto Final')
