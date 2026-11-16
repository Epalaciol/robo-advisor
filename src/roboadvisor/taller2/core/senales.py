"""Decisión comprar / vender / mantener a partir de spread = TIR observada − TIR estimada (pb).

spread > +u → "Comprar" (el papel rinde más que la curva: está barato)
spread < −u → "Vender"  (rinde menos que la curva: está caro)
en otro caso → "Mantener"
"""

from collections.abc import Sequence

import numpy as np

COMPRAR, VENDER, MANTENER = "Comprar", "Vender", "Mantener"


def umbral_pb(spreads: Sequence[float], regla: str | float) -> float:
    """'sigma' = desviación estándar muestral (como STDEV.S del Excel);
    'sigma_robusta' = 1,4826·MAD; número = umbral fijo en pb."""
    x = np.asarray(spreads, dtype=float)
    if regla == "sigma":
        return float(np.std(x, ddof=1))
    if regla == "sigma_robusta":
        return float(1.4826 * np.median(np.abs(x - np.median(x))))
    return float(regla)


def senal(spread_pb: float, umbral: float) -> str:
    if spread_pb > umbral:
        return COMPRAR
    if spread_pb < -umbral:
        return VENDER
    return MANTENER
