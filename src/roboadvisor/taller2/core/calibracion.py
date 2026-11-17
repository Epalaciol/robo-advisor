"""Estimación de β0, β1, β2 (equivale al Solver del Excel del profesor).

Minimiza SSE = Σ (P_sucio − P_est)² cambiando β0, β1, β2 (sin restricción de signo), τ fijo.
Se prueban varios puntos de partida y se queda el de menor SSE.
Variante "duracion": cada residuo se divide por P·D* (≈ error en tasa); el SSE reportado
sigue siendo el de precios, para poder compararlo.
"""

from collections.abc import Sequence

import numpy as np
from scipy.optimize import least_squares

from .modelos import Betas, Calibracion, Flujos, Papel
from .nelson_siegel import precio, spot
from .rendimientos import duracion_modificada, tir


def _peso_duracion(f: Flujos, p: float) -> float:
    """1 / (P · D*) con la TIR observada: convierte el error de precio en error de tasa."""
    y = tir(p, f)
    return 1.0 / (p * max(duracion_modificada(y, f), 1e-3))


def sse(papeles: Sequence[tuple[Papel, Flujos]], betas: Betas, tau: float) -> float:
    return float(sum((p.precio_sucio - precio(f, betas, tau)) ** 2 for p, f in papeles))


def calibrar(
    papeles: Sequence[tuple[Papel, Flujos]],
    tau: float = 3.7,
    arranques: Sequence[tuple[float, float, float]] = ((0.13, -0.01, 0.0),),
    ponderacion: str = "ninguna",
    usar_origen: str = "todos",
) -> Calibracion:
    """Calibra la curva del día. `papeles` = pares (Papel, Flujos) a la fecha de valoración."""
    usados = [(p, f) for p, f in papeles if usar_origen == "todos" or p.origen_tasa == usar_origen]
    if len(usados) < 3:
        raise ValueError(f"Se necesitan al menos 3 papeles para calibrar; hay {len(usados)}")
    pesos = np.array(
        [_peso_duracion(f, p.precio_sucio) if ponderacion == "duracion" else 1.0 for p, f in usados]
    )

    def residuos(b):
        betas = Betas(*b)
        return np.array([p.precio_sucio - precio(f, betas, tau) for p, f in usados]) * pesos

    mejor = None
    for x0 in arranques:
        r = least_squares(residuos, x0, xtol=1e-15, ftol=1e-15, gtol=1e-15, max_nfev=20_000)
        betas = Betas(*map(float, r.x))
        valor = sse(usados, betas, tau)
        if mejor is None or valor < mejor[1]:
            mejor = (betas, valor, tuple(x0), bool(r.success))
    betas, valor, x0, exito = mejor
    plazos = np.linspace(0, 30, 301)
    curva_sana = bool(np.all(spot(plazos, betas, tau) > -0.99))
    return Calibracion(
        betas=betas,
        tau=tau,
        sse=valor,
        rmse=float(np.sqrt(valor / len(usados))),
        n=len(usados),
        convergio=exito and curva_sana,
        arranque=x0,
        ponderacion=ponderacion,
        usar_origen=usar_origen,
    )
