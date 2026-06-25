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


# ──────────────────────────────────────────────────────────────────────────
# INTEGRACIÓN DIXON-COLES → selección de picks
# La matriz de marcadores da la probabilidad EXACTA de cada mercado. Se usa para
# (1) surtir picks que califican (incl. UNDER 1.5 y UNDER 1.5 HT que el motor de
# reglas casi no emite) y (2) corregir el pick primario cuando el modelo lo
# contradice (el backtest probó que DC acierta más en selecciones).
# ──────────────────────────────────────────────────────────────────────────
def _tipo_mercado_simple(pick: str) -> str:
    """Clasifica un pick a un tipo de mercado canónico (para deduplicar)."""
    p = (pick or "").lower()
    if "+" in p or "combinad" in p or "combo" in p: return "combo"
    if "doble" in p: return "doble"
    if "over 1.5 ht" in p: return "ht_over"
    if "under 1.5 ht" in p: return "ht_under"
    if "over 1.5" in p: return "over1.5"
    if "over 2.5" in p: return "over2.5"
    if "over 3.5" in p: return "over3.5"
    if "under 1.5" in p: return "under1.5"
    if "under 2.5" in p or "under" in p: return "under2.5"
    if "btts" in p or "ambos" in p: return "btts"
    if "local (" in p: return "local"
    if "visitante (" in p: return "visitante"
    if "empate" in p: return "empate"
    return p[:14]


def _picks_dixon_coles(mc: dict, local: str, visitante: str) -> list:
    """Picks que CALIFICAN según las probabilidades exactas de la matriz DC.
    Umbrales más bajos que el motor de reglas porque estas probabilidades son
    exactas y están calibradas (lo confirmó el backtest)."""
    m = mc.get("mercados", {})
    if not m:
        return []
    picks = []

    def add(pick, conf):
        picks.append({"pick": pick, "confianza": round(conf, 1), "regla": "DC", "fuente_dc": True})

    # Moneyline
    if m.get("local", 0) >= 55:      add(f"LOCAL ({local})", m["local"])
    if m.get("visitante", 0) >= 55:  add(f"VISITANTE ({visitante})", m["visitante"])
    # Doble oportunidad (lado del favorito; pago bajo pero muy seguro)
    if m.get("local", 0) > m.get("visitante", 0) and m.get("doble_1x", 0) >= 78:
        add(f"DOBLE: {local} o Empate", m["doble_1x"])
    elif m.get("visitante", 0) > m.get("local", 0) and m.get("doble_x2", 0) >= 78:
        add(f"DOBLE: Empate o {visitante}", m["doble_x2"])
    # ── Empate / doble oportunidad en partidos PAREJOS ──────────────────────
    # El motor de reglas NUNCA emite empate, pero en torneos de selecciones los
    # partidos cerrados son comunes (Mexico 1-1 Korea) y el empate PAGA bien
    # (~+250). El histórico WC da ~21-22% de empates, así que solo se surte
    # cuando el 1X2 de DC ve el partido claramente MÁS cerrado que esa media.
    pE = m.get("empate", 0)
    pL_ml = m.get("local", 0)
    pV_ml = m.get("visitante", 0)
    toss_up = pL_ml < 50 and pV_ml < 50          # sin favorito claro
    if pE >= 32:                                  # empate directo de valor
        add("EMPATE", pE)
    if toss_up and pE >= 26:                      # cubrir empate + resultado del lado probable
        if pL_ml >= pV_ml and m.get("doble_1x", 0) >= 65:
            add(f"DOBLE: {local} o Empate", m["doble_1x"])
        elif pV_ml > pL_ml and m.get("doble_x2", 0) >= 65:
            add(f"DOBLE: Empate o {visitante}", m["doble_x2"])
    # Over / Under tiempo completo. Umbrales calibrados con el backtest:
    #   • OVER 1.5, OVER 2.5, UNDER 2.5: confiables (ganan ≥62% out-of-sample).
    #   • UNDER 1.5: sólo con prob MUY alta (al 55% ganaba <40% — Poisson subestima
    #     la varianza de goles).
    #   • OVER 3.5 y BTTS: NO se surten — el backtest mostró que un Poisson
    #     independiente no los predice (ganan ~52-55% diciendo 70%). Quedan
    #     visibles en la matriz, pero el motor no los recomienda.
    if m.get("over_1.5", 0) >= 70:   add("OVER 1.5", m["over_1.5"])
    if m.get("over_2.5", 0) >= 55:   add("OVER 2.5", m["over_2.5"])
    if m.get("under_1.5", 0) >= 72:  add("UNDER 1.5", m["under_1.5"])
    if m.get("under_2.5", 0) >= 68:  add("UNDER 2.5", m["under_2.5"])
    # Primer tiempo (umbral alto por la misma subestimación de varianza)
    if m.get("ht_under_1.5", 0) >= 70: add("UNDER 1.5 HT", m["ht_under_1.5"])
    if m.get("ht_over_1.5", 0) >= 62:  add("OVER 1.5 HT", m["ht_over_1.5"])
    return picks


