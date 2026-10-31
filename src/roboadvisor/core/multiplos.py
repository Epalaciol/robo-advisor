"""Análisis de múltiplos (P/E) para sugerir tilts de sobre/subponderación.

Ver docs/03 §8. Las señales **ajustan una sugerencia**, no recalculan Markowitz.
"""

from dataclasses import dataclass

import pandas as pd

from roboadvisor.config import ParametrosFinancieros

DIAS_ANTIGUEDAD_MAX = 10  # fundamentales con más de 10 días de antigüedad se descartan
MIN_PEERS = 4
UMBRAL_Z = 1.0
CONSTANTE_MAD = 1.4826


@dataclass(frozen=True)
class SenalMultiplo:
    """Señal de múltiplos de un ticker frente a sus peers del catálogo."""

    ticker: str
    pe: float | None
    mediana_peers: float | None
    z: float | None
    senal: str  # "cara" | "barata" | "neutral" | "sin_dato"
    tilt_sugerido: float
    motivo: str | None = None


def _peers_validos(fundamentales: pd.DataFrame, fecha_referencia: pd.Timestamp) -> pd.DataFrame:
    antiguedad = (fecha_referencia - fundamentales["fecha"]).dt.days
    return fundamentales[(antiguedad <= DIAS_ANTIGUEDAD_MAX) & (fundamentales["pe"] > 0)]


def senales_multiplos(
    fundamentales: pd.DataFrame,
    elegibles: list[str],
    params: ParametrosFinancieros,
    fecha_referencia: pd.Timestamp,
) -> list[SenalMultiplo]:
    """Señal de múltiplos (`cara`/`barata`/`neutral`/`sin_dato`) por ticker elegible.

    `z = (PE_i − mediana(PE_peers)) / (1.4826·MAD(PE_peers))`, con peers = acciones
    del catálogo con `pe > 0` y antigüedad `<= 10` días. `z > 1` → cara (sugiere
    subponderar `tilt_multiplos`); `z < -1` → barata (sobreponderar). Si hay menos
    de 4 peers con dato, o `MAD = 0`, no hay señal confiable.
    """
    validos = _peers_validos(fundamentales, fecha_referencia).set_index("ticker")
    peers_pe = validos["pe"]

    mediana = peers_pe.median() if len(peers_pe) else None
    mad = (peers_pe - mediana).abs().median() if mediana is not None else None

    senales = []
    for ticker in elegibles:
        if ticker not in validos.index:
            senales.append(
                SenalMultiplo(
                    ticker=ticker,
                    pe=None,
                    mediana_peers=mediana,
                    z=None,
                    senal="sin_dato",
                    tilt_sugerido=0.0,
                    motivo="Sin dato de P/E vigente (≤10 días) o P/E no significativo",
                )
            )
            continue

        if len(peers_pe) < MIN_PEERS:
            senales.append(
                SenalMultiplo(
                    ticker=ticker,
                    pe=float(peers_pe[ticker]),
                    mediana_peers=mediana,
                    z=None,
                    senal="sin_dato",
                    tilt_sugerido=0.0,
                    motivo=f"Menos de {MIN_PEERS} peers con dato",
                )
            )
            continue

        pe_i = float(peers_pe[ticker])
        if mad == 0:
            senales.append(
                SenalMultiplo(
                    ticker=ticker,
                    pe=pe_i,
                    mediana_peers=float(mediana),
                    z=0.0,
                    senal="neutral",
                    tilt_sugerido=0.0,
                )
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
            SenalMultiplo(
                ticker=ticker,
                pe=pe_i,
                mediana_peers=float(mediana),
                z=float(z),
                senal=senal,
                tilt_sugerido=tilt,
            )
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
