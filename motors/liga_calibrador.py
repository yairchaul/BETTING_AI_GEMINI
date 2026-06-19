# -*- coding: utf-8 -*-
"""
CALIBRADOR POR LIGA/COMPETICIÓN — Ajusta las confianzas del motor según
las tasas históricas reales de cada competición.

Fuente internacional: martj42/international_results (49K partidos)
Fuente clubes: estimaciones basadas en fuentes públicas (Understat, FBREF, etc.)

Tasas históricas verificadas:
  Bundesliga:         avg 3.28 goles | O1.5=85% | O2.5=64% | BTTS=54%
  Premier League:     avg 2.75 goles | O1.5=76% | O2.5=52% | BTTS=51%
  La Liga:            avg 2.63 goles | O1.5=74% | O2.5=48% | BTTS=47%
  Serie A:            avg 2.54 goles | O1.5=72% | O2.5=45% | BTTS=46%
  Ligue 1:            avg 2.65 goles | O1.5=74% | O2.5=48% | BTTS=47%
  Copa Libertadores:  avg 2.12 goles | O1.5=64% | O2.5=34% | BTTS=41%
  Copa Sudamericana:  avg 2.06 goles | O1.5=63% | O2.5=32% | BTTS=39%
  MLS:                avg 2.96 goles | O1.5=76% | O2.5=55% | BTTS=49%
  Liga MX:            avg 2.64 goles | O1.5=73% | O2.5=47% | BTTS=46%
  Champions League:   avg 2.80 goles | O1.5=75% | O2.5=52% | BTTS=50%
  UEFA Euro:          avg 2.44 goles | O1.5=72% | O2.5=45% | BTTS=49%
  FIFA World Cup:     avg 2.83 goles | O1.5=73% | O2.5=52% | BTTS=51%
  Copa América:       avg 3.14 goles | O1.5=76% | O2.5=57% | BTTS=48%
"""
import unicodedata