def _dc_prob_de_pick(pick: str, m: dict, local: str, visitante: str):
    """Probabilidad que DC asigna al pick heurístico (o None si no se puede mapear,
    p.ej. combos). Sirve para validar/corregir el pick primario."""
    p = (pick or "").lower()
    if "+" in p or "combinad" in p or "combo" in p:
        return None
    if "btts" in p or "ambos" in p:        return m.get("btts_si")
    if "over 3.5" in p:                    return m.get("over_3.5")
    if "over 2.5" in p:                    return m.get("over_2.5")
    if "over 1.5 ht" in p:                 return m.get("ht_over_1.5")
    if "under 1.5 ht" in p:                return m.get("ht_under_1.5")
    if "over 1.5" in p:                    return m.get("over_1.5")
    if "over 0.5" in p:                    return m.get("ht_over_0.5") if "ht" in p else None
    if "under 2.5" in p:                   return m.get("under_2.5")
    if "under 1.5" in p:                   return m.get("under_1.5")
    if "under" in p:                       return m.get("under_2.5")
    if "doble" in p and local.lower() in p:    return m.get("doble_1x")
    if "doble" in p and visitante.lower() in p: return m.get("doble_x2")
    if "empate" in p:                      return m.get("empate")
    if local.lower() in p or "local" in p: return m.get("local")
    if visitante.lower() in p or "visitante" in p: return m.get("visitante")
    return None


def _mejor_pick_dc(dc_picks: list):
    """Elige el pick DC de mayor VALOR (no solo mayor probabilidad)."""
    def prioridad(x):
        p = x["pick"].lower()
        c = x["confianza"]
        if "over 2.5" in p or "over 3.5" in p:           return (0, -c)  # buen pago, prob suficiente
        if "empate" in p and "doble" not in p:           return (1, -c)  # empate directo paga bien
        if "btts" in p or "ambos" in p:                  return (1, -c)
        if "under 2.5" in p:                             return (1, -c)
        if "local (" in p or "visitante (" in p:         return (2, -c)
        if "under 1.5" in p and "ht" not in p:           return (3, -c)
        if "ht" in p:                                    return (4, -c)
        if "over 1.5" in p:                              return (5, -c)
        return (6, -c)  # doble oportunidad (pago muy bajo) al final
    return sorted(dc_picks, key=prioridad)[0] if dc_picks else None


