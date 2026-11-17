"""Selección de referencia de 11 activos por reglas, según el coeficiente de aversión al riesgo A.

No hay listas fijas: la selección se **recalcula con los datos** del catálogo, así que se adapta si
el comportamiento de los activos cambia. A puede ser cualquier valor (se acota a [a_min, a_max]).

Regla (ver docs/taller-1/03-motor-financiero.md §11):

1. **Elegibles:** activos con historia suficiente (≥ `min_dias`) y que no sean apalancados/inversos
   (ETF 2x, 3x, "Ultra", "Bull", "Bear"): su retorno histórico no es representativo.
2. **Puntaje** = `w·pct(retorno) + (1−w)·pct(−volatilidad)`, con `w = (a_max − A)/(a_max − a_min)`.
   `pct` es el percentil del activo entre los elegibles. A baja (poca aversión) → `w`→1: se
   prioriza el retorno histórico; A alta → `w`→0: se prioriza la baja volatilidad.
3. **Diversificación:** se toma el mejor activo de cada una de las `n_clases` mejores clases de
   activo (acciones EE.UU., renta fija IG, REIT, cripto…) y el resto de cupos se llena con los
   activos de mejor puntaje, con un máximo de `max_por_clase` por clase.

Es una sugerencia de partida: el usuario puede modificarla antes de optimizar.
"""

import re

import pandas as pd

from roboadvisor.taller1.config import ParametrosFinancieros
from roboadvisor.taller1.core.retornos import DIAS_ANIO

APALANCADO = re.compile(r"\b[23]x\b|\bultra(pro)?\b|\bbull\b|\bbear\b|\binverse\b", re.IGNORECASE)


def es_apalancado(nombre: str) -> bool:
    """ETF apalancado o inverso, detectado por su nombre (p. ej. "UltraPro QQQ (3x Nasdaq)")."""
    return bool(APALANCADO.search(nombre))


def estadisticas_activos(precios: pd.DataFrame, ventana_dias: int) -> pd.DataFrame:
    """Retorno medio anual, volatilidad anual y nº de retornos de cada activo (su propia historia).

    `precios`: `DataFrame[fecha × ticker]`. Usa los últimos `ventana_dias` retornos diarios.
    """
    retornos = precios.sort_index().pct_change().tail(ventana_dias)
    return pd.DataFrame(
        {
            "mu": retornos.mean() * DIAS_ANIO,
            "sigma": retornos.std() * DIAS_ANIO**0.5,
            "n": retornos.notna().sum(),
        }
    )


def peso_retorno(a: float, params: ParametrosFinancieros) -> float:
    """`w` ∈ [0, 1]: importancia del retorno frente a la baja volatilidad (1 con A mínima)."""
    a = min(max(a, params.a_min), params.a_max)
    return (params.a_max - a) / (params.a_max - params.a_min)


def seleccion_referencia(
    a: float, candidatos: pd.DataFrame, params: ParametrosFinancieros | None = None
) -> list[str]:
    """Tickers sugeridos (hasta `n_seleccion`) para un A dado.

    `candidatos`: índice = ticker; columnas `clase`, `nombre`, `mu`, `sigma`, `n`.
    """
    params = params or ParametrosFinancieros()
    c = candidatos[
        (candidatos["n"] >= params.min_dias) & ~candidatos["nombre"].map(es_apalancado)
    ].copy()
    if c.empty:
        return []
    w = peso_retorno(a, params)
    c["puntaje"] = w * c["mu"].rank(pct=True) + (1 - w) * (-c["sigma"]).rank(pct=True)
    c = c.sort_values(["puntaje", "mu"], ascending=False)

    mejor_por_clase = c.groupby("clase").head(1)
    elegidos = list(mejor_por_clase.head(params.sel_n_clases).index)
    for ticker, fila in c.drop(index=elegidos).iterrows():
        if len(elegidos) >= params.n_seleccion:
            break
        en_clase = sum(c.at[e, "clase"] == fila["clase"] for e in elegidos)
        if en_clase < params.sel_max_por_clase:
            elegidos.append(ticker)
    return elegidos
