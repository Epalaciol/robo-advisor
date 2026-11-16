"""Flujos de un TES: cupones anuales en los aniversarios del vencimiento + 100 al final.

Convención del Excel del profesor (verificada con el cupón corrido del informe del 2-oct):
las fechas se obtienen restando años al vencimiento (`EDATE(venc, −12·k)`), solo cuentan las
**estrictamente posteriores** a la fecha de valoración, y t = días / 365.
"""

from datetime import date

import numpy as np

from .modelos import Flujos, Papel


def aniversario(vencimiento: date, anos_atras: int) -> date:
    """`EDATE(vencimiento, −12·anos_atras)`. Un 29-feb cae en 28-feb si el año no es bisiesto."""
    anio = vencimiento.year - anos_atras
    try:
        return vencimiento.replace(year=anio)
    except ValueError:
        return vencimiento.replace(year=anio, day=28)


def flujos(
    vencimiento: date,
    cupon: float,
    fecha: date,
    dias_ano: int = 365,
    incluir_cupon_hoy: bool = False,
) -> Flujos:
    """Flujos posteriores a `fecha` por cada $100 de facial. TCO (cupón 0): solo 100.

    Con `incluir_cupon_hoy`, el cupón que cae exactamente en `fecha` entra como flujo en t = 0
    (DF = 1): IRC lo deja dentro del precio sucio ese día (ver `incluye_cupon_hoy`).
    """
    if vencimiento <= fecha:
        raise ValueError(f"El papel vence ({vencimiento}) en o antes de la valoración ({fecha})")
    if cupon == 0:
        fechas = [vencimiento]
        montos = [100.0]
    else:
        fechas, k = [], 0
        while (f := aniversario(vencimiento, k)) > fecha or (incluir_cupon_hoy and f == fecha):
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


def cupon_corrido(
    vencimiento: date,
    cupon: float,
    fecha: date,
    dias_ano: int = 365,
    incluir_cupon_hoy: bool = False,
) -> float:
    """Cupón corrido = cupón × días desde el último aniversario / 365 (= sucio − limpio).

    Si el cupón cae en `fecha` y se incluye (`incluir_cupon_hoy`), el corrido es el cupón completo.
    """
    if cupon == 0:
        return 0.0
    if incluir_cupon_hoy and ultimo_cupon(vencimiento, fecha) == fecha:
        return cupon
    return cupon * (fecha - ultimo_cupon(vencimiento, fecha)).days / dias_ano


def incluye_cupon_hoy(papel: Papel, fecha: date, tol: float = 0.10) -> bool:
    """¿Trae el precio sucio el cupón que se paga en `fecha`? (sucio − limpio ≈ cupón completo).

    Solo aplica si un aniversario del vencimiento es `fecha`. Si el sucio − limpio es ≈ 0 (precio
    ex-cupón) el cupón no se incluye. `tol` en puntos de precio (el informe puede venir con unos
    días de rezago en el corrido: 4 días de un cupón de 5,75 son 0,06).
    """
    if papel.cupon == 0 or papel.precio_limpio is None or papel.vencimiento <= fecha:
        return False
    if ultimo_cupon(papel.vencimiento, fecha) != fecha:
        return False
    return abs(papel.precio_sucio - papel.precio_limpio - papel.cupon) <= tol


def flujos_papel(papel: Papel, fecha: date, dias_ano: int = 365, tol: float = 0.10) -> Flujos:
    """Flujos de un papel decidiendo si el cupón de la fecha de valoración entra en t = 0."""
    return flujos(
        papel.vencimiento,
        papel.cupon,
        fecha,
        dias_ano,
        incluir_cupon_hoy=incluye_cupon_hoy(papel, fecha, tol),
    )


def cupon_corrido_papel(papel: Papel, fecha: date, dias_ano: int = 365, tol: float = 0.10) -> float:
    return cupon_corrido(
        papel.vencimiento,
        papel.cupon,
        fecha,
        dias_ano,
        incluir_cupon_hoy=incluye_cupon_hoy(papel, fecha, tol),
    )
