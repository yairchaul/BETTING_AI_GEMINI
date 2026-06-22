# -*- coding: utf-8 -*-
"""
ANALIZADOR JERÁRQUICO UNIFICADO — FÚTBOL V25
Soporta: ligas normales + Copa del Mundo 2026 + EURO + Copa América
Fixes v25: threshold ≥3.5, divisor dinámico, recency weighting, fase de torneo
"""

import math
import logging
from utils.database_manager import db
from .motor_fut_pro import analizar_futbol_pro_v20

logger = logging.getLogger(__name__)

# ─── Reglas adicionales para partidos de torneo (eliminación directa) ─────────
TORNEO_BOOST = 0.95   # Los equipos se vuelven más cautelosos → ligero sesgo UNDER

# ─── Ranking FIFA aproximado jun-2026 (para fallback sin DB) ──────────────────
_FIFA_RANK = {
    "Argentina": 1, "France": 2, "England": 3, "Belgium": 4,
    "Brazil": 5, "Portugal": 6, "Netherlands": 7, "Spain": 8,
    "Croatia": 9, "Italy": 10, "USA": 11, "United States": 11,
    "Mexico": 12, "Switzerland": 13, "Uruguay": 14, "Colombia": 15,
    "Germany": 16, "Morocco": 17, "Senegal": 18, "Japan": 19,
    "South Korea": 20, "Denmark": 21, "Austria": 22, "Ecuador": 23,
    "Australia": 24, "Hungary": 25, "Poland": 26, "Serbia": 27,
    "Venezuela": 28, "Ukraine": 29, "Canada": 30, "Turkey": 31,
    "Czech Republic": 32, "Czechia": 32, "Slovakia": 33,
    "Romania": 34, "Egypt": 35, "Sweden": 36, "Algeria": 37,
    "Wales": 38, "Costa Rica": 40, "Bolivia": 45, "Paraguay": 46,
    "South Africa": 48, "Jamaica": 52, "Honduras": 55,
    "El Salvador": 60, "Panama": 65, "New Zealand": 70,
    "Guatemala": 75, "Trinidad and Tobago": 78,
}


