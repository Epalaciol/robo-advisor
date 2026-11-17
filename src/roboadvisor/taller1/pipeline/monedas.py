"""Conversión de precios en moneda local a USD (moneda base del proyecto).

Funciones puras: reciben `DataFrame`/`Series` ya descargados, sin red. El pipeline
guarda siempre precios en USD, así un ETF en pesos (p. ej. `GXTESCOL.CL`) incorpora
el riesgo cambiario que asumiría un inversionista con base en dólares.
"""

import pandas as pd

# moneda local -> par de Yahoo que da "unidades de moneda local por 1 USD"
PARES_FX = {"COP": "COP=X"}


def convertir_a_usd(df: pd.DataFrame, local_por_usd: pd.Series) -> pd.DataFrame:
    """Divide `close` y `adj_close` entre el tipo de cambio (moneda local por USD).

    El tipo de cambio se alinea a las fechas del ETF con `ffill` (festivos distintos);
    filas sin tipo de cambio disponible se descartan. `df` trae `ticker, fecha, close,
    adj_close, volumen`.
    """
    if df.empty:
        return df
    tasas = local_por_usd.sort_index()
    fechas = pd.DatetimeIndex(df["fecha"])
    alineada = tasas.reindex(tasas.index.union(fechas)).ffill().reindex(fechas)

    salida = df.copy()
    validas = alineada.notna().to_numpy()
    salida = salida.loc[validas].copy()
    divisor = alineada.to_numpy()[validas]
    for columna in ("close", "adj_close"):
        salida[columna] = salida[columna].to_numpy() / divisor
    return salida.reset_index(drop=True)
