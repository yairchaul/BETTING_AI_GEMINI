# -*- coding: utf-8 -*-
"""
MOTOR MLB PRO V25 — "MEJOR PICK"

Combina TODAS las señales disponibles y decide la mejor apuesta del partido:
  1. Récords y rachas de ambos equipos
  2. Momios (la probabilidad implícita del mercado como confirmación)
  3. Lanzadores: WHIP, K/9, ERA reciente (caché local)
  4. Over/Under: línea + dominancia de pitcheo
  5. Candidatos a Home Run (si se inyecta el predictor)
  6. Jerarquía de decisión V21: ÉLITE / SEGURO / RESCATE / EVITAR

Devuelve SIEMPRE un pick con razones transparentes. Cada señal es opcional:
si falta un dato, el motor degrada con elegancia en vez de fallar.
"""

import re
import os
import json
import logging

logger = logging.getLogger(__name__)

# Mapa nombre completo → abreviatura (el dataset de HR usa abreviaturas)
_TEAM_ABREV = {
    "arizona diamondbacks": "ARI", "atlanta braves": "ATL", "baltimore orioles": "BAL",
    "boston red sox": "BOS", "chicago cubs": "CHC", "chicago white sox": "CHW",
    "cincinnati reds": "CIN", "cleveland guardians": "CLE", "colorado rockies": "COL",
    "detroit tigers": "DET", "houston astros": "HOU", "kansas city royals": "KC",
    "los angeles angels": "LAA", "los angeles dodgers": "LAD", "miami marlins": "MIA",
    "milwaukee brewers": "MIL", "minnesota twins": "MIN", "new york mets": "NYM",
    "new york yankees": "NYY", "athletics": "OAK", "oakland athletics": "OAK",
    "philadelphia phillies": "PHI", "pittsburgh pirates": "PIT", "san diego padres": "SD",
    "san francisco giants": "SF", "seattle mariners": "SEA", "st. louis cardinals": "STL",
    "tampa bay rays": "TB", "texas rangers": "TEX", "toronto blue jays": "TOR",
    "washington nationals": "WSH", "washington nationals ": "WSH",
}

# Bateadores de poder de los 4 equipos que faltan en el dataset (KC, MIA, OAK, WSH)
_HR_EXTRA = {
    "Bobby Witt Jr": {"equipo": "KC", "hr": 7, "ops": 0.86},
    "Salvador Perez": {"equipo": "KC", "hr": 8, "ops": 0.80},
    "Vinnie Pasquantino": {"equipo": "KC", "hr": 6, "ops": 0.78},
    "MJ Melendez": {"equipo": "KC", "hr": 4, "ops": 0.72},
    "Jake Burger": {"equipo": "MIA", "hr": 9, "ops": 0.81},
    "Jesus Sanchez": {"equipo": "MIA", "hr": 5, "ops": 0.75},
    "Josh Bell": {"equipo": "MIA", "hr": 5, "ops": 0.74},
    "Jonah Bride": {"equipo": "MIA", "hr": 3, "ops": 0.70},
    "Brent Rooker": {"equipo": "OAK", "hr": 10, "ops": 0.88},
    "Lawrence Butler": {"equipo": "OAK", "hr": 7, "ops": 0.80},
    "Tyler Soderstrom": {"equipo": "OAK", "hr": 6, "ops": 0.78},
    "JJ Bleday": {"equipo": "OAK", "hr": 5, "ops": 0.74},
    "James Wood": {"equipo": "WSH", "hr": 8, "ops": 0.84},
    "CJ Abrams": {"equipo": "WSH", "hr": 6, "ops": 0.79},
    "Keibert Ruiz": {"equipo": "WSH", "hr": 4, "ops": 0.71},
    "Nathaniel Lowe": {"equipo": "WSH", "hr": 5, "ops": 0.75},
}

