# -*- coding: utf-8 -*-
"""
MERCADO BLEND — combina la probabilidad del MODELO con la del MERCADO de apuestas
(estilo William Benter). El mercado (cuotas de varias casas, de-vigueadas) es un
prior muy bien calibrado que contiene información que el modelo NO ve: rotaciones,
lesiones de último momento, sentido de urgencia. Mezclar ambos corrige la
sobre-confianza del modelo (nuestro backtest mostró que en el extremo alto el
modelo exagera: OVER 2.5 ≥65% solo pegó 40%).

    P_final = renormalizar( w_model · P_modelo + (1 − w_model) · P_mercado )

Sin dependencias nuevas (solo json/os). Fuente de cuotas: data/odds_api_cache.json
(The Odds API). Devuelve None si no hay cuotas para el partido → el motor sigue
con su probabilidad pura, sin romperse.
"""
import os
import json
import unicodedata
import logging

logger = logging.getLogger(__name__)

_ODDS_CACHE = os.path.join("data", "odds_api_cache.json")
W_MODEL_DEFAULT = 0.55   # peso del modelo; el resto al mercado (Benter da peso real a ambos)


def _norm(s: str) -> str:
    t = unicodedata.normalize("NFD", (s or "")).encode("ascii", "ignore").decode()
    return t.lower().replace(".", "").replace("-", " ").strip()


def _american_to_prob(price) -> float:
    """Momio americano → probabilidad implícita (con vig)."""
    try:
        p = float(price)
    except (TypeError, ValueError):
        return 0.0
    if p < 0:
        return (-p) / ((-p) + 100.0)
    return 100.0 / (p + 100.0)


def _mediana(xs):
    s = sorted(xs)
    n = len(s)
    if not n:
        return None
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2.0