# ── Tasas históricas por competición ─────────────────────────────────────────
# keys: o15 (Over 1.5%), o25 (Over 2.5%), o35 (Over 3.5%), btts, avg_goles
_RATES: dict = {
    # ── Europa (clubes) ───────────────────────────────────────────────────────
    "bundesliga":            {"o15": 85, "o25": 64, "o35": 36, "btts": 54, "avg": 3.28},
    "premier league":        {"o15": 76, "o25": 52, "o35": 28, "btts": 51, "avg": 2.75},
    "la liga":               {"o15": 74, "o25": 48, "o35": 24, "btts": 47, "avg": 2.63},
    "serie a":               {"o15": 72, "o25": 45, "o35": 22, "btts": 46, "avg": 2.54},
    "ligue 1":               {"o15": 74, "o25": 48, "o35": 24, "btts": 47, "avg": 2.65},
    "eredivisie":            {"o15": 82, "o25": 61, "o35": 34, "btts": 54, "avg": 3.17},
    "primeira liga":         {"o15": 74, "o25": 49, "o35": 26, "btts": 48, "avg": 2.68},
    "championship":          {"o15": 77, "o25": 53, "o35": 28, "btts": 50, "avg": 2.81},
    "super lig":             {"o15": 73, "o25": 48, "o35": 25, "btts": 47, "avg": 2.62},
    # ── Europa (copas) ────────────────────────────────────────────────────────
    "uefa champions league": {"o15": 75, "o25": 52, "o35": 30, "btts": 50, "avg": 2.80},
    "uefa europa league":    {"o15": 74, "o25": 50, "o35": 27, "btts": 49, "avg": 2.73},
    "uefa conference league":{"o15": 74, "o25": 50, "o35": 27, "btts": 49, "avg": 2.71},
    "champions league":      {"o15": 75, "o25": 52, "o35": 30, "btts": 50, "avg": 2.80},
    "europa league":         {"o15": 74, "o25": 50, "o35": 27, "btts": 49, "avg": 2.73},
    # ── Sudamérica (clubes) ───────────────────────────────────────────────────
    "copa libertadores":     {"o15": 64, "o25": 34, "o35": 14, "btts": 41, "avg": 2.12},
    "copa sudamericana":     {"o15": 63, "o25": 32, "o35": 13, "btts": 39, "avg": 2.06},
    "libertadores":          {"o15": 64, "o25": 34, "o35": 14, "btts": 41, "avg": 2.12},
    "sudamericana":          {"o15": 63, "o25": 32, "o35": 13, "btts": 39, "avg": 2.06},
    "brasileiro":            {"o15": 70, "o25": 44, "o35": 21, "btts": 44, "avg": 2.42},
    "serie a brasile":       {"o15": 70, "o25": 44, "o35": 21, "btts": 44, "avg": 2.42},
    "liga profesional":      {"o15": 68, "o25": 42, "o35": 19, "btts": 43, "avg": 2.35},
    "primera division":      {"o15": 68, "o25": 42, "o35": 19, "btts": 43, "avg": 2.35},
    # ── Norteamérica ─────────────────────────────────────────────────────────
    "mls":                   {"o15": 76, "o25": 55, "o35": 30, "btts": 49, "avg": 2.96},
    "liga mx":               {"o15": 73, "o25": 47, "o35": 23, "btts": 46, "avg": 2.64},
    "liga de expansión mx":  {"o15": 71, "o25": 45, "o35": 21, "btts": 45, "avg": 2.55},
    # ── Internacional (selecciones) ───────────────────────────────────────────
    "fifa world cup":        {"o15": 73, "o25": 52, "o35": 31, "btts": 51, "avg": 2.83},
    "world cup":             {"o15": 73, "o25": 52, "o35": 31, "btts": 51, "avg": 2.83},
    "mundial":               {"o15": 73, "o25": 52, "o35": 31, "btts": 51, "avg": 2.83},
    "copa america":          {"o15": 76, "o25": 57, "o35": 38, "btts": 48, "avg": 3.14},
    "uefa euro":             {"o15": 72, "o25": 45, "o35": 19, "btts": 49, "avg": 2.44},
    "euro":                  {"o15": 72, "o25": 45, "o35": 19, "btts": 49, "avg": 2.44},
    "african cup of nations":{"o15": 67, "o25": 43, "o35": 22, "btts": 46, "avg": 2.38},
    "afcon":                 {"o15": 67, "o25": 43, "o35": 22, "btts": 46, "avg": 2.38},
    "concacaf":              {"o15": 76, "o25": 54, "o35": 31, "btts": 46, "avg": 2.90},
    "gold cup":              {"o15": 74, "o25": 49, "o35": 31, "btts": 45, "avg": 2.81},
    "nations league":        {"o15": 71, "o25": 45, "o35": 24, "btts": 45, "avg": 2.51},
    "afc asian cup":         {"o15": 73, "o25": 48, "o35": 29, "btts": 46, "avg": 2.66},
    # ── Default (ligas no identificadas) ─────────────────────────────────────
    "_default":              {"o15": 72, "o25": 48, "o35": 25, "btts": 47, "avg": 2.65},
}

# Umbrales mínimos de confianza del MOTOR para proponer cada mercado en cada liga.
# Si el motor dice "OVER 3.5" pero la liga tiene O3.5=13%, necesitamos >=70% del motor.
_MIN_CONF_FOR_MARKET = {
    # (o35_rate) → min motor confidence para proponer Over 3.5
    "over_3.5": lambda rates: 70 if rates["o35"] < 25 else 65 if rates["o35"] < 30 else 60,
    # (o25_rate) → min motor confidence para proponer Over 2.5
    "over_2.5": lambda rates: 65 if rates["o25"] < 38 else 60,
    # btts → min confidence cuando btts rate es bajo
    "btts":     lambda rates: 70 if rates["btts"] < 43 else 65,
}


def _norm(s: str) -> str:
    t = unicodedata.normalize("NFD", (s or "").strip()).encode("ascii", "ignore").decode()
    return t.lower()


def get_rates(liga: str) -> dict:
    """Devuelve las tasas históricas para la liga/competición dada."""
    nl = _norm(liga)
    # Búsqueda exacta primero
    if nl in _RATES:
        return _RATES[nl]
    # Búsqueda parcial (la liga contiene el key, o el key está en la liga)
    for key, rates in _RATES.items():
        if key == "_default":
            continue
        if key in nl or nl in key:
            return rates
    return _RATES["_default"]


