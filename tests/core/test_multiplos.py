import pandas as pd
import pytest

from roboadvisor.config import ParametrosFinancieros
from roboadvisor.core.multiplos import peso_ajustado, senales_multiplos

HOY = pd.Timestamp("2024-06-10")


def _fundamentales(filas: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(filas)


def test_senal_con_peers_conocidos_da_z_esperado():
    # peers: 10, 12, 14, 16 -> mediana=13
    # MAD: |10-13|,|12-13|,|14-13|,|16-13| = 3,1,1,3 -> mediana=2
    fundamentales = _fundamentales(
        [
            {"ticker": "A", "pe": 10.0, "pb": 1.0, "fecha": HOY},
            {"ticker": "B", "pe": 12.0, "pb": 1.0, "fecha": HOY},
            {"ticker": "C", "pe": 14.0, "pb": 1.0, "fecha": HOY},
            {"ticker": "D", "pe": 16.0, "pb": 1.0, "fecha": HOY},
        ]
    )
    params = ParametrosFinancieros()
    señales = senales_multiplos(fundamentales, ["D"], params, HOY)
    señal_d = señales[0]

    z_esperado = (16.0 - 13.0) / (1.4826 * 2.0)
    assert señal_d.z == pytest.approx(z_esperado)
    if z_esperado > 1:
        esperado = "cara"
    elif z_esperado < -1:
        esperado = "barata"
    else:
        esperado = "neutral"
    assert señal_d.senal == esperado


def test_mad_cero_da_neutral():
    fundamentales = _fundamentales(
        [
            {"ticker": "A", "pe": 10.0, "pb": 1.0, "fecha": HOY},
            {"ticker": "B", "pe": 10.0, "pb": 1.0, "fecha": HOY},
            {"ticker": "C", "pe": 10.0, "pb": 1.0, "fecha": HOY},
            {"ticker": "D", "pe": 10.0, "pb": 1.0, "fecha": HOY},
        ]
    )
    params = ParametrosFinancieros()
    señales = senales_multiplos(fundamentales, ["A"], params, HOY)
    assert señales[0].senal == "neutral"
    assert señales[0].z == 0.0


def test_menos_de_cuatro_peers_da_sin_dato():
    fundamentales = _fundamentales(
        [
            {"ticker": "A", "pe": 10.0, "pb": 1.0, "fecha": HOY},
            {"ticker": "B", "pe": 12.0, "pb": 1.0, "fecha": HOY},
        ]
    )
    params = ParametrosFinancieros()
    señales = senales_multiplos(fundamentales, ["A"], params, HOY)
    assert señales[0].senal == "sin_dato"
    assert señales[0].motivo is not None


def test_pe_negativo_da_sin_dato():
    fundamentales = _fundamentales(
        [
            {"ticker": "A", "pe": -5.0, "pb": 1.0, "fecha": HOY},
            {"ticker": "B", "pe": 12.0, "pb": 1.0, "fecha": HOY},
            {"ticker": "C", "pe": 14.0, "pb": 1.0, "fecha": HOY},
            {"ticker": "D", "pe": 16.0, "pb": 1.0, "fecha": HOY},
        ]
    )
    params = ParametrosFinancieros()
    señales = senales_multiplos(fundamentales, ["A"], params, HOY)
    assert señales[0].senal == "sin_dato"


def test_dato_viejo_se_descarta():
    fundamentales = _fundamentales(
        [
            {"ticker": "A", "pe": 10.0, "pb": 1.0, "fecha": HOY - pd.Timedelta(days=15)},
            {"ticker": "B", "pe": 12.0, "pb": 1.0, "fecha": HOY},
            {"ticker": "C", "pe": 14.0, "pb": 1.0, "fecha": HOY},
            {"ticker": "D", "pe": 16.0, "pb": 1.0, "fecha": HOY},
        ]
    )
    params = ParametrosFinancieros()
    señales = senales_multiplos(fundamentales, ["A"], params, HOY)
    assert señales[0].senal == "sin_dato"


def test_peso_ajustado_suma_lo_mismo_y_respeta_0_1():
    from roboadvisor.core.multiplos import SenalMultiplo

    pesos = pd.Series({"A": 0.3, "B": 0.3, "C": 0.4})
    señales = [
        SenalMultiplo(
            ticker="A", pe=20.0, mediana_peers=10.0, z=2.0, senal="cara", tilt_sugerido=-0.025
        ),
        SenalMultiplo(
            ticker="B", pe=5.0, mediana_peers=10.0, z=-2.0, senal="barata", tilt_sugerido=0.025
        ),
        SenalMultiplo(
            ticker="C", pe=10.0, mediana_peers=10.0, z=0.0, senal="neutral", tilt_sugerido=0.0
        ),
    ]
    ajustado = peso_ajustado(pesos, señales, tilt=0.025)

    assert ajustado.sum() == pytest.approx(pesos.sum())
    assert (ajustado >= 0.0).all()
    assert (ajustado <= 1.0).all()
    assert ajustado["A"] < pesos["A"]
    assert ajustado["B"] > pesos["B"]
