import pandas as pd
import pytest

from roboadvisor.config import ParametrosFinancieros
from roboadvisor.core.multiplos import SenalMultiplo, peso_ajustado, senales_multiplos

HOY = pd.Timestamp("2024-06-10")
PARAMS = ParametrosFinancieros()


def _historial(ticker: str, pes: list[float], termina: pd.Timestamp = HOY) -> pd.DataFrame:
    """Una foto semanal por P/E, la última en `termina`."""
    fechas = [termina - pd.Timedelta(weeks=len(pes) - 1 - i) for i in range(len(pes))]
    return pd.DataFrame({"ticker": ticker, "fecha": fechas, "pe": pes})


def test_z_frente_al_propio_historico():
    # pasados: 10..21 (12 fotos) -> mediana 15.5; MAD = mediana(|x - 15.5|) = 3.0; hoy = 25
    pasados = [float(x) for x in range(10, 22)]
    historial = _historial("A", [*pasados, 25.0])
    s = senales_multiplos(historial, ["A"], PARAMS, HOY)[0]
    z_esperado = (25.0 - 15.5) / (1.4826 * 3.0)
    assert s.mediana_historica == pytest.approx(15.5)
    assert s.z == pytest.approx(z_esperado)
    assert s.senal == "cara"
    assert s.tilt_sugerido == -PARAMS.tilt_multiplos
    assert s.n_obs == 12


def test_barata_cuando_esta_muy_por_debajo_de_su_historia():
    historial = _historial("A", [*[float(x) for x in range(20, 32)], 8.0])
    s = senales_multiplos(historial, ["A"], PARAMS, HOY)[0]
    assert s.senal == "barata"
    assert s.tilt_sugerido == PARAMS.tilt_multiplos


def test_neutral_si_esta_dentro_de_lo_normal():
    historial = _historial("A", [*[float(x) for x in range(10, 22)], 16.0])
    s = senales_multiplos(historial, ["A"], PARAMS, HOY)[0]
    assert s.senal == "neutral"


def test_historia_insuficiente_da_sin_dato_y_explica_cuanto_falta():
    historial = _historial("A", [10.0, 11.0, 12.0])  # 2 fotos previas
    s = senales_multiplos(historial, ["A"], PARAMS, HOY)[0]
    assert s.senal == "sin_dato"
    assert s.pe == 12.0
    assert s.n_obs == 2
    assert f"2 de {PARAMS.min_obs_pe}" in s.motivo


def test_pe_viejo_o_inexistente_da_sin_dato():
    viejo = _historial("A", [float(x) for x in range(10, 24)], termina=HOY - pd.Timedelta(days=30))
    vacio = pd.DataFrame(columns=["ticker", "fecha", "pe"])
    assert senales_multiplos(viejo, ["A"], PARAMS, HOY)[0].senal == "sin_dato"
    assert senales_multiplos(vacio, ["A"], PARAMS, HOY)[0].senal == "sin_dato"


def test_mad_cero_da_neutral():
    historial = _historial("A", [10.0] * 13)
    s = senales_multiplos(historial, ["A"], PARAMS, HOY)[0]
    assert s.senal == "neutral"
    assert s.z == 0.0


def test_pe_no_positivo_se_ignora():
    historial = _historial("A", [-5.0, *[float(x) for x in range(10, 22)], 15.0])
    s = senales_multiplos(historial, ["A"], PARAMS, HOY)[0]
    assert s.n_obs == 12  # el negativo no cuenta


def test_peso_ajustado_aplica_tilt_y_conserva_la_suma():
    pesos = pd.Series({"A": 0.5, "B": 0.3, "C": 0.2})
    senales = [
        SenalMultiplo("A", 20.0, 10.0, 2.0, "cara", -0.025),
        SenalMultiplo("B", 5.0, 10.0, -2.0, "barata", 0.025),
        SenalMultiplo("C", 10.0, 10.0, 0.0, "neutral", 0.0),
    ]
    ajustado = peso_ajustado(pesos, senales, 0.025)
    assert ajustado.sum() == pytest.approx(1.0)
    assert ajustado["A"] < 0.5
    assert ajustado["B"] > 0.3
