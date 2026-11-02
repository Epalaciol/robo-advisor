"""Reglas de calidad de los precios descargados. Ver docs/04 §Validaciones.

Funciones puras: reciben `DataFrame`s ya descargados y devuelven un reporte,
sin red ni Supabase.
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

UMBRAL_SALTO_RENTA_FIJA = 0.40
UMBRAL_SALTO_RENTA_VARIABLE = 0.60


@dataclass(frozen=True)
class ReporteValidacion:
    """Resultado de validar los precios de un ticker.

    `valido=False` significa que el ticker **no se carga** en esta corrida;
    las advertencias no bloquean la carga, solo quedan en el reporte.
    """

    valido: bool
    errores: list[str] = field(default_factory=list)
    advertencias: list[str] = field(default_factory=list)


def validar_precios(
    df: pd.DataFrame,
    es_renta_fija: bool,
    fecha_corrida: pd.Timestamp,
    dias_stale: int,
) -> ReporteValidacion:
    """Valida un panel `ticker, fecha, close, adj_close, volumen` de un solo ticker.

    Errores (bloquean la carga): `adj_close <= 0` o nulo, fecha futura, fecha
    duplicada, sin datos. Advertencias (se carga pero se reporta): salto diario
    `|retorno| > 40%` (renta fija) o `> 60%` (renta variable/cripto); último
    dato con más de `dias_stale` días hábiles de atraso respecto a `fecha_corrida`.
    """
    errores: list[str] = []
    advertencias: list[str] = []

    if df.empty:
        return ReporteValidacion(valido=False, errores=["Sin datos"])

    if (df["adj_close"] <= 0).any() or df["adj_close"].isna().any():
        errores.append("adj_close <= 0 o nulo")

    # tolerancia de 1 día: desfase UTC (la cripto cotiza 24/7)
    if (df["fecha"] > fecha_corrida + pd.Timedelta(days=1)).any():
        errores.append("Fecha futura")

    if df["fecha"].duplicated().any():
        errores.append("Fecha duplicada")

    if errores:
        return ReporteValidacion(valido=False, errores=errores, advertencias=advertencias)

    ordenado = df.sort_values("fecha")
    retornos = ordenado["adj_close"].pct_change().dropna()
    umbral_salto = UMBRAL_SALTO_RENTA_FIJA if es_renta_fija else UMBRAL_SALTO_RENTA_VARIABLE
    n_saltos = int((retornos.abs() > umbral_salto).sum())
    if n_saltos:
        advertencias.append(
            f"Salto diario > {umbral_salto:.0%} en {n_saltos} fecha(s) (revisar splits)"
        )

    ultima_fecha = ordenado["fecha"].max()
    dias_habiles_atraso = int(np.busday_count(ultima_fecha.date(), fecha_corrida.date()))
    if dias_habiles_atraso > dias_stale:
        advertencias.append(
            f"Último dato con {dias_habiles_atraso} días hábiles de atraso (> {dias_stale})"
        )

    return ReporteValidacion(valido=True, errores=[], advertencias=advertencias)
