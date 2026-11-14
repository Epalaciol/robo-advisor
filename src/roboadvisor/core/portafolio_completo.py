"""Portafolio completo: combinación del tangente con el activo libre de riesgo.

Ver docs/03-motor-financiero.md §5. Sin apalancamiento: `y*` se recorta a `[0, 1]`.
"""

from dataclasses import dataclass

import pandas as pd

from roboadvisor.core.markowitz import Portafolio
from roboadvisor.core.utilidad import utilidad


@dataclass(frozen=True)
class PortafolioCompleto:
    """Portafolio completo para un coeficiente de aversión `A` dado."""

    y: float
    peso_rf: float
    pesos_riesgo: pd.Series
    pesos_completo: pd.Series
    retorno: float
    sigma: float
    utilidad: float
    apalancamiento_requerido: bool


def y_star(er_p: float, sigma_p: float, rf: float, a: float) -> tuple[float, float]:
    """`y* = (E(R_p) − rf) / (A·σ_p²)`, recortado a `[0, 1]` (sin apalancamiento).

    Devuelve `(y_sin_recorte, y)`.
    """
    y_sin_recorte = (er_p - rf) / (a * sigma_p**2)
    y = min(max(y_sin_recorte, 0.0), 1.0)
    return y_sin_recorte, y


def componer(port_riesgo: Portafolio, rf: float, a: float) -> PortafolioCompleto:
    """Combina el portafolio de riesgo con el activo libre de riesgo según `y*`.

    `E(R_c) = rf + y*(E(R_p) − rf)`, `σ_c = y*·σ_p`, `U_c = E(R_c) − ½A·σ_c²`.
    """
    y_sin_recorte, y = y_star(port_riesgo.retorno, port_riesgo.sigma, rf, a)

    retorno = rf + y * (port_riesgo.retorno - rf)
    sigma = y * port_riesgo.sigma
    u = utilidad(retorno, sigma, a)

    return PortafolioCompleto(
        y=y,
        peso_rf=1 - y,
        pesos_riesgo=port_riesgo.w,
        pesos_completo=y * port_riesgo.w,
        retorno=retorno,
        sigma=sigma,
        utilidad=u,
        apalancamiento_requerido=y_sin_recorte > 1,
    )


def escenarios_por_a(port_riesgo: Portafolio, rf: float, valores_a: list[float]) -> pd.DataFrame:
    """Cómo quedaría el mismo portafolio de riesgo con distintos `A`.

    Una fila por `A`: `y*` sin recorte y recortado, % en libre de riesgo, retorno, σ,
    utilidad y si se requeriría apalancamiento. Todos los puntos caen sobre la CAL.
    """
    filas = []
    for a in valores_a:
        c = componer(port_riesgo, rf, a)
        y_sin_recorte, _ = y_star(port_riesgo.retorno, port_riesgo.sigma, rf, a)
        filas.append(
            {
                "a": a,
                "y_sin_recorte": y_sin_recorte,
                "y": c.y,
                "peso_rf": c.peso_rf,
                "retorno": c.retorno,
                "sigma": c.sigma,
                "utilidad": c.utilidad,
                "apalancamiento_requerido": c.apalancamiento_requerido,
            }
        )
    return pd.DataFrame(filas)