def _integrar_dixon_coles(mc, local, visitante, primary, picks_multiples):
    """Surte los picks de la matriz a picks_multiples y corrige el primario si DC
    lo contradice. Devuelve (primary, picks_multiples, ajuste_dc)."""
    ajuste_dc = ""
    if not (mc and mc.get("disponible") and mc.get("mercados")):
        return primary, picks_multiples, ajuste_dc

    m = mc["mercados"]
    dc_picks = _picks_dixon_coles(mc, local, visitante)

    # Surtir picks DC a picks_multiples (dedup por tipo de mercado)
    tipos = {_tipo_mercado_simple(p["pick"]) for p in picks_multiples}
    for dp in dc_picks:
        t = _tipo_mercado_simple(dp["pick"])
        if t not in tipos:
            picks_multiples.append(dp)
            tipos.add(t)

    # Cruzar/corregir el pick primario
    dc_prob_primary = _dc_prob_de_pick(primary["pick"], m, local, visitante)
    mejor = _mejor_pick_dc(dc_picks)
    if dc_prob_primary is not None and dc_prob_primary < 48 and mejor:
        ajuste_dc = (f"⚠️ Dixon-Coles corrige: '{primary['pick']}' solo {dc_prob_primary:.0f}% "
                     f"según el modelo → mejor: {mejor['pick']} ({mejor['confianza']:.0f}%)")
        primary = {"pick": mejor["pick"], "confianza": mejor["confianza"], "regla": "DC"}
    elif dc_prob_primary is not None:
        ajuste_dc = f"✅ Dixon-Coles coincide: {primary['pick']} ≈ {dc_prob_primary:.0f}% (modelo)"

    picks_multiples.sort(key=lambda x: (0 if x["pick"] == primary["pick"] else 1, -x["confianza"]))
    return primary, picks_multiples, ajuste_dc


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

    # ── Dixon-Coles PRE-cálculo (xG específico del enfrentamiento) ──────────
    # Se calcula ANTES de las reglas para que la Regla 4 (OVER/UNDER) use la
    # probabilidad ESPECÍFICA del partido (vía xG local+visita) y no solo la
    # frecuencia histórica cruda, que mezcla los entornos de ambos equipos y
    # produce sesgos (caso Portugal: UNDER 1.5 cuando en realidad metió 3, o
    # partidos cerrados marcados como de alta anotación). Se reutiliza más
    # abajo para nutrir picks múltiples y corregir el primario (sin recalcular).
    _dc_pre = None
    # Entorno de goles del torneo en curso (sube el xG si el Mundial es goleador
    # → reduce los UNDER espurios contra equipos goleadores). 1.0 si no es torneo.
    _gf_torneo = 1.0
    if es_torneo:
        try:
            from motors.wc_cerebro import factor_goles_torneo
            _gf_torneo = factor_goles_torneo()
        except Exception:
            _gf_torneo = 1.0
    try:
        from motors.dixon_coles import predecir as _dc_predecir
        _dc_tmp = _dc_predecir(local, visitante, neutral=bool(es_torneo), goles_factor=_gf_torneo)
        if _dc_tmp.get("disponible"):
            _dc_pre = _dc_tmp
    except Exception as _e:
        logger.debug(f"dixon_coles pre-cálculo no disponible {local} vs {visitante}: {_e}")
    _dc_mkt = (_dc_pre or {}).get("mercados", {})

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
    # Probabilidad histórica CRUDA: frecuencia de goles en los últimos 5 de
    # AMBOS equipos juntos. Mezcla los dos entornos → sesga el OVER al alza en
    # partidos que en realidad son cerrados (y a veces a la baja, como Portugal).
    p_o15_hist = _pct(todos_totales, lambda t: t > 1.5)
    p_o25_hist = _pct(todos_totales, lambda t: t > 2.5)
    p_o35_hist = _pct(todos_totales, lambda t: t >= 3.5)
    p_u25_hist = _pct(todos_totales, lambda t: t <= 2.5)

    # Mezcla con la probabilidad ESPECÍFICA del enfrentamiento (Dixon-Coles xG,
    # que ya combina fuerza estructural + forma reciente 2026). 60% DC / 40%
    # histórico cuando hay modelo; 100% histórico si no hay DC. Esto reubica el
    # OVER al nivel real del matchup en vez de la frecuencia cruda de cada equipo.
    _W_DC_OVER = 0.60

    def _mezcla_over(p_hist, clave_dc):
        dc_v = _dc_mkt.get(clave_dc)
        if dc_v is None:
            return p_hist
        return _W_DC_OVER * dc_v + (1 - _W_DC_OVER) * p_hist

    p_o15 = _mezcla_over(p_o15_hist, "over_1.5")
    p_o25 = _mezcla_over(p_o25_hist, "over_2.5")
    p_o35_raw = _mezcla_over(p_o35_hist, "over_3.5")
    p_under25 = _mezcla_over(p_u25_hist, "under_2.5")

    # OVER 2.5 se surte desde 52% (no 55%): el backtest WC out-of-sample mostró
    # que ya es +EV ahí (≥50%→59%, ≥58%→64% de acierto, breakeven -110 = 52.4%).
    # OVER 1.5 y 3.5 se mantienen en 55% (1.5 paga poco, 3.5 es ruidoso).
    _umbral_over = {"OVER 2.5": 52}
    for nombre, pr in (("OVER 1.5", p_o15), ("OVER 2.5", p_o25), ("OVER 3.5", p_o35_raw)):
        if pr >= _umbral_over.get(nombre, 55):
            viable_picks.append({"pick": nombre, "confianza": round(min(92, pr * factor_fase), 1), "regla": 4})
    # UNDER 2.5 — matchups DEFENSIVOS (ambos conceden/anotan poco). Detecta los
    # partidos cerrados (p.ej. Mexico 1-0 Korea) donde el OVER falla. Compite por
    # probabilidad como el resto: si el UNDER es más probable, gana la selección.
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
    # Reutiliza el UNDER ya mezclado con Dixon-Coles (no recalcula el crudo).
    if es_eliminacion:
        if p_under25 >= 60:
            viable_picks.append({
                "pick": "UNDER 2.5 (Eliminación directa)",
                "confianza": round(p_under25, 1),
                "regla": 6,
            })

    # ── Regla 7 — COMBINADO (gana + Over): mismatch claro. Dos sabores ──────
    # Exige favorito con ML ≥63%. Se ofrecen DOS combos según el perfil de riesgo:
    #   • VALOR  : Gana + Over 2.5/3.5 (Over ≥58%) → más pago, menos probable.
    #   • SEGURO : Gana + Over 1.5 (Over 1.5 ≥72%) → más probable, paga más que el
    #     moneyline solo. El backtest WC mostró que favoritos ML≥60% aciertan este
    #     combo 60-75% out-of-sample (es +EV; lo pidió el usuario).
    ml_pick = next((p for p in viable_picks if p["regla"] == 5 and p["confianza"] >= 63), None)
    if ml_pick and not es_eliminacion:
        equipo = ml_pick["pick"].split("(")[-1].rstrip(")") if "(" in ml_pick["pick"] else ml_pick["pick"]

        def _add_combo(over_nombre, over_prob, seguro=False):
            conf_combo = round(ml_pick["confianza"] / 100.0 * over_prob / 100.0 * 100)
            cuota_combo = round((100.0 / max(1, ml_pick["confianza"])) * (100.0 / max(1, over_prob)), 2)
            viable_picks.append({
                "pick": f"Gana {equipo} + {over_nombre}",
                "confianza": conf_combo, "regla": 7, "combo": True,
                "combo_seguro": seguro, "cuota": cuota_combo,
            })

        # VALOR: la línea de Over más alta que cumpla ≥58% (2.5 o 3.5)
        over_fuerte = [(nm, pr) for nm, pr in (("OVER 2.5", p_o25), ("OVER 3.5", p_o35_raw)) if pr >= 58]
        if over_fuerte:
            _add_combo(*over_fuerte[-1], seguro=False)
        # SEGURO: Gana + Over 1.5 cuando el Over 1.5 ya es ALTO (≥72%)
        if p_o15 >= 72:
            _add_combo("OVER 1.5", p_o15, seguro=True)

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
    ajuste_dc = ""
    try:
        # Reutiliza el pre-cálculo de Dixon-Coles (la matriz NO se recalcula).
        if _dc_pre is not None:
            marcador_correcto = _dc_pre
            # Nutre los picks con los mercados exactos de la matriz y corrige el
            # primario si el modelo lo contradice.
            primary, picks_multiples, ajuste_dc = _integrar_dixon_coles(
                marcador_correcto, local, visitante, primary, picks_multiples)
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
        "ajuste_dc": ajuste_dc,
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
        ml = {"local": _dc["prob"]["local"], "empate": _dc["prob"]["empate"],
              "visitante": _dc["prob"]["visitante"]}
        # Blend de mercado (Benter): modelo + cuotas de-vigueadas
        try:
            from motors.mercado_blend import blend_1x2
            benter = blend_1x2(ml, local, visitante)
        except Exception:
            benter = None
        return {
            "fuente": "dixon-coles",
            "xg_local": _dc["xg_local"], "xg_visitante": _dc["xg_visit"],
            "moneyline": ml,
            "over_under": {"over_2.5": _dc["over_under"]["over_2.5"],
                           "under_2.5": _dc["over_under"]["under_2.5"],
                           "over_1.5": _dc["over_under"]["over_1.5"]},
            "btts": _dc["btts"],
            "goleadores": goleadores,
            "benter": benter,
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