def calibrar_pick(pick: str, confianza: float, liga: str) -> tuple[float, str]:
    """
    Ajusta la confianza de un pick según las tasas históricas de la liga.
    Devuelve (confianza_nueva, nota_calibracion).

    Reglas:
      1. Si propone Over 3.5 pero la liga tiene tasa baja → penalizar fuerte / bloquear
      2. Si propone Over 2.5 en liga defensiva → bajar línea a Over 1.5
      3. Si propone BTTS en liga con baja tasa → penalizar
      4. Si propone Over 1.5 en liga de alta anotación → ligero boost
    """
    rates = get_rates(liga)
    p = pick.lower()
    nota = ""

    # ── OVER 3.5: muy raro en la mayoría de ligas ─────────────────────────────
    if "over 3.5" in p or ("over 3" in p and "5" in p):
        min_conf = _MIN_CONF_FOR_MARKET["over_3.5"](rates)
        if confianza < min_conf:
            # Degradar a Over 2.5 si la tasa de O2.5 es alta, si no → Over 1.5
            if rates["o25"] >= 48:
                nueva_pick = "OVER 2.5 goles"
                nueva_conf = round(rates["o25"] * 0.85, 1)
                nota = (f"Liga {liga}: Over 3.5 real {rates['o35']}% "
                        f"(motor {confianza:.0f}% < mínimo {min_conf}%) → degradado a Over 2.5")
            else:
                nueva_pick = "OVER 1.5 goles"
                nueva_conf = round(rates["o15"] * 0.85, 1)
                nota = (f"Liga {liga}: Over 3.5 real {rates['o35']}% → degradado a Over 1.5")
            return nueva_conf, nota + f" | PICK CAMBIADO: {nueva_pick}"
        # Si tiene confianza suficiente, ajustar leve
        nueva_conf = round(confianza * (rates["o35"] / 30.0), 1)
        return min(88, max(50, nueva_conf)), ""

    # ── OVER 2.5: cuidado en ligas defensivas ─────────────────────────────────
    if "over 2.5" in p:
        min_conf = _MIN_CONF_FOR_MARKET["over_2.5"](rates)
        if confianza < min_conf:
            # Liga defensiva: bajar a Over 1.5
            nueva_conf = round(rates["o15"] * 0.85, 1)
            nota = (f"Liga {liga}: Over 2.5 real {rates['o25']}% "
                    f"(motor {confianza:.0f}% < mínimo {min_conf}%) → degradado a Over 1.5")
            return nueva_conf, nota + " | PICK CAMBIADO: OVER 1.5 goles"
        # Ajuste proporcional
        factor = rates["o25"] / 52.0  # 52% es la referencia WC
        return round(min(88, max(50, confianza * factor)), 1), ""

    # ── OVER 1.5: ajuste por liga ─────────────────────────────────────────────
    if "over 1.5" in p:
        factor = rates["o15"] / 73.0  # 73% referencia WC
        nueva_conf = round(min(88, max(50, confianza * factor)), 1)
        if abs(nueva_conf - confianza) > 3:
            nota = f"Liga {liga}: Over 1.5 real {rates['o15']}% → conf ajustada {confianza:.0f}%→{nueva_conf:.0f}%"
        return nueva_conf, nota

    # ── BTTS ──────────────────────────────────────────────────────────────────
    if "btts" in p or "ambos anotan" in p:
        min_conf = _MIN_CONF_FOR_MARKET["btts"](rates)
        factor = rates["btts"] / 51.0  # 51% referencia WC
        nueva_conf = round(confianza * factor, 1)
        if nueva_conf < min_conf:
            # BTTS es muy arriesgado en esta liga → penalizar al umbral
            nueva_conf = min_conf - 5  # justo por debajo del threshold para que no se proponga
            nota = (f"Liga {liga}: BTTS real {rates['btts']}% "
                    f"(penal de confianza {confianza:.0f}%→{nueva_conf:.0f}%)")
        return round(min(88, max(30, nueva_conf)), 1), nota

    return confianza, ""


def pick_alternativo(pick: str, liga: str) -> str:
    """Si el pick fue degradado, devuelve el pick alternativo sugerido."""
    _, nota = calibrar_pick(pick, 55.0, liga)  # usar 55% como referencia
    if "PICK CAMBIADO:" in nota:
        return nota.split("PICK CAMBIADO:")[-1].strip()
    return pick


def resumen_liga(liga: str) -> str:
    """Texto de las tasas de la liga para mostrar en UI."""
    rates = get_rates(liga)
    return (
        f"{liga}: Over 1.5={rates['o15']}% · Over 2.5={rates['o25']}% · "
        f"Over 3.5={rates['o35']}% · BTTS={rates['btts']}% · avg {rates['avg']} goles"
    )