def _analisis_ranking_fifa(local: str, visitante: str, fase: str = "") -> dict:
    """Fallback por ranking FIFA cuando no hay historial en DB (típico en el
    Mundial). Emite los MERCADOS de alta probabilidad que mejor pegan —
    'favorito anota (Over 0.5)', Over 1.5, BTTS y gana favorito— con confianza
    realista que SÍ califica para el selector de picks/parlays."""
    r_l = next((v for k, v in _FIFA_RANK.items() if k.lower() in local.lower() or local.lower() in k.lower()), 60)
    r_v = next((v for k, v in _FIFA_RANK.items() if k.lower() in visitante.lower() or visitante.lower() in k.lower()), 60)
    diff = r_v - r_l            # positivo = local mejor ranked
    abs_diff = abs(diff)
    fav = local if diff > 0 else visitante
    es_elim = bool(fase) and any(x in fase.lower() for x in ["octavo", "cuarto", "semi", "final", "round of", "quarter"])

    opciones = []
    # Mercado más seguro: el favorito marca al menos un gol (Over 0.5)
    if abs_diff >= 12:
        opciones.append({"pick": f"{fav} OVER 0.5 goles (anota)",
                         "confianza": min(82, 70 + abs_diff // 4), "regla": 1})
    # Con favorito claro suele haber goles → Over 1.5 total
    if abs_diff >= 16:
        opciones.append({"pick": "OVER 1.5 goles",
                         "confianza": min(72, 58 + abs_diff // 5), "regla": 2})
    # Partidos parejos/ofensivos → ambos anotan
    if 8 <= abs_diff <= 24:
        opciones.append({"pick": "AMBOS ANOTAN (BTTS)", "confianza": 58, "regla": 3})
    # Gana el favorito (incluye prórroga en eliminación directa)
    if abs_diff >= 20:
        opciones.append({"pick": f"Gana {fav}" + (" (incluye prórroga)" if es_elim else ""),
                         "confianza": min(70, 56 + abs_diff // 5), "regla": 4})
    # COMBINADO (mayor pago): gana favorito + Over. En mismatches grandes sigue
    # siendo alta probabilidad y paga mucho más (caso Alemania: gana + Over 3.5).
    if abs_diff >= 20:
        p_gana = min(72, 56 + abs_diff // 5)
        linea_over = "2.5" if abs_diff >= 30 else "1.5"
        p_over = min(80, (66 if linea_over == "1.5" else 58) + abs_diff // 5)
        conf_combo = round(p_gana / 100.0 * p_over / 100.0 * 100)
        cuota_combo = round((100.0 / p_gana) * (100.0 / p_over), 2)
        opciones.append({
            "pick": f"Gana {fav} + Over {linea_over}",
            "confianza": conf_combo, "regla": 7, "combo": True, "cuota": cuota_combo,
        })

    # Caso muy parejo: Over 1.5 suave
    if not opciones:
        opciones.append({"pick": "OVER 1.5 goles", "confianza": 55, "regla": 2})

    # En eliminación directa los equipos se cierran → enfría mercados de goles
    if es_elim:
        for o in opciones:
            if "OVER" in o["pick"] or "BTTS" in o["pick"]:
                o["confianza"] = max(50, o["confianza"] - 4)

    # ── Calibración WC: ajusta BTTS down, Over 1.5 up según tasas históricas ──
    wc_nota_rank = ""
    try:
        from motors.wc_cerebro import ajustar_pick, resumen_wc
        for o in opciones:
            new_conf, nota = ajustar_pick(o["pick"], o["confianza"], True, fase)
            if nota:
                o["confianza"] = new_conf
        wc_nota_rank = resumen_wc(fase)
    except Exception:
        pass

    # Orden por VALOR: COMBO > Gana favorito > Over 1.5 > Over 0.5 (demasiado seguro).
    # Dentro del mismo nivel, gana la mayor confianza.
    def _rank_prio(o):
        p = o["pick"].lower()
        if o.get("combo"):       return (0, -o["confianza"])   # COMBO mismatch
        if "gana " in p:         return (1, -o["confianza"])   # ML favorito
        if "over 1.5" in p:      return (2, -o["confianza"])   # Over 1.5 razonable
        if "btts" in p or "ambos anotan" in p: return (2, -o["confianza"])
        if "over 0.5" in p:      return (3, -o["confianza"])   # Over 0.5 = paga nada
        return (2, -o["confianza"])
    opciones.sort(key=_rank_prio)
    best = opciones[0]

    # Debug de reglas
    debug_reglas = [{
        "pick": o["pick"],
        "confianza": o["confianza"],
        "regla": o["regla"],
        "descripcion": {1:"Over 0.5 favorito",2:"Over 1.5",3:"BTTS",4:"Gana favorito",7:"Combo gana+Over"}.get(o["regla"],""),
        "es_principal": o["pick"] == best["pick"],
    } for o in opciones]

    return {
        "pick": best["pick"],
        "confianza": best["confianza"],
        "regla": best["regla"],
        "todas_opciones": opciones,
        "nota": f"Ranking FIFA: #{r_l} {local} vs #{r_v} {visitante} (sin historial en DB).",
        "wc_nota": wc_nota_rank,
        "h2h_nota": "",
        "liga_nota": "",
        "pick_motor_1": best["pick"],
        "conf_motor_1": best["confianza"],
        "regla_motor_1": best["regla"],
        "debug_reglas": debug_reglas,
    }


def _pct(lista: list, condicion) -> float:
    """Porcentaje de elementos que cumplen la condición. Devuelve 0 si lista vacía."""
    if not lista:
        return 0.0
    return sum(1 for x in lista if condicion(x)) / len(lista) * 100


def _weighted_avg(lista: list) -> float:
    """Media ponderada dando más peso a los partidos recientes."""
    if not lista:
        return 0.0
    n = len(lista)
    pesos = list(range(1, n + 1))  # 1, 2, 3 … n (más reciente = mayor peso)
    total_peso = sum(pesos)
    return sum(v * w for v, w in zip(lista, pesos)) / total_peso


def _h2h_suplemento(local: str, visitante: str) -> dict:
    """Datos H2H históricos de international_results (martj42) como contexto extra.
    Nunca falla: devuelve {} si los datos no están disponibles."""
    try:
        from motors.international_results import head_to_head, historial_mundial
        h2h = head_to_head(local, visitante, n=20)
        if h2h.get('total', 0) < 3:
            return {}
        wc_l = historial_mundial(local)
        wc_v = historial_mundial(visitante)
        return {
            'total': h2h['total'],
            'pct_local': h2h['pct_local'],
            'pct_empate': h2h['pct_empate'],
            'pct_visita': h2h['pct_visita'],
            'avg_goles': h2h['avg_total'],
            'ultimos': h2h.get('ultimos', []),
            'wc_local': wc_l,
            'wc_visita': wc_v,
        }
    except Exception:
        return {}


def analizar_futbol_jerarquico(
    local: str,
    visitante: str,
    es_torneo: bool = False,
    fase: str = "",
    forzar_ranking: bool = False,
    liga: str = "",
) -> dict:
    """
    Aplica reglas de descarte jerárquico para fútbol.

    Args:
        local:     Nombre del equipo local
        visitante: Nombre del equipo visitante
        es_torneo: True si es torneo internacional (Mundial, EURO, Copa América…)
        fase:      Fase del torneo ('Grupo', 'Octavos', 'Cuartos', 'Semifinal', 'Final')
        forzar_ranking: usa SOLO el fallback por ranking FIFA (lógica pre-partido),
                   sin leer la DB. En el backtest de torneos evita el "leakage" de
                   stats post-juego y reproduce el MISMO pick que mostró la tarjeta.
    """
    if forzar_ranking:
        res = _analisis_ranking_fifa(local, visitante, fase)
        res['h2h_historico'] = _h2h_suplemento(local, visitante)
        return res
    s_l = db.get_team_stats_detailed(local, "soccer")
    s_v = db.get_team_stats_detailed(visitante, "soccer")

    if not s_l or not s_v:
        res = _analisis_ranking_fifa(local, visitante, fase)
        res['h2h_historico'] = _h2h_suplemento(local, visitante)
        # Aplicar calibración de liga incluso en el fallback de ranking
        if liga:
            try:
                from motors.liga_calibrador import calibrar_pick as _cal_liga
                conf_cal, liga_nota = _cal_liga(res["pick"], res["confianza"], liga)
                if liga_nota:
                    res = dict(res)
                    res["liga_nota"] = liga_nota
                    if "PICK CAMBIADO:" in liga_nota:
                        res["pick"] = liga_nota.split("PICK CAMBIADO:")[-1].strip()
                    res["confianza"] = conf_cal
            except Exception:
                pass
        return res

    gl = s_l.get("goles_favor", [])
    gc = s_l.get("goles_contra", [])
    ht_l = s_l.get("goles_ht", [0] * len(gl))

    gv = s_v.get("goles_favor", [])
    gc_v = s_v.get("goles_contra", [])
    ht_v = s_v.get("goles_ht", [0] * len(gv))

    # Mínimo 2 partidos por equipo para continuar
    if len(gl) < 2 or len(gv) < 2:
        return _analisis_ranking_fifa(local, visitante, fase)

    total_partidos = len(gl) + len(gv)

    # Totales por partido (favor + contra)
    totales_l = [f + c for f, c in zip(gl, gc)]
    totales_v = [f + c for f, c in zip(gv, gc_v)]
    todos_totales = totales_l + totales_v

    # Promedio ponderado por recencia
    avg_goles_l = _weighted_avg(totales_l)
    avg_goles_v = _weighted_avg(totales_v)

    # Aplicar factor conservador en fases eliminatorias
    fase_lower = (fase or "").lower()
    es_eliminacion = es_torneo and any(
        k in fase_lower for k in ("octavo", "cuarto", "semi", "final", "round of", "quarter", "knockout")
    )
    factor_fase = TORNEO_BOOST if es_eliminacion else 1.0

    viable_picks = []

    # ── Regla 1 — OVER 1.5 HT: P(2+ goles TOTALES en el 1er tiempo) ─────────
    # Modelo Poisson sobre los goles esperados de AMBOS equipos en la 1ª parte.
    #   • Si el historial trae goles de HT reales → se usan directamente.
    #   • Si no (la mayoría de fuentes solo dan el marcador final) → se ESTIMAN
    #     aplicando la cuota histórica de goles en la 1ª parte (~45% del total).
    hay_ht_real = any(g and g > 0 for g in (ht_l + ht_v))
    if hay_ht_real:
        lam_ht = _weighted_avg(ht_l) + _weighted_avg(ht_v)      # goles esperados HT (local+visita)
        fuente_ht = "HT real"
    else:
        exp_total_ft = (avg_goles_l + avg_goles_v) / 2.0
        lam_ht = 0.45 * exp_total_ft                            # ~45% de los goles caen en la 1ª parte
        fuente_ht = "estimado FT·0.45"
    # P(X >= 2) con X ~ Poisson(lam_ht):  1 - P(0) - P(1)
    prob_ht = max(0.0, 1 - math.exp(-lam_ht) * (1 + lam_ht)) * 100 * factor_fase
    if prob_ht >= 60:
        viable_picks.append({"pick": "OVER 1.5 HT", "confianza": round(prob_ht, 1),
                             "regla": 1, "fuente_ht": fuente_ht})

    # ── Regla 2 — OVER 3.5 ≥ 60% (fix: >= en lugar de >) ────────────────────
    prob_o35 = _pct(todos_totales, lambda t: t >= 3.5) * factor_fase  # FIX: >= 3.5
    if prob_o35 >= 60:
        viable_picks.append({"pick": "OVER 3.5 FT", "confianza": round(prob_o35, 1), "regla": 2})

    # ── Regla 3 — BTTS ≥ 60% ─────────────────────────────────────────────────
    hits_btts = (
        sum(1 for f, c in zip(gl, gc) if f > 0 and c > 0)
        + sum(1 for f, c in zip(gv, gc_v) if f > 0 and c > 0)
    )
    prob_btts = (hits_btts / total_partidos) * 100 * factor_fase
    if prob_btts >= 60:
        viable_picks.append({"pick": "AMBOS ANOTAN (BTTS)", "confianza": round(prob_btts, 1), "regla": 3})

    # ── Regla 4 — Overs de tiempo completo con su PROBABILIDAD REAL ─────────
    # Antes se elegía "el over más cercano al 55%", lo que IGNORABA a propósito
    # el OVER 1.5 de alta probabilidad. Ahora se añaden los OVER con su prob
    # real para que el de MAYOR probabilidad pueda ganar la selección. En el
    # Mundial el OVER 1.5 ronda 75-88% y suele ser el mercado más probable.
    p_o15 = _pct(todos_totales, lambda t: t > 1.5)
    p_o25 = _pct(todos_totales, lambda t: t > 2.5)
    p_o35_raw = _pct(todos_totales, lambda t: t >= 3.5)
    for nombre, pr in (("OVER 1.5", p_o15), ("OVER 2.5", p_o25), ("OVER 3.5", p_o35_raw)):
        if pr >= 55:
            viable_picks.append({"pick": nombre, "confianza": round(min(92, pr * factor_fase), 1), "regla": 4})
    # UNDER 2.5 — matchups DEFENSIVOS (ambos conceden/anotan poco). Detecta los
    # partidos cerrados (p.ej. Mexico 1-0 Korea) donde el OVER falla. Compite por
    # probabilidad como el resto: si el UNDER es más probable, gana la selección.
    p_under25 = _pct(todos_totales, lambda t: t <= 2.5)
    if p_under25 >= 58:
        viable_picks.append({"pick": "UNDER 2.5", "confianza": round(min(88, p_under25 * factor_fase), 1), "regla": 4})
    # Si ninguno llega a 55%, usar el más cercano (para no quedar sin over)
    if not any(p["regla"] == 4 for p in viable_picks):
        dist = {abs(p_o15 - 55): ("OVER 1.5", p_o15), abs(p_o25 - 55): ("OVER 2.5", p_o25),
                abs(p_o35_raw - 55): ("OVER 3.5", p_o35_raw)}
        nm, pr = dist[min(dist.keys())]
        viable_picks.append({"pick": nm, "confianza": round(max(50, pr), 1), "regla": 4})

    # ── Regla 5 — Moneyline ≥ 55% ────────────────────────────────────────────
    n_l = len(gl)
    n_v = len(gv)
    vic_l = s_l.get("victorias", 0)
    vic_v = s_v.get("victorias", 0)
    prob_l = (vic_l / n_l) * 100 if n_l > 0 else 0.0   # FIX: divisor dinámico
    prob_v = (vic_v / n_v) * 100 if n_v > 0 else 0.0

    # En TORNEOS de selecciones, el win% de los últimos 5 (amistosos/eliminatorias
    # vs rivales muy dispares) NO refleja la fuerza real. Se MEZCLA con la
    # probabilidad implícita por RANKING FIFA, dándole MÁS peso al ranking (0.70),
    # que el backtest mostró como la señal más fiable para selecciones. Evita
    # elegir a un equipo flojo con buena racha (Australia #24) sobre uno fuerte
    # (USA #11) y, a la vez, SÍ favorece al fuerte cuando corresponde.
    if es_torneo:
        r_l = next((v for k, v in _FIFA_RANK.items() if k.lower() in local.lower() or local.lower() in k.lower()), 60)
        r_v = next((v for k, v in _FIFA_RANK.items() if k.lower() in visitante.lower() or visitante.lower() in k.lower()), 60)
        edge = max(-0.35, min(0.35, (r_v - r_l) / 80.0))   # ventaja del mejor ranked (±35%)
        rank_prob_l = 50 + edge * 100
        rank_prob_v = 50 - edge * 100
        _W_RANK = 0.70   # peso del ranking (forma reciente de selecciones = ruidosa)
        prob_l = (1 - _W_RANK) * prob_l + _W_RANK * rank_prob_l
        prob_v = (1 - _W_RANK) * prob_v + _W_RANK * rank_prob_v

    if prob_l >= 55:
        viable_picks.append({"pick": f"LOCAL ({local})", "confianza": round(prob_l, 1), "regla": 5})
    if prob_v >= 55:
        viable_picks.append({"pick": f"VISITANTE ({visitante})", "confianza": round(prob_v, 1), "regla": 5})

    # ── Regla 6 — UNDER 2.5 en partidos de eliminación directa ──────────────
    if es_eliminacion:
        p_under25 = _pct(todos_totales, lambda t: t <= 2.5)
        if p_under25 >= 60:
            viable_picks.append({
                "pick": "UNDER 2.5 (Eliminación directa)",
                "confianza": round(p_under25, 1),
                "regla": 6,
            })

    # ── Regla 7 — COMBINADO (gana + Over 2.5/3.5): mismatch claro ───────────
    # Exige favorito con ML ≥63% Y Over 2.5 ≥58%. El combo NO incluye Over 1.5
    # (ese es el fallback, no aporta valor pagado). Se prefiere la línea más alta.
    ml_pick = next((p for p in viable_picks if p["regla"] == 5 and p["confianza"] >= 63), None)
    # Solo Over 2.5 y Over 3.5 para el combo (Over 1.5 en combo no paga)
    over_opciones_combo = [("OVER 2.5", p_o25), ("OVER 3.5", p_o35_raw)]
    over_fuerte = [(nm, pr) for nm, pr in over_opciones_combo if pr >= 58]
    if ml_pick and over_fuerte and not es_eliminacion:
        over_nombre, over_prob = over_fuerte[-1]   # línea más alta que cumple
        equipo = ml_pick["pick"].split("(")[-1].rstrip(")") if "(" in ml_pick["pick"] else ml_pick["pick"]
        conf_combo = round(ml_pick["confianza"] / 100.0 * over_prob / 100.0 * 100)
        cuota_combo = round((100.0 / max(1, ml_pick["confianza"])) * (100.0 / max(1, over_prob)), 2)
        viable_picks.append({
            "pick": f"Gana {equipo} + {over_nombre}",
            "confianza": conf_combo, "regla": 7, "combo": True, "cuota": cuota_combo,
        })

    # ── Pre-calibración WC: descarta picks cuya confianza cae < 50% ─────────
    # (se aplica ANTES de la selección para que picks degradados no bloqueen
    #  opciones con mayor confianza como el Moneyline)
    if es_torneo:
        try:
            from motors.wc_cerebro import ajustar_pick as _wc_ajustar
            viables_post_wc = []
            for vp in viable_picks:
                conf_adj, _ = _wc_ajustar(vp["pick"], vp["confianza"], True, fase)
                if conf_adj >= 50:
                    vp_copia = dict(vp)
                    vp_copia["confianza"] = conf_adj
                    viables_post_wc.append(vp_copia)
            if viables_post_wc:
                viable_picks = viables_post_wc
        except Exception:
            pass

    # ── Selección primaria por VALOR, no solo por probabilidad ────────────────
    # Orden: COMBO > OVER 2.5/3.5 (≥50%) > BTTS (≥58%) > UNDER (≥55%) > ML (≥63%) > OVER 1.5.
    # OVER 2.5 SIEMPRE gana a OVER 1.5 desde 50%: mayor pago con probabilidad suficiente.
    def _prioridad(x):
        pick_lower = x.get("pick", "").lower()
        conf = x.get("confianza", 0)
        es_combo = x.get("regla") == 7
        if es_combo and conf >= 40:
            return (0, -conf)   # COMBO válido → máximo valor
        if ("over 2.5" in pick_lower or "over 3.5" in pick_lower) and conf >= 50:
            return (1, -conf)   # OVER alto → mejor pago que OVER 1.5 desde 50%
        if ("btts" in pick_lower or "ambos anotan" in pick_lower) and conf >= 58:
            return (1, -conf)   # BTTS → ambos anotan, buen pago
        if "under" in pick_lower and conf >= 55:
            return (2, -conf)   # UNDER → matchup defensivo detectado
        if ("local (" in pick_lower or "visitante (" in pick_lower) and conf >= 63:
            return (3, -conf)   # ML simple → solo si es claro
        return (4, -conf)       # OVER 1.5 / HT / resto → fallback

    primary = {"pick": "REVISAR DATOS", "confianza": 0.0, "regla": 99}
    if viable_picks:
        viable_picks.sort(key=_prioridad)
        primary = viable_picks[0]
    # Guardar pick ANTES de calibraciones (Motor 1 original — reglas puras sin ajuste de liga/WC)
    pick_motor_1 = primary["pick"]
    conf_motor_1 = primary["confianza"]
    regla_motor_1 = primary["regla"]

    logger.info(
        f"Análisis futbol {local} vs {visitante} → {primary['pick']} "
        f"({primary['confianza']:.1f}% Regla {primary['regla']}) "
        f"[torneo={es_torneo} fase={fase}]"
    )

    # ── Suplemento H2H histórico (martj42/international_results) ─────────────
    h2h = _h2h_suplemento(local, visitante)
    h2h_nota = ""

    if h2h.get('total', 0) >= 5:
        pick_lower = primary["pick"].lower()
        if "local" in pick_lower or local.lower() in pick_lower:
            diff_h2h = (h2h['pct_local'] - 40) / 10.0
            primary["confianza"] = round(max(50, min(88, primary["confianza"] + diff_h2h * 2)), 1)
            h2h_nota = f"H2H: {local} gana {h2h['pct_local']}% en {h2h['total']} partidos históricos"
        elif "visitante" in pick_lower or visitante.lower() in pick_lower:
            diff_h2h = (h2h['pct_visita'] - 40) / 10.0
            primary["confianza"] = round(max(50, min(88, primary["confianza"] + diff_h2h * 2)), 1)
            h2h_nota = f"H2H: {visitante} gana {h2h['pct_visita']}% en {h2h['total']} partidos históricos"
        elif "btts" in pick_lower or "ambos anotan" in pick_lower:
            if h2h['avg_goles'] >= 2.5:
                primary["confianza"] = round(min(88, primary["confianza"] + 2), 1)
            h2h_nota = f"H2H avg goles: {h2h['avg_goles']} en {h2h['total']} partidos"
        elif "over" in pick_lower:
            if h2h['avg_goles'] >= 2.0:
                primary["confianza"] = round(min(88, primary["confianza"] + 1.5), 1)
            h2h_nota = f"H2H avg goles: {h2h['avg_goles']}"

    # ── Nota WC (la confianza YA se calibró en la PRE-calibración; NO se ──────
    # ── re-aplica aquí para evitar la doble inflación del OVER 1.5). ─────────
    wc_nota = ""
    if es_torneo:
        try:
            from motors.wc_cerebro import resumen_wc
            wc_nota = resumen_wc(fase)
        except Exception:
            pass

    # ── Calibración por liga/competición (degradar Over 3.5→1.5 en ligas ────
    # ── defensivas, Over 2.5→1.5 en Copa Libertadores/Sudamericana, etc.) ───
    liga_nota = ""
    if liga:
        try:
            from motors.liga_calibrador import calibrar_pick as _cal_liga
            conf_cal, liga_nota = _cal_liga(primary["pick"], primary["confianza"], liga)
            if liga_nota:
                if "PICK CAMBIADO:" in liga_nota:
                    nuevo_pick = liga_nota.split("PICK CAMBIADO:")[-1].strip()
                    primary = dict(primary)
                    primary["pick"] = nuevo_pick
                    primary["confianza"] = conf_cal
                else:
                    primary["confianza"] = conf_cal
        except Exception:
            pass

    # ── Motor V2 (rapido/momentum) en paralelo ───────────────────────────────
    motor_v2 = None
    try:
        from motors.futbol_analyzer_rapido import analizar_futbol_rapido
        motor_v2 = analizar_futbol_rapido(local, visitante, es_torneo, fase)
    except Exception as _e:
        logger.debug(f"motor_v2 falló: {_e}")

    # ── Picks múltiples: todos los markets que califican de forma independiente ──
    # Umbrales por tipo de mercado (independientes del pick primario)
    _UMBRALES_MULTI = {
        "over 1.5 ht": 65,
        "over 1.5": 60,
        "over 2.5": 52,
        "over 3.5": 55,
        "btts": 58,
        "ambos anotan": 58,
        "under": 52,
        "local (": 63,
        "visitante (": 63,
    }
    picks_multiples = []
    for vp in viable_picks:
        p_lower = vp["pick"].lower()
        umbral = 68  # default para tipos no listados
        for key, thr in _UMBRALES_MULTI.items():
            if key in p_lower:
                umbral = thr
                break
        if vp["confianza"] >= umbral:
            picks_multiples.append(dict(vp))
    # Ordenar: primario al frente, luego por confianza
    picks_multiples.sort(key=lambda x: (0 if x["pick"] == primary["pick"] else 1, -x["confianza"]))

    # ── Marcador correcto (Dixon-Coles) ───────────────────────────────────────
    # Para selecciones internacionales: top-N marcadores + matriz (heatmap) +
    # 1X2 derivado del MISMO modelo. Cae a None para clubes (no están en el dataset).
    marcador_correcto = None
    try:
        from motors.dixon_coles import predecir as _dc_predecir
        _dc = _dc_predecir(local, visitante, neutral=bool(es_torneo))
        if _dc.get("disponible"):
            marcador_correcto = _dc
    except Exception as _e:
        logger.debug(f"dixon_coles no disponible para {local} vs {visitante}: {_e}")

    # Debug: motivos por los que cada regla fue/no fue elegida
    debug_reglas = []
    for vp in viable_picks:
        regla_desc = {
            1: "OVER 1.5 HT ≥ 60%", 2: "OVER 3.5 ≥ 60%", 3: "BTTS ≥ 60%",
            4: "Mejor OVER cercano a 55%", 5: "Moneyline ≥ 55%",
            6: "UNDER 2.5 eliminación directa", 7: "COMBINADO (gana+Over)",
        }.get(vp.get("regla"), "regla desconocida")
        debug_reglas.append({
            "pick": vp["pick"],
            "confianza": vp["confianza"],
            "regla": vp.get("regla"),
            "descripcion": regla_desc,
            "es_principal": vp["pick"] == primary["pick"],
        })

    return {
        "pick":         primary["pick"],
        "confianza":    primary["confianza"],
        "regla":        primary["regla"],
        "todas_opciones": viable_picks,
        "avg_goles_local":  round(avg_goles_l, 2),
        "avg_goles_visit":  round(avg_goles_v, 2),
        "es_torneo":    es_torneo,
        "fase":         fase,
        "es_eliminacion": es_eliminacion,
        "h2h_historico": h2h,
        "h2h_nota":     h2h_nota,
        "wc_nota":      wc_nota,
        "liga_nota":    liga_nota,
        "pick_motor_1": pick_motor_1,
        "conf_motor_1": conf_motor_1,
        "regla_motor_1": regla_motor_1,
        "motor_v2":     motor_v2,
        "debug_reglas": debug_reglas,
        "picks_multiples": picks_multiples,
        "marcador_correcto": marcador_correcto,
    }


# ──────────────────────────────────────────────────────────────────────────
# MERCADOS COMPLETOS (para el botón "Analizar IA"): Moneyline 1X2, Over/Under,
# BTTS sí/no, y posibles goleadores. Modelo Poisson sobre goles esperados.
# ──────────────────────────────────────────────────────────────────────────
import math as _math


def _poisson(k, lam):
    try:
        return _math.exp(-lam) * (lam ** k) / _math.factorial(k)
    except Exception:
        return 0.0


def _avg(lista, default=1.2):
    return sum(lista) / len(lista) if lista else default


def mercados_completos_futbol(local, visitante, es_torneo=False, fase=""):
    """Devuelve probabilidades de Moneyline (1X2), Over/Under 2.5, BTTS sí/no
    y goleadores probables. Fuente primaria: Dixon-Coles (selecciones); si no
    está disponible (clubes), cae a historial (DB) o ranking FIFA."""
    # ── Fuente PRIMARIA: Dixon-Coles (ataque/defensa + Poisson con corrección τ)
    try:
        from motors.dixon_coles import predecir as _dc_predecir
        _dc = _dc_predecir(local, visitante, neutral=bool(es_torneo))
    except Exception:
        _dc = {"disponible": False}

    if _dc.get("disponible"):
        try:
            from motors.futbol_props import obtener_goleadores_partido
            goleadores = obtener_goleadores_partido(local, visitante)
        except Exception:
            goleadores = {"local": [], "visitante": []}
        return {
            "fuente": "dixon-coles",
            "xg_local": _dc["xg_local"], "xg_visitante": _dc["xg_visit"],
            "moneyline": {"local": _dc["prob"]["local"], "empate": _dc["prob"]["empate"],
                          "visitante": _dc["prob"]["visitante"]},
            "over_under": {"over_2.5": _dc["over_under"]["over_2.5"],
                           "under_2.5": _dc["over_under"]["under_2.5"],
                           "over_1.5": _dc["over_under"]["over_1.5"]},
            "btts": _dc["btts"],
            "goleadores": goleadores,
            "marcador_correcto": _dc,
        }

    s_l = db.get_team_stats_detailed(local, "soccer")
    s_v = db.get_team_stats_detailed(visitante, "soccer")

    fuente = "historial"
    if s_l and s_v and s_l.get("goles_favor") and s_v.get("goles_favor"):
        gf_l, gc_l = _avg(s_l.get("goles_favor", [])), _avg(s_l.get("goles_contra", []))
        gf_v, gc_v = _avg(s_v.get("goles_favor", [])), _avg(s_v.get("goles_contra", []))
        xg_l = max(0.2, (gf_l + gc_v) / 2 * 1.10)   # localía
        xg_v = max(0.2, (gf_v + gc_l) / 2)
    else:
        # Respaldo por ranking FIFA
        r_l = next((v for k, v in _FIFA_RANK.items() if k.lower() in local.lower() or local.lower() in k.lower()), 60)
        r_v = next((v for k, v in _FIFA_RANK.items() if k.lower() in visitante.lower() or visitante.lower() in k.lower()), 60)
        diff = (r_v - r_l) / 20.0
        xg_l = max(0.3, 1.4 + diff * 0.5)
        xg_v = max(0.3, 1.4 - diff * 0.5)
        fuente = "ranking FIFA"

    pl = [_poisson(i, xg_l) for i in range(7)]
    pv = [_poisson(j, xg_v) for j in range(7)]
    p_home = p_draw = p_away = p_over25 = p_over15 = p_btts = 0.0
    for i in range(7):
        for j in range(7):
            p = pl[i] * pv[j]
            if i > j:
                p_home += p
            elif i == j:
                p_draw += p
            else:
                p_away += p
            if i + j > 2.5:
                p_over25 += p
            if i + j > 1.5:
                p_over15 += p
            if i > 0 and j > 0:
                p_btts += p

    _r = lambda x: round(x * 100, 1)
    # Goleadores
    try:
        from motors.futbol_props import obtener_goleadores_partido
        goleadores = obtener_goleadores_partido(local, visitante)
    except Exception:
        goleadores = {"local": [], "visitante": []}

    return {
        "fuente": fuente,
        "xg_local": round(xg_l, 2), "xg_visitante": round(xg_v, 2),
        "moneyline": {"local": _r(p_home), "empate": _r(p_draw), "visitante": _r(p_away)},
        "over_under": {"over_2.5": _r(p_over25), "under_2.5": _r(1 - p_over25),
                       "over_1.5": _r(p_over15)},
        "btts": {"si": _r(p_btts), "no": _r(1 - p_btts)},
        "goleadores": goleadores,
        "marcador_correcto": None,
    }