# Park factor de HR por estadio (>1 favorece HR, <1 los reduce). Fuente: factores históricos.
_PARK_FACTOR_HR = {
    "Coors Field": 1.18, "Great American Ball Park": 1.16, "Yankee Stadium": 1.15,
    "Citizens Bank Park": 1.12, "Globe Life Field": 1.10, "Camden Yards": 1.10,
    "Oriole Park at Camden Yards": 1.10, "Wrigley Field": 1.06, "Fenway Park": 1.04,
    "Dodger Stadium": 1.03, "Rogers Centre": 1.05, "American Family Field": 1.07,
    "Truist Park": 1.02, "Minute Maid Park": 1.04, "Daikin Park": 1.04,
    "Chase Field": 1.02, "Nationals Park": 1.00, "Busch Stadium": 0.92,
    "Oracle Park": 0.88, "Petco Park": 0.92, "T-Mobile Park": 0.90,
    "loanDepot park": 0.88, "Comerica Park": 0.92, "Kauffman Stadium": 0.95,
    "PNC Park": 0.93, "Tropicana Field": 0.95, "Progressive Field": 0.96,
    "Target Field": 0.98, "Citi Field": 0.95, "Angel Stadium": 0.98,
    "Sutter Health Park": 1.08, "George M. Steinbrenner Field": 1.10,
}


def _park_factor(venue):
    if not venue:
        return 1.0
    v = str(venue).strip()
    if v in _PARK_FACTOR_HR:
        return _PARK_FACTOR_HR[v]
    for k, f in _PARK_FACTOR_HR.items():
        if k.lower() in v.lower() or v.lower() in k.lower():
            return f
    return 1.0


_HR_DATASET_CACHE = None


def _cargar_hr_dataset():
    global _HR_DATASET_CACHE
    if _HR_DATASET_CACHE is not None:
        return _HR_DATASET_CACHE
    for ruta in ("hr_datasets_completos.json", os.path.join("data", "hr_datasets_completos.json")):
        try:
            if os.path.exists(ruta):
                with open(ruta, encoding="utf-8") as f:
                    _HR_DATASET_CACHE = json.load(f).get("bateadores", {})
                    return _HR_DATASET_CACHE
        except Exception:
            pass
    _HR_DATASET_CACHE = {}
    return _HR_DATASET_CACHE


def _abrev(nombre_equipo):
    return _TEAM_ABREV.get((nombre_equipo or "").lower().strip())


def _candidatos_hr_equipo(equipo, pitcher_rival, venue=""):
    """Top candidatos a HR del equipo (dataset + extra), ajustados por estadio."""
    abrev = _abrev(equipo)
    if not abrev:
        return []
    # Combinar dataset principal + bateadores extra de los 4 equipos faltantes
    fuente = dict(_cargar_hr_dataset())
    fuente.update(_HR_EXTRA)
    pf = _park_factor(venue)  # factor de estadio
    cands = []
    for nombre, stats in fuente.items():
        if stats.get("equipo", "").upper() != abrev:
            continue
        hr = stats.get("hr", 0)
        if hr < 1:
            continue
        # Probabilidad CALIBRADA con el backtest real (un HR/juego es raro: ~5-18%).
        # El backtest mostró que los valores antiguos (hasta 52%) estaban inflados ~3x.
        hr_rate = hr / 15.0
        ops = stats.get("ops", 0.7) or 0.7
        prob_base = 4 + hr_rate * 14 + max(0, ops - 0.70) * 15
        prob = round(min(22, prob_base * pf))  # tope realista 22%
        cands.append({
            "jugador": nombre.strip(), "nombre": nombre.strip(), "equipo": equipo,
            "hr_total": hr, "probabilidad": prob, "pitcher_rival": pitcher_rival,
            "ops": stats.get("ops", 0.0), "park_factor": pf,
        })
    cands.sort(key=lambda x: x["probabilidad"], reverse=True)
    return cands

try:
    from .motor_lanzadores import obtener_analisis_lanzadores
except ImportError:
    obtener_analisis_lanzadores = None

try:
    from .mlb_stats_api import obtener_whip_cacheado
except ImportError:
    obtener_whip_cacheado = None

