"""Flujos de un TES: cupones anuales en los aniversarios del vencimiento + 100 al final.

Convención del Excel del profesor (verificada con el cupón corrido del informe del 2-oct):
las fechas se obtienen restando años al vencimiento (`EDATE(venc, −12·k)`), solo cuentan las
**estrictamente posteriores** a la fecha de valoración, y t = días / 365.
"""

from datetime import date

import numpy as np

from .modelos import Flujos


def aniversario(vencimiento: date, anos_atras: int) -> date:
    """`EDATE(vencimiento, −12·anos_atras)`. Un 29-feb cae en 28-feb si el año no es bisiesto."""
    anio = vencimiento.year - anos_atras
    try:
        return vencimiento.replace(year=anio)
    except ValueError:
        return vencimiento.replace(year=anio, day=28)


def flujos(vencimiento: date, cupon: float, fecha: date, dias_ano: int = 365) -> Flujos:
    """Flujos posteriores a `fecha` por cada $100 de facial. TCO (cupón 0): solo 100."""
    if vencimiento <= fecha:
        raise ValueError(f"El papel vence ({vencimiento}) en o antes de la valoración ({fecha})")
    if cupon == 0:
        fechas = [vencimiento]
        montos = [100.0]
    else:
        fechas, k = [], 0
        while (f := aniversario(vencimiento, k)) > fecha:
            fechas.append(f)
            k += 1
        fechas.reverse()
        montos = [cupon] * len(fechas)
        montos[-1] += 100.0
    t = np.array([(f - fecha).days for f in fechas], dtype=float) / dias_ano
    return Flujos(fechas=tuple(fechas), t=t, montos=np.array(montos, dtype=float))


def ultimo_cupon(vencimiento: date, fecha: date) -> date:
    """Último aniversario del vencimiento en o antes de `fecha` (inicio del cupón corrido)."""
    k = 0
    while (f := aniversario(vencimiento, k)) > fecha:
        k += 1
    return f


def cupon_corrido(vencimiento: date, cupon: float, fecha: date, dias_ano: int = 365) -> float:
    """Cupón corrido = cupón × días desde el último aniversario / 365 (= sucio − limpio)."""
    if cupon == 0:
        return 0.0
    return cupon * (fecha - ultimo_cupon(vencimiento, fecha)).days / dias_ano
