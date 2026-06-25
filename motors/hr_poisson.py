# -*- coding: utf-8 -*-
"""
NÚCLEO POISSON DE HOME RUNS — probabilidad calibrada de que un bateador pegue
al menos 1 HR en el juego.

Mismo enfoque que el modelo de fútbol (Dixon-Coles): modelar el evento como un
proceso de Poisson y reportar P(≥1) = 1 − e^(−λ), que se topa SOLO en valores
realistas en vez de inflarse al 95%.

    λ_HR = tasa_HR_por_juego  ×  factor_pitcher  ×  factor_parque  ×  factor_mano
    P(≥1 HR) = 1 − e^(−λ_HR)

Decisiones de calibración (validadas con motors.hr_backtester):
  • SHRINKAGE bayesiano de la tasa hacia la media de un bateador de poder: una
    racha corta (3 HR en 8 juegos) NO vale lo mismo que 24 HR en 72. Regresa a la
    media los tamaños de muestra chicos.
  • Factores ACOTADOS y suaves — el backtest mostró que el modelo viejo inflaba
    ~1.5× (el tramo "30%+" pegaba sólo 19% real). Los rangos de aquí evitan eso.
  • SIN doble conteo de OPS (ya está correlacionado con la tasa de HR) y SIN
    supersticiones (día de la semana, etc.).
  • Tope realista: ni el mejor bateador del mundo pasa de ~25% por juego.
"""
import math

LIGA_HR9 = 1.20      # HR/9 permitidos, media de liga (referencia del factor pitcher)
LIGA_HPG = 0.10      # HR/juego de un bateador de poder "promedio" (ancla del shrinkage)
PRIOR_JUEGOS = 30    # fuerza del shrinkage (≈ juegos de "prior")
TOPE_PROB = 25.0     # ningún bateador supera ~25% de pegar HR en un juego


def factor_pitcher(hr9):
    """Vulnerabilidad del abridor rival. Acotado y suave."""
    if not hr9 or hr9 <= 0:
        return 1.0
    return max(0.80, min(1.30, float(hr9) / LIGA_HR9))


def factor_parque(park_factor):
    """Factor de HR del estadio, acotado."""
    pf = park_factor if park_factor and park_factor > 0 else 1.0
    return max(0.88, min(1.15, float(pf)))


def factor_clima(clima):
    """Ajuste por clima sobre λ_HR. El aire CALIENTE es menos denso y la bola
    viaja más; el viento SALIENDO (Out) la empuja fuera y ENTRANDO (In) la frena.
    Acotado y suave, como los demás factores. No-op si no hay datos de clima.

    clima: dict con 'temp' (°F), 'wind_speed' (mph), 'wind_dir' ('Out'/'In'/'None').
    """
    if not clima or not isinstance(clima, dict):
        return 1.0
    f = 1.0
    # Temperatura: ~+0.6%/°F sobre 70 (referencia documentada ~1%/°F, lo dejamos
    # conservador y acotado a [-10%, +12%]).
    temp = clima.get("temp")
    if temp is not None:
        try:
            f *= max(0.90, min(1.12, 1.0 + (float(temp) - 70.0) * 0.006))
        except (TypeError, ValueError):
            pass
    # Viento: ~1% por mph en la dirección correspondiente, acotado.
    try:
        wind = float(clima.get("wind_speed") or 0)
    except (TypeError, ValueError):
        wind = 0.0
    wdir = str(clima.get("wind_dir", "None")).lower()
    if "out" in wdir:
        f *= min(1.18, 1.0 + wind * 0.010)
    elif "in" in wdir:
        f *= max(0.85, 1.0 - wind * 0.010)
    return max(0.82, min(1.22, f))


def factor_mano(mano_pitcher, mano_bateador=None):
    """Ventaja de plato. Si conocemos ambas manos, premia el cruce opuesto; si no,
    un abridor zurdo da una ventaja global leve (hay más bateadores diestros)."""
    mp = (mano_pitcher or "R").upper()[:1]
    mb = (mano_bateador or "").upper()[:1] if mano_bateador else None
    if mb:
        return 1.07 if mb != mp else 0.95   # opuesto favorece; mismo lado penaliza leve
    return 1.05 if mp == "L" else 1.0


def tasa_shrunk(hr_por_juego, hr_total=0, juegos=0):
    """Tasa de HR/juego regresada a la media (shrinkage por tamaño de muestra)."""
    hpg = hr_por_juego if (hr_por_juego and hr_por_juego > 0) else None
    if hpg is None and juegos:
        hpg = hr_total / max(juegos, 1)
    if hpg is None:
        hpg = LIGA_HPG
    # Estimar nº de juegos si no viene (de hr_total y hpg)
    if not juegos or juegos <= 0:
        juegos = int(round(hr_total / hpg)) if (hr_total and hpg > 0) else 0
    if juegos and juegos > 0:
        hpg = (hpg * juegos + LIGA_HPG * PRIOR_JUEGOS) / (juegos + PRIOR_JUEGOS)
    return hpg


def factor_fatiga(fatiga):
    """Acota el factor de fatiga del equipo (de motors.mlb_fatiga). Solo reduce o
    es neutro. Acepta el float ya calculado; None/0 → 1.0 (sin efecto)."""
    if not fatiga:
        return 1.0
    try:
        return max(0.85, min(1.0, float(fatiga)))
    except (TypeError, ValueError):
        return 1.0


def prob_hr(hr_por_juego, hr_total=0, juegos=0, pitcher_hr9=None,
            park_factor=1.0, mano_pitcher="R", mano_bateador=None, ops=None,
            clima=None, fatiga=None):
    """Probabilidad calibrada (%) de que el bateador pegue ≥1 HR en el juego."""
    hpg = tasa_shrunk(hr_por_juego, hr_total, juegos)
    lam = (hpg
           * factor_pitcher(pitcher_hr9)
           * factor_parque(park_factor)
           * factor_mano(mano_pitcher, mano_bateador)
           * factor_clima(clima)
           * factor_fatiga(fatiga))
    # Ajuste MUY leve por OPS de élite (acotado; no doble-cuenta el grueso)
    if ops and ops > 0.90:
        lam *= 1.0 + min(0.10, (ops - 0.90) * 0.5)
    p = (1 - math.exp(-lam)) * 100
    return round(min(TOPE_PROB, p), 1)


def lambda_hr(hr_por_juego, hr_total=0, juegos=0, pitcher_hr9=None,
              park_factor=1.0, mano_pitcher="R", mano_bateador=None, ops=None,
              clima=None, fatiga=None):
    """λ_HR esperado (HR esperados del bateador en el juego), por si se quiere el
    valor continuo en vez de la probabilidad."""
    hpg = tasa_shrunk(hr_por_juego, hr_total, juegos)
    lam = (hpg * factor_pitcher(pitcher_hr9) * factor_parque(park_factor)
           * factor_mano(mano_pitcher, mano_bateador) * factor_clima(clima)
           * factor_fatiga(fatiga))
    if ops and ops > 0.90:
        lam *= 1.0 + min(0.10, (ops - 0.90) * 0.5)
    return lam
