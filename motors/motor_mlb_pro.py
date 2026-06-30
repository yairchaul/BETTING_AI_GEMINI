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
import math
import logging

logger = logging.getLogger(__name__)

from .hr_poisson import prob_hr as prob_hr_poisson

try:
    from .mlb_runs_model import predecir as predecir_runs_model
except ImportError:
    predecir_runs_model = None

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


_LIGA_HR9 = 1.20   # HR/9 permitidos, media de liga (para el factor bateador-vs-pitcher)


def _candidatos_hr_equipo(equipo, pitcher_rival, venue="", pitcher_hr9=None, rival_team=""):
    """Top candidatos a HR del equipo. Modelo BATEADOR vs PITCHER: la prob del
    bateador (Poisson sobre su HR/juego + OPS + estadio) se AJUSTA por la
    vulnerabilidad del abridor rival (HR/9 que permite)."""
    abrev = _abrev(equipo)
    if not abrev:
        return []
    fuente = dict(_cargar_hr_dataset())
    fuente.update(_HR_EXTRA)
    pf = _park_factor(venue)  # factor de estadio (el núcleo Poisson aplica el resto)
    # Si no hay abridor rival confirmado, mostrar el EQUIPO rival (no "TBD")
    rival_disp = pitcher_rival
    if not pitcher_rival or str(pitcher_rival) in ("TBD", "", "N/A", "None"):
        rival_disp = f"abridor de {rival_team}" if rival_team else "abridor rival"
    cands = []
    for nombre, stats in fuente.items():
        if stats.get("equipo", "").upper() != abrev:
            continue
        hr = stats.get("hr", 0)
        if hr < 1:
            continue
        # Probabilidad calibrada por el núcleo Poisson (shrinkage + factores acotados)
        hpg = stats.get("hr_por_juego")
        ops = stats.get("ops", 0.7) or 0.7
        prob = prob_hr_poisson(
            hr_por_juego=hpg, hr_total=hr,
            pitcher_hr9=pitcher_hr9, park_factor=pf,
            mano_pitcher="R", ops=ops,
        )
        cands.append({
            "jugador": nombre.strip(), "nombre": nombre.strip(), "equipo": equipo,
            "hr_total": hr, "probabilidad": prob, "pitcher_rival": rival_disp,
            "pitcher_hr9": round(pitcher_hr9, 2) if pitcher_hr9 else None,
            "ops": stats.get("ops", 0.0), "park_factor": pf,
            "en_lineup": False,
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
# MEJOR APUESTA — elige el mercado óptimo ponderado por rendimiento histórico
# ──────────────────────────────────────────────────────────────────────────

# Peso base por mercado — JERARQUÍA calibrada con backtest REAL 2026:
#   HANDICAP (runline +1.5 al no favorito) ≈ 58-63% → el más fiable, va primero
#   MONEYLINE (favorito) ≈ 56% → sólido
#   HOME_RUN ≈ 22% pero paga mucho → solo "spice" de parlay, no ancla
#   TOTAL (O/U) ≈ 41% · PONCHES (K a línea de casa) ≈ 40% → flojos
#   TOTAL_BASES ≈ 21% → el peor, casi nunca debe ser el pick principal
_PESO_MERCADO = {"HANDICAP": 1.10, "MONEYLINE": 1.00, "HOME_RUN": 0.85,
                 "TOTAL": 0.80, "PONCHES": 0.75, "TOTAL_BASES": 0.45}

# Buffer de la casa de apuestas para STRIKEOUTS (K): la casa suele fijar la línea
# ~1 K por encima de la línea analítica del programa (ej. programa OVER 4.5 →
# casa OVER 5.5). Calculamos la probabilidad REAL del OVER en la línea de la
# casa con Poisson; solo es "apostable" si supera el umbral. Configurable.
K_BUFFER_CASA = 1.0


def _poisson_over(lam, linea):
    """P(K > linea) con K ~ Poisson(lam). 'linea' es x.5 (no entero)."""
    if lam <= 0:
        return 0.0
    k_min = int(math.floor(linea)) + 1          # primer entero estrictamente > línea
    cdf = sum(math.exp(-lam) * lam ** i / math.factorial(i) for i in range(k_min))
    return max(0.0, min(1.0, 1.0 - cdf))


def _runline_pick(fav_team, local, visitante, confianza, p_pick, gap_pct=0.0, modelo_rl=None):
    """Hándicap (runline).

    Si hay probabilidades del MODELO DE CARRERAS (modelo_rl, la matriz Poisson),
    analiza AMBOS lados — favorito +1.5/+2.5 (asegurar), no-favorito +1.5/+2.5, y
    favorito -1.5 (paga más) — y devuelve el de MAYOR probabilidad con valor real
    como pick, más las alternativas. Así puede dar el hándicap al equipo correcto
    (p.ej. favorito +1.5 cuando domina) en vez de siempre al perdedor.

    Sin modelo, cae a la heurística backtesteada (perdedor +1.5/+2.5)."""
    perdedor = visitante if fav_team == local else local
    es_visitante_dog = (perdedor == visitante)
    lado_fav = "local" if fav_team == local else "visitante"
    lado_dog = "visitante" if fav_team == local else "local"

    # ── Decisión DATA-DRIVEN con el modelo de carreras (ambos lados) ──────────
    if modelo_rl:
        def _p(clave):
            v = modelo_rl.get(clave)
            return float(v) if v is not None else None
        crudos = [
            (f"{fav_team} +1.5", _p(f"{lado_fav}_+1.5"), "favorito pierde por ≤1 o gana — el más seguro"),
            (f"{fav_team} +2.5", _p(f"{lado_fav}_+2.5"), "favorito con colchón de 2 carreras"),
            (f"{perdedor} +1.5", _p(f"{lado_dog}_+1.5"), "no favorito pierde por ≤1 o gana"),
            (f"{perdedor} +2.5", _p(f"{lado_dog}_+2.5"), "no favorito con colchón de 2"),
            (f"{fav_team} -1.5", _p(f"{lado_fav}_-1.5"), "favorito gana por 2+ (paga más)"),
        ]
        cands = sorted([(e, pr, n) for e, pr, n in crudos if pr is not None],
                       key=lambda c: c[1], reverse=True)
        if cands:
            # El más probable CON valor (≤93%, que pague algo); si todos son
            # casi seguros, toma igual el más probable (modo "asegurar").
            pick_e, pick_pr, pick_n = next((c for c in cands if c[1] <= 93), cands[0])
            return {"pick": pick_e, "linea": pick_e.split()[-1], "confianza": round(pick_pr),
                    "nota": f"modelo de carreras: {pick_n} (~{pick_pr:.0f}%)",
                    "alternativas": [{"pick": e, "prob": round(pr)} for e, pr, _ in cands[:4]]}

    # ── Hándicap por NIVEL DE CONFIANZA (estrategia del usuario) ────────────
    # Cobertura real (backtest MLB 2026, 259 juegos): -1.5 ~47% · +1.5 ~55-59%
    # (visitante 66%) · +2.5 ~69%. El -1.5 paga momio + (favorito por 2+), por eso
    # vale cuando ESPERAS paliza aunque cubra ~47%.
    #   • Confianza ALTA en el favorito  → favorito -1.5 (paga más, solo en paliza)
    #   • DUDA (confianza baja/parejo)    → perdedor +2.5 (colchón de 2, el más seguro)
    #   • En medio                        → perdedor +1.5 (preferente al visitante)
    if confianza >= 72 and (p_pick or 0) >= 0.66:
        return {"pick": f"{fav_team} -1.5", "linea": "-1.5", "confianza": 47,
                "nota": f"{fav_team} por 2+: alto pago, úsalo solo si esperas paliza (cubre ~47% histórico)"}
    if confianza < 56:
        return {"pick": f"{perdedor} +2.5", "linea": "+2.5", "confianza": 69,
                "nota": f"duda/parejo: {perdedor} +2.5 da colchón de 2 carreras, el más seguro (~69%)"}
    conf = 63 if es_visitante_dog else 58
    nota_gap = ""
    if gap_pct >= 0.20:
        conf -= 8
        nota_gap = " (brecha grande: riesgo de paliza)"
    elif gap_pct >= 0.12:
        conf -= 4
    base = ("visitante +1.5: cubre ~66% (pierde por ≤1 o gana)" if es_visitante_dog
            else "no favorito +1.5: cubre ~58%")
    return {"pick": f"{perdedor} +1.5", "linea": "+1.5", "confianza": max(48, conf),
            "nota": base + nota_gap}


def _factor_mercado(mercado):
    """Peso base × rendimiento histórico real del mercado (pick_memory). Así el
    motor le da MÁS peso a los mercados que más se aciertan (y menos a los que fallan)."""
    base = _PESO_MERCADO.get(mercado, 0.9)
    try:
        from .pick_memory import pick_memory
        f = pick_memory.factor_confianza("MLB", mercado)
        return base * (f if f else 1.0)
    except Exception:
        return base


def _mejor_apuesta_mlb(res, factor_fn=_factor_mercado):
    """Compara TODOS los mercados del juego (ML, O/U, run line, ponches, HR,
    bases) y elige el de mayor confianza AJUSTADA por el histórico."""
    cands = []
    if res.get("pick"):
        cands.append({"mercado": "MONEYLINE", "pick": f"Gana {res['pick']}",
                      "confianza": res.get("confianza", 0)})
    if res.get("ou_pick"):
        cands.append({"mercado": "TOTAL", "pick": f"{res['ou_pick']} {res.get('ou_linea_ajustada','')}",
                      "confianza": res.get("ou_confianza", 0)})
    rl = res.get("run_line", {}) or {}
    if rl.get("pick"):
        cands.append({"mercado": "HANDICAP", "pick": rl["pick"],
                      "confianza": rl.get("confianza", 0)})
    for kp in (res.get("k_picks") or [])[:2]:
        cands.append({"mercado": "PONCHES", "pick": f"{kp.get('pitcher','')} {kp.get('pick','')}",
                      "confianza": kp.get("confianza", 0)})
    for hr in (res.get("hr_candidates") or [])[:1]:
        cands.append({"mercado": "HOME_RUN",
                      "pick": f"{hr.get('jugador','')} HR vs {hr.get('pitcher_rival','')}",
                      "confianza": hr.get("probabilidad", 0)})
    for tb in (res.get("tb_picks") or [])[:1]:
        if tb.get("prediccion") == "OVER":
            cands.append({"mercado": "TOTAL_BASES", "pick": f"{tb.get('jugador','')} {tb.get('pick','')}",
                          "confianza": tb.get("confianza", 0)})
    if not cands:
        return None
    for c in cands:
        f = factor_fn(c["mercado"]) if factor_fn else 1.0
        c["confianza_ajustada"] = round(c["confianza"] * f, 1)
        c["factor"] = round(f, 2)
    mejor = max(cands, key=lambda c: c["confianza_ajustada"])
    mejor["razon"] = (f"Mejor de {len(cands)} mercados — conf {mejor['confianza']:.0f}% "
                      f"× histórico {mejor['factor']}")
    mejor["alternativas"] = sorted(cands, key=lambda c: c["confianza_ajustada"], reverse=True)[:4]
    return mejor


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
    hr9_l = hr9_v = None   # HR/9 permitidos por cada abridor (para bateador-vs-pitcher)

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
        hr9_l = info_l.get('hr9_adj') or info_l.get('hr9')
    if info_v:
        if info_v.get('nombre') not in ('TBD', '', None):
            ap = info_v['nombre']
        k9_v = info_v.get('k9_adj') or info_v.get('k9') or k9_v
        era_v = info_v.get('era_adj') or info_v.get('era') or era_v
        whip_v = info_v.get('whip_adj') or info_v.get('whip')
        cal_v = info_v.get('calidad', 0.0) or 0.0
        hr9_v = info_v.get('hr9_adj') or info_v.get('hr9')

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

    # --- MEJORA: Integrar modelo de carreras (Dixon-Coles) para precisión ---
    prob_dc_local = None
    res_dc = None   # se reutiliza abajo para el run line (def antes del try)
    if predecir_runs_model:
        try:
            res_dc = predecir_runs_model(local, visitante)
            if res_dc and res_dc.get("disponible"):
                prob_dc_local = res_dc.get("moneyline", {}).get("local")
                if prob_dc_local is not None:
                    razones.append(f"Modelo Carreras: {local} {prob_dc_local:.1f}%")
        except Exception as e:
            logger.debug(f"mlb_runs_model falló: {e}")

    # --- Fusión de probabilidades: MERCADO + Modelo de Carreras + Heurístico ---
    # El MERCADO (momio de-vigueado) es el mejor predictor individual (incorpora
    # pitcheo/lesiones/forma), así que manda. Gemini lo había eliminado dejando
    # solo score+runs_model, lo que degradaba el ML (que iba 57.9% real).
    prob_heur_local = max(10, min(90, 50 + score / 2.0))

    prob_mkt_local = None
    if p_l is not None and p_v is not None and (p_l + p_v) > 0:
        prob_mkt_local = p_l / (p_l + p_v) * 100   # de-vig a 2 vías

    componentes = []                      # (probabilidad_local, peso)
    if prob_mkt_local is not None:
        componentes.append((prob_mkt_local, 0.50))
    if prob_dc_local is not None:
        componentes.append((prob_dc_local, 0.30))
    componentes.append((prob_heur_local, 0.20 if componentes else 1.0))
    _tot_w = sum(w for _, w in componentes)
    final_prob_local = sum(p * w for p, w in componentes) / _tot_w

    pick_team = local if final_prob_local >= 50 else visitante
    confianza = round(min(88, max(35, max(final_prob_local, 100 - final_prob_local))))
    p_pick = final_prob_local / 100.0 if pick_team == local else (100 - final_prob_local) / 100.0

    # Alerta cuando el modelo contradice al mejor récord (el upset que conviene seguir)
    alerta_upset = ""
    fav_record = local if diff_pct >= 0 else visitante
    if pick_team != fav_record and abs(diff_pct) >= 0.05:
        alerta_upset = (f"Upset: el modelo favorece a {pick_team} pese al mejor récord de "
                        f"{fav_record} — suele dar la vuelta")

    if confianza >= 70:
        decision, tipo, handicap, stake = "🟢 ÉLITE", "MONEYLINE", "", "3u"
    elif confianza >= 60:
        decision, tipo, handicap, stake = "🟡 SEGURO", "MONEYLINE", "", "2u"
    elif confianza >= 53:
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

    # Pitcheo dominante (K/9 alto + ERA baja) empuja al UNDER. Para TOTALES, el
    # abridor del día es la señal #1; un modelo de carreras a nivel EQUIPO no
    # mejoró el O/U en backtest (47% vs 50.6% baseline: los totales MLB son muy
    # eficientes y el modelo de equipo ignora al abridor). Por eso O/U usa pitcheo.
    factor_pitcheo = (k9_l + k9_v) / 2 - 7.5 + (4.2 - (era_l + era_v) / 2) * 1.5
    pf_runs = _park_factor(venue)  # parques de HR también suben carreras
    total_proyectado = max(5.0, round(ou_linea - factor_pitcheo * 0.55 + (pf_runs - 1.0) * 4, 1))
    # Probabilidad REAL del over con Poisson sobre el total proyectado.
    p_over_tot = _poisson_over(total_proyectado, ou_linea)
    p_under_tot = 1.0 - p_over_tot
    if p_over_tot >= p_under_tot:
        ou_pick, ou_conf = "OVER", int(min(75, round(p_over_tot * 100)))
    else:
        ou_pick, ou_conf = "UNDER", int(min(75, round(p_under_tot * 100)))
    razones.append(f"O/U Poisson (pitcheo+estadio): proy {total_proyectado} vs línea {ou_linea} → {ou_pick} {ou_conf}%")

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
        # Para bateadores LOCAL el rival es el abridor VISITANTE (ap, hr9_v) y viceversa
        hr_candidates = (_candidatos_hr_equipo(local, ap, venue, pitcher_hr9=hr9_v, rival_team=visitante) +
                         _candidatos_hr_equipo(visitante, hp, venue, pitcher_hr9=hr9_l, rival_team=local))
        hr_candidates.sort(key=lambda x: x.get('probabilidad', 0), reverse=True)
        hr_candidates = hr_candidates[:6]

    # ── Marcar en_lineup con la alineación del día (OFICIAL o PROYECTADA) ──
    # Si la oficial no se publicó, se usa la última confirmada del equipo como
    # proyección → evita el "alineación por confirmar" y permite filtrar HRs.
    if game_pk:
        try:
            from .lineup_provider import obtener_lineup, en_alineacion
            lu_local = obtener_lineup(game_pk, local)
            lu_visit = obtener_lineup(game_pk, visitante)
            for b in hr_candidates:
                eq = str(b.get("equipo", "")).lower()
                lu = lu_local if (local and local.lower() in eq) else lu_visit
                en = en_alineacion(b.get("jugador", b.get("nombre", "")), lu)
                if en is not None:
                    b["en_lineup"] = en
                    b["lineup_proyectada"] = lu.get("proyectada", False)
                    b["lineup_fuente"] = lu.get("fuente", "")
        except Exception as _le:
            logger.debug(f"lineup_provider: {_le}")

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
        # Línea analítica del programa (conservadora) y línea REALISTA de la casa
        # (~1 K más arriba = la que SÍ se puede apostar).
        linea = max(2.5, round(k_proy) - 0.5)
        linea_casa = round(linea + K_BUFFER_CASA, 1)
        # Probabilidad REAL en la línea de la casa (Poisson), no margen blando.
        p_over = _poisson_over(k_proy, linea_casa)
        p_under = 1.0 - p_over
        if p_over >= 0.55:
            pred, conf_p, apostable = "OVER", p_over, True
        elif p_under >= 0.58:           # UNDER exige más margen (riesgo de blow-up)
            pred, conf_p, apostable = "UNDER", p_under, True
        else:
            pred, conf_p, apostable = "OVER", p_over, False   # sin edge real en la casa
        conf_k = int(max(38, min(80, round(conf_p * 100))))

        # ── PLAN B: escalera de líneas alternas + colchón seguro ────────────
        # La casa pone SU línea y no siempre coincide con la nuestra (a veces muy
        # alta o muy baja). La escalera da la prob a varias líneas para CASAR con
        # la que ofrezca el book; el plan_b es el OVER más alto que aún cubre ≥72%
        # (colchón seguro, como el +2.5 del run line) para cuando el ponche es la
        # opción pero la línea no coincide.
        escalera = []
        for ln in (round(k_proy) - 2.5, round(k_proy) - 1.5, round(k_proy) - 0.5,
                   round(k_proy) + 0.5, round(k_proy) + 1.5):
            if ln < 1.5:
                continue
            po = _poisson_over(k_proy, ln)
            escalera.append({'linea': ln, 'over': round(po * 100), 'under': round((1 - po) * 100)})
        plan_b = None
        for e in escalera:                     # ascendente → me quedo con el OVER más alto ≥72%
            if e['over'] >= 72:
                plan_b = {'pick': f"OVER {e['linea']} K", 'confianza': e['over'],
                          'nota': 'Plan B seguro: colchón de K si la línea de la casa no coincide'}

        k_picks.append({
            'pitcher': pitcher, 'k9': round(k9, 1), 'proyeccion': k_proy,
            'linea': linea_casa, 'linea_programa': linea, 'linea_casa': linea_casa,
            'prediccion': pred, 'pick': f"{pred} {linea_casa} K",
            'prob_over_casa': round(p_over * 100, 1), 'apostable': apostable,
            'confianza': conf_k,
            'escalera': escalera, 'plan_b': plan_b,
        })

    resultado = {
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
        'alerta_upset': alerta_upset,   # aviso si abridor/mercado sugiere upset (no voltea el pick)
        # Transparencia y extras
        'razones': razones[:5],
        'hr_candidates': hr_candidates,
        'k_picks': k_picks,
        'tb_picks': tb_picks,
        'run_line': _runline_pick(pick_team, local, visitante, confianza, p_pick, abs(diff_pct),
                                  modelo_rl=(res_dc or {}).get("run_line")),
        'score_raw': round(score, 2),
        'pitchers': {'local': hp, 'visitante': ap},
    }
    # Selector del MEJOR mercado del juego, ponderado por rendimiento histórico
    resultado['mejor_apuesta'] = _mejor_apuesta_mlb(resultado)
    return resultado
