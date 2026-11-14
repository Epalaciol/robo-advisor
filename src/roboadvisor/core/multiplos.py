"""Análisis de múltiplos (P/E) para sugerir tilts de sobre/subponderación.

Ver docs/03 §8. Cada activo se compara **con su propio histórico de P/E** (no con otros
activos): `cara` si hoy cotiza a un múltiplo alto frente a lo que ha sido normal para él,
`barata` si bajo. Las señales **ajustan una sugerencia**, no recalculan Markowitz.
"""

from dataclasses import dataclass

import pandas as pd

from roboadvisor.config import ParametrosFinancieros

DIAS_ANTIGUEDAD_MAX = 10  # un P/E con más de 10 días de antigüedad no cuenta como "actual"
UMBRAL_Z = 1.0
CONSTANTE_MAD = 1.4826


@dataclass(frozen=True)
class SenalMultiplo:
    """Señal de múltiplos de un ticker frente a su propio histórico de P/E."""

    ticker: str
    pe: float | None
    mediana_historica: float | None
    z: float | None
    senal: str  # "cara" | "barata" | "neutral" | "sin_dato"
    tilt_sugerido: float
    motivo: str | None = None
    n_obs: int = 0  # observaciones históricas propias usadas


def senales_multiplos(
    historial: pd.DataFrame,
    elegibles: list[str],
    params: ParametrosFinancieros,
    fecha_referencia: pd.Timestamp,
) -> list[SenalMultiplo]:
    """Señal de múltiplos (`cara`/`barata`/`neutral`/`sin_dato`) por ticker elegible.

    `historial` trae `ticker, fecha, pe` (una fila por foto de P/E). Para cada ticker:
    `z = (PE_hoy − mediana(PE_pasados)) / (1.4826·MAD(PE_pasados))`. `z > 1` → cara
    (sugiere subponderar `tilt_multiplos`); `z < -1` → barata (sobreponderar). Sin señal
    si no hay un P/E actual (≤ 10 días), si el histórico propio tiene menos de
    `params.min_obs_pe` observaciones previas, o si `MAD = 0` (se marca neutral).
    """
    historial = historial.copy()
    if not historial.empty:
        historial["fecha"] = pd.to_datetime(historial["fecha"])
        historial = historial[historial["pe"] > 0]

    senales = []
    for ticker in elegibles:
        serie = (
            historial[historial["ticker"] == ticker].sort_values("fecha")
            if not historial.empty
            else historial
        )
        if serie.empty:
            senales.append(
                SenalMultiplo(ticker, None, None, None, "sin_dato", 0.0, "Sin dato de P/E")
            )
            continue

        actual = serie.iloc[-1]
        pasados = serie.iloc[:-1]["pe"].astype(float)
        pe_i = float(actual["pe"])
        antiguedad = (fecha_referencia - actual["fecha"]).days

        if antiguedad > DIAS_ANTIGUEDAD_MAX:
            senales.append(
                SenalMultiplo(
                    ticker, None, None, None, "sin_dato", 0.0,
                    f"Último P/E con {antiguedad} días de antigüedad (> {DIAS_ANTIGUEDAD_MAX})",
                    len(pasados),
                )
            )  # fmt: skip
            continue

        if len(pasados) < params.min_obs_pe:
            senales.append(
                SenalMultiplo(
                    ticker, pe_i, None, None, "sin_dato", 0.0,
                    f"Acumulando historia propia: {len(pasados)} de {params.min_obs_pe} "
                    "observaciones previas necesarias",
                    len(pasados),
                )
            )  # fmt: skip
            continue

        mediana = float(pasados.median())
        mad = float((pasados - mediana).abs().median())
        if mad == 0:
            senales.append(
                SenalMultiplo(ticker, pe_i, mediana, 0.0, "neutral", 0.0, None, len(pasados))
            )
            continue

        z = (pe_i - mediana) / (CONSTANTE_MAD * mad)
        if z > UMBRAL_Z:
            senal, tilt = "cara", -params.tilt_multiplos
        elif z < -UMBRAL_Z:
            senal, tilt = "barata", params.tilt_multiplos
        else:
            senal, tilt = "neutral", 0.0
        senales.append(
            SenalMultiplo(ticker, pe_i, mediana, float(z), senal, tilt, None, len(pasados))
        )

    return senales


def peso_ajustado(
    pesos_actuales: pd.Series, senales: list[SenalMultiplo], tilt: float
) -> pd.Series:
    """Aplica el tilt de múltiplos a `pesos_actuales` (sugerencia, no recalcula
    Markowitz): resta `tilt` a las acciones "cara", suma `tilt` a las "barata",
    recorta a `[0, 1]` y renormaliza para sumar lo mismo que antes.
    """
    por_ticker = {s.ticker: s.senal for s in senales}
    ajustado = pesos_actuales.copy().astype(float)

    for ticker in ajustado.index:
        senal = por_ticker.get(ticker)
        if senal == "cara":
            ajustado[ticker] -= tilt
        elif senal == "barata":
            ajustado[ticker] += tilt

    ajustado = ajustado.clip(lower=0.0, upper=1.0)
    total_original = pesos_actuales.sum()
    return ajustado / ajustado.sum() * total_original