def _juegos_odds(sport_key="soccer_fifa_world_cup"):
    try:
        with open(_ODDS_CACHE, encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        return []
    nodo = d.get(sport_key)
    if isinstance(nodo, dict):
        return nodo.get("data") or nodo.get("juegos") or []
    return nodo or []


def cuotas_1x2(local: str, visitante: str, sport_key="soccer_fifa_world_cup"):
    """Prob 1X2 IMPLÍCITA del mercado, de-vigueada y como mediana entre casas.
    Devuelve {'local','empate','visitante'} en % y 'n_casas', o None si no hay
    cuotas para el partido."""
    nl, nv = _norm(local), _norm(visitante)
    juego = None
    for g in _juegos_odds(sport_key):
        h, a = _norm(g.get("home_team", "")), _norm(g.get("away_team", ""))
        if (nl in h or h in nl or nl in a or a in nl) and (nv in h or h in nv or nv in a or a in nv):
            juego = g
            break
    if not juego:
        return None

    home_raw = _norm(juego.get("home_team", ""))
    # ¿el 'local' del análisis es el home del mercado?
    local_es_home = nl in home_raw or home_raw in nl

    pl_list, pe_list, pv_list = [], [], []
    for bk in juego.get("bookmakers", []):
        for m in bk.get("markets", []):
            if m.get("key") != "h2h":
                continue
            imp = {"home": None, "away": None, "draw": None}
            for o in m.get("outcomes", []):
                nm = _norm(o.get("name", ""))
                price = o.get("price")
                if "draw" in nm or "empate" in nm:
                    imp["draw"] = _american_to_prob(price)
                elif nm in home_raw or home_raw in nm:
                    imp["home"] = _american_to_prob(price)
                else:
                    imp["away"] = _american_to_prob(price)
            if None in imp.values():
                continue
            total = imp["home"] + imp["away"] + imp["draw"]  # overround
            if total <= 0:
                continue
            # de-vig (normalizar a 1)
            h_dv, a_dv, d_dv = imp["home"] / total, imp["away"] / total, imp["draw"] / total
            if local_es_home:
                pl_list.append(h_dv); pv_list.append(a_dv)
            else:
                pl_list.append(a_dv); pv_list.append(h_dv)
            pe_list.append(d_dv)

    if not pl_list:
        return None
    return {
        "local": round(_mediana(pl_list) * 100, 1),
        "empate": round(_mediana(pe_list) * 100, 1),
        "visitante": round(_mediana(pv_list) * 100, 1),
        "n_casas": len(pl_list),
    }


def cuotas_2via(equipo_a: str, equipo_b: str, sport_key: str):
    """h2h de 2 vías (sin empate) DE-VIGUEADO, mediana entre casas. Para el money
    line de MLB (baseball_mlb) y el ganador de UFC (mma_mixed_martial_arts).
    Devuelve {'a','b','n_casas'} con a=equipo_a, b=equipo_b en %, o None."""
    na, nb = _norm(equipo_a), _norm(equipo_b)
    juego = None
    for g in _juegos_odds(sport_key):
        h, aw = _norm(g.get("home_team", "")), _norm(g.get("away_team", ""))
        if ((na in h or h in na or na in aw or aw in na)
                and (nb in h or h in nb or nb in aw or aw in nb)):
            juego = g
            break
    if not juego:
        return None
    pa, pb = [], []
    for bk in juego.get("bookmakers", []):
        for m in bk.get("markets", []):
            if m.get("key") != "h2h":
                continue
            ia = ib = None
            for o in m.get("outcomes", []):
                nm = _norm(o.get("name", ""))
                if na in nm or nm in na:
                    ia = _american_to_prob(o.get("price"))
                elif nb in nm or nm in nb:
                    ib = _american_to_prob(o.get("price"))
            if ia is None or ib is None:
                continue
            tot = ia + ib
            if tot <= 0:
                continue
            pa.append(ia / tot); pb.append(ib / tot)   # de-vig
    if not pa:
        return None
    return {"a": round(_mediana(pa) * 100, 1), "b": round(_mediana(pb) * 100, 1), "n_casas": len(pa)}


def blend_2via(p_model_a, equipo_a: str, equipo_b: str, sport_key: str,
               w_model: float = W_MODEL_DEFAULT):
    """Benter de 2 vías: combina la prob del MODELO de que gane equipo_a (%) con
    la del MERCADO. Devuelve {'modelo','mercado','blend','blend_b','nota'} o blend
    None si no hay cuotas. Sirve para MLB money line y UFC ganador."""
    mkt = cuotas_2via(equipo_a, equipo_b, sport_key)
    pm = float(p_model_a or 0)
    if not mkt:
        return {"modelo": round(pm, 1), "mercado": None, "blend": None, "blend_b": None,
                "nota": "Sin cuotas de mercado para este evento (solo modelo)."}
    w = max(0.0, min(1.0, float(w_model)))
    ba = w * pm + (1 - w) * mkt["a"]
    bb = w * (100 - pm) + (1 - w) * mkt["b"]
    s = ba + bb or 1.0
    blend_a = round(ba / s * 100, 1)
    dif = abs(pm - mkt["a"])
    if dif >= 12:
        nota = (f"⚠️ Modelo {pm:.0f}% vs mercado {mkt['a']:.0f}% ({dif:.0f}pts): el mercado "
                f"puede saber algo (lesión, alineación). Benter → {blend_a:.0f}%.")
    else:
        nota = f"Mercado ≈ modelo. Benter ({int(w*100)}/{int((1-w)*100)}) → {blend_a:.0f}%."
    return {"modelo": round(pm, 1), "mercado": mkt, "blend": blend_a,
            "blend_b": round(100 - blend_a, 1), "nota": nota, "n_casas": mkt["n_casas"]}


def blend_1x2(model_1x2: dict, local: str, visitante: str, w_model: float = W_MODEL_DEFAULT):
    """Mezcla el 1X2 del modelo con el del mercado (Benter). Devuelve dict con
    'modelo', 'mercado', 'blend' (todos {local,empate,visitante}) y 'nota'. Si no
    hay cuotas, 'mercado'/'blend' son None y 'nota' lo indica."""
    mkt = cuotas_1x2(local, visitante)
    if not mkt:
        return {"modelo": model_1x2, "mercado": None, "blend": None,
                "nota": "Sin cuotas de mercado para este partido (solo modelo)."}

    w = max(0.0, min(1.0, float(w_model)))
    out = {}
    for k in ("local", "empate", "visitante"):
        m = float(model_1x2.get(k, 0) or 0)
        q = float(mkt.get(k, 0) or 0)
        out[k] = w * m + (1 - w) * q
    s = sum(out.values()) or 1.0
    blend = {k: round(v / s * 100, 1) for k, v in out.items()}

    # Nota: ¿modelo y mercado discrepan fuerte? (señal de rotación/lesión)
    fav_modelo = max(("local", "empate", "visitante"), key=lambda k: model_1x2.get(k, 0))
    dif = abs(float(model_1x2.get(fav_modelo, 0)) - float(mkt.get(fav_modelo, 0)))
    if dif >= 15:
        nota = (f"⚠️ Modelo y mercado discrepan {dif:.0f}pts en {fav_modelo}: el mercado puede "
                f"saber algo (rotación/lesión). Benter → {blend[fav_modelo]:.0f}%.")
    else:
        nota = f"Mercado ≈ modelo. Benter ({int(w*100)}% modelo / {int((1-w)*100)}% mercado) aplicado."
    return {"modelo": model_1x2, "mercado": mkt, "blend": blend, "nota": nota, "n_casas": mkt["n_casas"]}
