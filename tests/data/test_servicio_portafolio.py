"""Pruebas de `servicio_portafolio.construir_resumen` con repositorios falsos
(duck-typing: no tocan Supabase ni el mock, solo implementan los métodos que
el servicio llama)."""

import numpy as np
import pandas as pd
import pytest

from roboadvisor.config import ParametrosFinancieros
from roboadvisor.data.servicio_portafolio import construir_resumen

PARAMS = ParametrosFinancieros()
CATALOGO = [
    {"ticker": "A", "es_renta_fija": False},
    {"ticker": "B", "es_renta_fija": False},
    {"ticker": "C", "es_renta_fija": False},
    {"ticker": "ACWI", "es_renta_fija": False},
]


class RepoUsuarioFalso:
    def __init__(self, perfil, encuesta, portafolio):
        self._perfil = perfil
        self._encuesta = encuesta
        self._portafolio = portafolio

    def obtener_perfil(self):
        return self._perfil

    def obtener_encuesta(self):
        return self._encuesta

    def obtener_portafolio(self):
        return self._portafolio


class RepoMercadoFalso:
    def __init__(self, precios: pd.DataFrame, rf: float, fundamentales=None):
        self._precios = precios
        self._rf = rf
        self._fundamentales = (
            fundamentales
            if fundamentales is not None
            else pd.DataFrame(columns=["ticker", "fecha", "pe"])
        )

    def listar_catalogo(self):
        return CATALOGO

    def precios(self, tickers, desde):
        desde_ts = pd.Timestamp(desde)
        cols = [t for t in tickers if t in self._precios.columns]
        df = self._precios[cols]
        return df.loc[df.index >= desde_ts]

    def rf_ultima(self):
        return self._rf

    def fundamentales_historial(self, tickers):
        return self._fundamentales

    def ultima_fecha_precios(self):
        return str(self._precios.index.max().date())


def _panel_diario(fecha_inicio: str, fecha_fin: str, drifts: dict[str, float], vol: float = 0.001):
    """Panel diario determinista: cada ticker crece geométricamente a `drift`
    diario con un poco de ruido (semilla fija) para que la matriz de
    covarianza no sea degenerada."""
    fechas = pd.bdate_range(fecha_inicio, fecha_fin)
    rng = np.random.default_rng(7)
    data = {}
    for ticker, drift in drifts.items():
        ret = rng.normal(drift, vol, size=len(fechas))
        data[ticker] = 100 * np.cumprod(1 + ret)
    return pd.DataFrame(data, index=fechas)


def _portafolio(tickers: list[str], fecha_base: str, rf: float = 0.03) -> dict:
    n = len(tickers)
    pesos_riesgo = dict.fromkeys(tickers, round(1 / n, 6))
    return {
        "tickers": tickers,
        "pesos_riesgo": pesos_riesgo,
        "pesos_completo": {t: round(0.8 / n, 6) for t in tickers},
        "y_star": 0.8,
        "peso_rf": 0.2,
        "metricas": {
            "retorno_completo": 0.08,
            "sigma_completo": 0.12,
        },
        "parametros": {"ventana_dias": 1260, "min_dias": 504, "w_max": 0.40, "rf": rf},
        "fecha_base": fecha_base,
    }


PERFIL = {"alias": "Prueba", "edad_rango": "25-34"}
ENCUESTA = {"perfil": "moderado", "a": 4.0}


def test_recien_creado_sin_datos_nuevos_no_falla():
    # 66 meses de historia hasta "hoy"; portafolio creado justo hoy -> 1 sola
    # observación de precio -> seguimiento.suficiente debe ser False.
    hoy = pd.Timestamp("2026-01-15")
    panel = _panel_diario(
        "2019-06-01", "2026-01-15", drifts={"A": 0.0006, "B": 0.0004, "ACWI": 0.0005}
    )
    fecha_base = str(hoy.date())

    repo_usuario = RepoUsuarioFalso(PERFIL, ENCUESTA, _portafolio(["A", "B"], fecha_base))
    repo_mercado = RepoMercadoFalso(panel, rf=0.03)

    resumen = construir_resumen(repo_usuario, repo_mercado, PARAMS, hoy=hoy)

    assert resumen.seguimiento.suficiente is False
    assert resumen.dias_desde_base == 0


def test_30_dias_despues_el_mas_rentable_pesa_mas():
    hoy = pd.Timestamp("2026-01-15")
    fecha_base = str((hoy - pd.Timedelta(days=30)).date())
    # A sube fuerte, B cae: tras 30 días, A debe pesar más que su 50% inicial.
    panel = _panel_diario(
        "2019-06-01", "2026-01-15", drifts={"A": 0.004, "B": -0.002, "ACWI": 0.0005}
    )

    repo_usuario = RepoUsuarioFalso(PERFIL, ENCUESTA, _portafolio(["A", "B"], fecha_base))
    repo_mercado = RepoMercadoFalso(panel, rf=0.03)

    resumen = construir_resumen(repo_usuario, repo_mercado, PARAMS, hoy=hoy)

    assert resumen.seguimiento.suficiente is True
    assert resumen.pesos_actuales_riesgo["A"] > resumen.pesos_iniciales["A"]
    assert resumen.pesos_actuales_riesgo["B"] < resumen.pesos_iniciales["B"]


def test_datos_viejos_activa_r5():
    hoy = pd.Timestamp("2026-01-15")
    fecha_base = str((hoy - pd.Timedelta(days=30)).date())
    panel = _panel_diario(
        "2019-06-01", "2026-01-15", drifts={"A": 0.0006, "B": 0.0005, "ACWI": 0.0005}
    )
    # "B" no tiene datos de los últimos 10 días hábiles (pipeline atrasado).
    panel.loc[panel.index[-10:], "B"] = np.nan

    repo_usuario = RepoUsuarioFalso(PERFIL, ENCUESTA, _portafolio(["A", "B"], fecha_base))
    repo_mercado = RepoMercadoFalso(panel, rf=0.03)

    resumen = construir_resumen(repo_usuario, repo_mercado, PARAMS, hoy=hoy)

    ids_disparados = {(r.id, r.ticker) for r in resumen.recomendaciones}
    assert ("R5", "B") in ids_disparados


def test_activo_rezagado_frente_a_rf_activa_r2():
    hoy = pd.Timestamp("2026-01-15")
    fecha_base = str((hoy - pd.Timedelta(days=30)).date())
    # "B" cae sostenidamente los últimos 12 meses: su retorno 12m debe quedar
    # muy por debajo de rf, con peso > min_peso_alerta (está al 50%).
    panel = _panel_diario(
        "2019-06-01", "2026-01-15", drifts={"A": 0.0008, "B": -0.004, "ACWI": 0.0005}
    )

    repo_usuario = RepoUsuarioFalso(PERFIL, ENCUESTA, _portafolio(["A", "B"], fecha_base))
    repo_mercado = RepoMercadoFalso(panel, rf=0.03)

    resumen = construir_resumen(repo_usuario, repo_mercado, PARAMS, hoy=hoy)

    ids_disparados = {(r.id, r.ticker) for r in resumen.recomendaciones}
    assert ("R2", "B") in ids_disparados


def test_lanza_valueerror_si_falta_portafolio():
    repo_usuario = RepoUsuarioFalso(PERFIL, ENCUESTA, None)
    repo_mercado = RepoMercadoFalso(pd.DataFrame(), rf=0.03)

    with pytest.raises(ValueError, match="Falta perfil"):
        construir_resumen(repo_usuario, repo_mercado, PARAMS)
