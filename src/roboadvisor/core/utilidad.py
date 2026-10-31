"""Función de utilidad media-varianza del inversionista."""


def utilidad(er: float, sigma: float, a: float) -> float:
    """Utilidad media-varianza: `U = er − 0.5·a·sigma²`.

    `sigma` es la desviación estándar (no la varianza) y debe ser `>= 0`;
    `a` es el coeficiente de aversión al riesgo y debe ser `> 0`.
    """
    if sigma < 0:
        raise ValueError(f"sigma debe ser >= 0: {sigma}")
    if a <= 0:
        raise ValueError(f"a debe ser > 0: {a}")
    return er - 0.5 * a * sigma**2