# Abridores probables del día + stats FRESCAS por pitcher (API oficial MLB).
# Es el factor #1 de un juego individual y puede voltear el pick contra el récord.
try:
    from .mlb_pitchers_live import obtener_abridores_hoy as abridores_hoy, abridor_de
except ImportError:
    abridores_hoy = None
    def abridor_de(*_a, **_k):
        return None

LIGA_ERA_REF = 4.20   # media de liga para el composite de calidad de pitcher


# ──────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────

def _parse_record(record_str):
    """'15-14' → (15, 14, 0.517)."""
    try:
        m = re.match(r'(\d+)-(\d+)', str(record_str))
        if m:
            w, l = int(m.group(1)), int(m.group(2))
            total = w + l
            return w, l, (w / total if total else 0.5)
    except Exception:
        pass
    return 0, 0, 0.5


def _parse_streak(streak_str):
    """'W3' → +3 | 'L2' → -2 | '' → 0."""
    try:
        s = str(streak_str).strip().upper()
        m = re.match(r'([WL])(\d+)', s)
        if m:
            n = int(m.group(2))
            return n if m.group(1) == 'W' else -n
    except Exception:
        pass
    return 0


def _prob_implicita(ml):
    """Momio americano → probabilidad implícita (0-1). None si no hay momio."""
    try:
        v = float(str(ml).replace('+', ''))
        if v == 0:
            return None
        if v > 0:
            return 100 / (v + 100)
        return abs(v) / (abs(v) + 100)
    except Exception:
        return None


def _pitcher_nombre(pitchers, lado):
    p = pitchers.get(lado, {})
    if isinstance(p, dict):
        return p.get('nombre', 'TBD') or 'TBD'
    return str(p) if p else 'TBD'


# ──────────────────────────────────────────────────────────────────────────
# MOTOR PRINCIPAL
# ──────────────────────────────────────────────────────────────────────────

