"""Fixtures sintéticos compartidos para pruebas del motor financiero (E04+).

Semilla fija para que todas las corridas sean deterministas.
"""

import numpy as np
import pandas as pd
import pytest

from roboadvisor.core.retornos import estimar

TICKERS_SINTETICOS = ["ACT_A", "ACT_B", "ACT_C", "ACT_D", "ACT_E"]
N_MESES_SINTETICOS = 70
SEMILLA = 42


def generar_panel_sintetico() -> pd.DataFrame:
    """Panel de 5 activos, precios de cierre de mes, 70 meses, semilla fija."""
    rng = np.random.default_rng(SEMILLA)
    fechas = pd.date_range("2019-01-31", periods=N_MESES_SINTETICOS, freq="ME")

    medias_mensuales = np.array([0.004, 0.006, 0.003, 0.008, 0.005])
    volatilidades_mensuales = np.array([0.03, 0.05, 0.02, 0.07, 0.04])

    retornos = rng.normal(
        loc=medias_mensuales,
        scale=volatilidades_mensuales,
        size=(N_MESES_SINTETICOS, len(TICKERS_SINTETICOS)),
    )
    precios = 100 * np.cumprod(1 + retornos, axis=0)
    return pd.DataFrame(precios, index=fechas, columns=TICKERS_SINTETICOS)


@pytest.fixture
def panel_precios_sintetico() -> pd.DataFrame:
    return generar_panel_sintetico()


@pytest.fixture
def estimacion_sintetica(panel_precios_sintetico):
    """`Estimacion` construida con `estimar()` sobre el panel sintético."""
    return estimar(panel_precios_sintetico, rf=0.02, ventana_meses=60, min_meses=36)