def analizar_mlb_pro_v20(partido, game_pk=None, predictor_hr=None):
    """Analiza un partido MLB con todas las señales y devuelve el mejor pick."""
    local = partido.get('local') or partido.get('home', 'Local')
    visitante = partido.get('visitante') or partido.get('away', 'Visitante')
    odds = partido.get('odds', {}) or {}
    pitchers = partido.get('pitchers', {}) or {}
    venue = partido.get('venue', '') or partido.get('estadio', '')

    razones = []
    score = 0.0          # positivo → favorece LOCAL, negativo → VISITANTE

    # ── 1. Récords ──────────────────────────────────────────────────────
    w_l, l_l, pct_l = _parse_record(partido.get('local_record', '0-0'))
    w_v, l_v, pct_v = _parse_record(
        partido.get('visitante_record') or partido.get('visit_record', '0-0'))
    diff_pct = pct_l - pct_v
    score += diff_pct * 18                       # récord pesa menos: el abridor manda
    if abs(diff_pct) >= 0.08:
        mejor = local if diff_pct > 0 else visitante
        razones.append(f"Récord favorece a {mejor} ({pct_l:.0%} vs {pct_v:.0%})")

    # ── 2. Rachas ───────────────────────────────────────────────────────
    st_l = _parse_streak(partido.get('local_streak', ''))
    st_v = _parse_streak(partido.get('visitante_streak', ''))
    score += (st_l - st_v) * 1.2                 # ±6 aprox
    if st_l >= 3:
        razones.append(f"{local} en racha {partido.get('local_streak')}")
    if st_v >= 3:
        razones.append(f"{visitante} en racha {partido.get('visitante_streak')}")

    # ── 3. Mercado (momios) ─────────────────────────────────────────────
    ml = odds.get('moneyline', {}) or {}
    ml_l = ml.get('local') or ml.get('home')
    ml_v = ml.get('visitante') or ml.get('away')
    p_l = _prob_implicita(ml_l)
    p_v = _prob_implicita(ml_v)
    if p_l is not None and p_v is not None:
        diff_mercado = p_l - p_v
        score += diff_mercado * 18               # ±9 típico
        if abs(diff_mercado) >= 0.10:
            fav = local if diff_mercado > 0 else visitante
            razones.append(f"Mercado respalda a {fav} (ML {ml_l if diff_mercado > 0 else ml_v})")

    # ── 4. Abridores — FACTOR #1 de un juego de MLB ─────────────────────
    # Datos FRESCOS del día, por pitcher, desde la API oficial (con shrinkage
    # para que muestras chicas no engañen). El duelo de abridores puede VOLTEAR
    # el pick contra el récord: así se cazan los upsets (buen abridor en equipo
    # de mal récord) que el motor por-récord siempre perdía.
    ap = _pitcher_nombre(pitchers, 'visitante')
    hp = _pitcher_nombre(pitchers, 'local')
    k9_l = k9_v = 7.8
    era_l = era_v = LIGA_ERA_REF
    whip_l = whip_v = None
    cal_l = cal_v = 0.0

    info_l = info_v = None
    if abridores_hoy is not None:
        try:
            mapa_ab = abridores_hoy()
            info_l = abridor_de(local, mapa_ab)
            info_v = abridor_de(visitante, mapa_ab)
        except Exception:
            info_l = info_v = None

    if info_l:
        if info_l.get('nombre') not in ('TBD', '', None):
            hp = info_l['nombre']
        k9_l = info_l.get('k9_adj') or info_l.get('k9') or k9_l
        era_l = info_l.get('era_adj') or info_l.get('era') or era_l
        whip_l = info_l.get('whip_adj') or info_l.get('whip')
        cal_l = info_l.get('calidad', 0.0) or 0.0
    if info_v:
        if info_v.get('nombre') not in ('TBD', '', None):
            ap = info_v['nombre']
        k9_v = info_v.get('k9_adj') or info_v.get('k9') or k9_v
        era_v = info_v.get('era_adj') or info_v.get('era') or era_v
        whip_v = info_v.get('whip_adj') or info_v.get('whip')
        cal_v = info_v.get('calidad', 0.0) or 0.0

    # Fallback: stats por equipo del JSON local (solo si la API no dio abridores)
    datos_k = {}
    if not (info_l or info_v) and obtener_analisis_lanzadores:
        try:
            datos_k = obtener_analisis_lanzadores() or {}
        except Exception:
            datos_k = {}
        if local in datos_k:
            k9_l = datos_k[local].get('k9', k9_l)
            era_l = datos_k[local].get('era', datos_k[local].get('era_reciente', era_l))
            cal_l = (LIGA_ERA_REF - era_l) + (k9_l - 8.2) * 0.35
        if visitante in datos_k:
            k9_v = datos_k[visitante].get('k9', k9_v)
            era_v = datos_k[visitante].get('era', datos_k[visitante].get('era_reciente', era_v))
            cal_v = (LIGA_ERA_REF - era_v) + (k9_v - 8.2) * 0.35

    # Edge de pitcheo (+ = abridor LOCAL mejor). Peso alto para que pueda voltear
    # el pick, pero acotado ±30 para no desbocarse con un outlier.
    pitcher_edge = cal_l - cal_v
    score += max(-30.0, min(30.0, pitcher_edge * 8.0))
    if abs(pitcher_edge) >= 0.6:
        if pitcher_edge > 0:
            mejor_p, era_mejor, era_rival = hp, era_l, era_v
        else:
            mejor_p, era_mejor, era_rival = ap, era_v, era_l
        razones.insert(0, f"Duelo de abridores favorece a {mejor_p} "
                          f"(ERA {era_mejor:.2f} vs {era_rival:.2f})")

    # ── 5. Ventaja de local ─────────────────────────────────────────────
    score += 3.0

    # ── Pick de ganador + jerarquía V21 (consciente del mercado) ─────────
    pick_team = local if score >= 0 else visitante
    confianza = round(min(85, max(35, 50 + abs(score) * 1.4)))

    # ¿Nuestro pick coincide con el favorito del mercado, o lo estamos fadeando?
    pick_es_favorito = None
    if p_l is not None and p_v is not None:
        fav_mercado = local if p_l >= p_v else visitante
        pick_es_favorito = (pick_team == fav_mercado)
    fadeando = (pick_es_favorito is False)   # pick = underdog → valor en el ML

    # Al fadear el mercado somos algo menos categóricos (más incertidumbre) y el
    # valor está en el MONEYLINE (momio +), no en un run line -1.5.
    if fadeando:
        confianza = min(confianza, 79)

    if confianza >= 80:
        decision, tipo, handicap, stake = "🟢 ÉLITE", "MONEYLINE", "", "3u"
    elif confianza >= 65:
        if fadeando:
            decision, tipo, handicap, stake = "🟡 SEGURO", "MONEYLINE", "", "2u"
        else:
            decision, tipo, handicap, stake = "🟡 SEGURO", "HANDICAP", "-1.5", "2u"
    elif confianza >= 55:
        if fadeando:
            decision, tipo, handicap, stake = "🔵 RESCATE", "MONEYLINE", "", "1u"
        else:
            decision, tipo, handicap, stake = "🔵 RESCATE", "HANDICAP", "+1.5", "1u"
    else:
        decision, tipo, handicap, stake = "🔴 EVITAR", "EVITAR", "", "0u"

    if not razones:
        razones.append("Señales parejas — pick por ventaja mínima acumulada")

    # ── 6. Over/Under ───────────────────────────────────────────────────
    ou_linea = odds.get('over_under') or odds.get('overUnder') or 8.5
    try:
        ou_linea = float(ou_linea)
    except Exception:
        ou_linea = 8.5

    # Pitcheo dominante (K/9 alto + ERA baja) empuja al UNDER
    factor_pitcheo = (k9_l + k9_v) / 2 - 7.5 + (4.2 - (era_l + era_v) / 2) * 1.5
    # Total de carreras PROYECTADO: línea ajustada por el factor de pitcheo + estadio
    pf_runs = _park_factor(venue)  # parques de HR también suben carreras
    total_proyectado = round(ou_linea - factor_pitcheo * 0.55 + (pf_runs - 1.0) * 4, 1)
    if factor_pitcheo >= 1.0:
        ou_pick, ou_conf = "UNDER", round(min(70, 52 + factor_pitcheo * 5))
        razones.append(f"Pitcheo dominante (K/9 prom {((k9_l + k9_v) / 2):.1f}) → UNDER")
    elif factor_pitcheo <= -1.0:
        ou_pick, ou_conf = "OVER", round(min(70, 52 + abs(factor_pitcheo) * 5))
        razones.append("Pitcheo vulnerable → OVER")
    else:
        # Caso neutral: usar la proyección, con nudge del sesgo OVER real (backtest)
        try:
            calib = json.load(open(os.path.join("data", "mlb_calibracion.json"), encoding="utf-8"))
            tasa_over = calib.get("ou_tasa_over", 50)
        except Exception:
            tasa_over = 50
        sesgo_over = (tasa_over - 50) * 0.04  # nudge suave hacia el lado más frecuente
        if total_proyectado + sesgo_over > ou_linea:
            ou_pick, ou_conf = "OVER", round(min(62, 50 + abs(total_proyectado - ou_linea) * 6 + (tasa_over - 50) * 0.3))
        else:
            ou_pick, ou_conf = "UNDER", round(min(62, 50 + abs(total_proyectado - ou_linea) * 6))

    # ── 7. Candidatos HR ────────────────────────────────────────────────
    # Primero intentar el predictor con lineup oficial (si ya se publicó);
    # si no devuelve nada (lineup no posteado), usar el dataset por equipo.
    hr_candidates = []
    if predictor_hr and game_pk:
        try:
            if hasattr(predictor_hr, 'analizar_equipo_completo'):
                bats = (predictor_hr.analizar_equipo_completo(visitante, game_pk=game_pk) +
                        predictor_hr.analizar_equipo_completo(local, game_pk=game_pk))
                for b in bats:
                    b.setdefault('jugador', b.get('nombre', '?'))
                    if not b.get('pitcher_rival'):
                        eq = b.get('equipo', '')
                        b['pitcher_rival'] = ap if (local and local.lower() in eq.lower()) else hp
                hr_candidates = sorted(bats, key=lambda x: x.get('probabilidad', 0), reverse=True)[:6]
        except Exception as e:
            logger.debug(f"Predictor HR sin lineup: {e}")

    # Fallback robusto (lineup no publicado): mejores bateadores del dataset
    # Ajustados por el estadio (park factor de HR)
    if not hr_candidates:
        hr_candidates = (_candidatos_hr_equipo(local, ap, venue) + _candidatos_hr_equipo(visitante, hp, venue))
        hr_candidates.sort(key=lambda x: x.get('probabilidad', 0), reverse=True)
        hr_candidates = hr_candidates[:6]

    # ── Total de bases por bateador (Over 1.5) ──────────────────────────
    # Señal principal: poder del bateador (HR en 15 días). Un slugger supera 1.5
    # bases con frecuencia. OPS suma si está disponible.
    tb_picks = []
    for b in hr_candidates[:6]:
        hr = b.get('hr_total', 0)
        ops = b.get('ops', 0) or 0
        # Base 50%, +3% por cada HR reciente, +OPS bonus si existe
        prob_tb = 50 + hr * 3 + (max(0, ops - 0.75) * 60 if ops else 0)
        prob_tb = round(max(45, min(72, prob_tb)))
        pick_tb = "OVER" if prob_tb >= 50 else "UNDER"
        tb_picks.append({
            'jugador': b.get('jugador', b.get('nombre', '?')),
            'equipo': b.get('equipo', ''),
            'linea': 1.5, 'prediccion': pick_tb,
            'pick': f"{pick_tb} 1.5 bases", 'confianza': prob_tb,
        })

    # ── 8. Proyección de Strikeouts (Over/Under por lanzador) ───────────
    # K proyectados = (K/9 ÷ 9) × entradas esperadas (≈5.5). Línea = round(proy)−0.5
    k_picks = []
    for team, pitcher, k9_team in ((local, hp, k9_l), (visitante, ap, k9_v)):
        if pitcher in ('TBD', 'None', '', None):
            continue
        k9 = datos_k.get(team, {}).get('k9', k9_team) or k9_team
        innings = 5.5
        k_proy = round((k9 / 9.0) * innings, 1)
        linea = max(2.5, round(k_proy) - 0.5)
        pred = "OVER" if k_proy > linea else "UNDER"
        # Confianza por margen respecto a la línea
        margen = abs(k_proy - linea)
        conf_k = int(min(70, 52 + margen * 12))
        k_picks.append({
            'pitcher': pitcher, 'k9': round(k9, 1), 'proyeccion': k_proy,
            'linea': linea, 'prediccion': pred, 'pick': f"{pred} {linea} K",
            'confianza': conf_k,
        })

    return {
        # Lo que el visual muestra
        'recomendacion': pick_team,
        'pick': pick_team,
        'confianza': confianza,
        'tipo_apuesta': tipo,
        'handicap': handicap,
        'decision': decision,
        'stake': stake,
        'ou_pick': ou_pick,
        'ou_linea_ajustada': ou_linea,
        'ou_confianza': ou_conf,
        'total_proyectado': total_proyectado,
        'diferencia_record': round(diff_pct * 100, 1),
        # Transparencia y extras
        'razones': razones[:5],
        'hr_candidates': hr_candidates,
        'k_picks': k_picks,
        'tb_picks': tb_picks,
        'run_line': {'pick': pick_team,
                     'linea': handicap or ('+1.5' if fadeando else '-1.5'),
                     'confianza': max(50, confianza - 8)},
        'score_raw': round(score, 2),
        'pitchers': {'local': hp, 'visitante': ap},
    }
