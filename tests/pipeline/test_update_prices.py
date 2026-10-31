import pandas as pd
import pytest

from roboadvisor.config import ParametrosFinancieros
from roboadvisor.pipeline.update_prices import ejecutar

HOY = pd.Timestamp("2024-06-10")
PARAMS = ParametrosFinancieros()


def _panel(ticker: str, fechas: pd.DatetimeIndex, precio_inicial: float = 100.0) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ticker,
            "fecha": fechas,
            "close": precio_inicial,
            "adj_close": precio_inicial,
            "volumen": 1000,
        }
    )


class FakeYahoo:
    """Yahoo falso: devuelve un panel fijo por ticker; algunos tickers fallan."""

    def __init__(self, paneles: dict[str, pd.DataFrame], fallidos: set[str] = frozenset()):
        self.paneles = paneles
        self.fallidos = fallidos
        self.llamadas_desde: list[pd.Timestamp] = []

    def descargar_precios(self, tickers: list[str], desde: pd.Timestamp) -> pd.DataFrame:
        ticker = tickers[0]
        self.llamadas_desde.append(desde)
        if ticker in self.fallidos:
            raise RuntimeError("Yahoo no disponible")
        panel = self.paneles[ticker]
        return panel[panel["fecha"] >= desde].reset_index(drop=True)

    def descargar_rf(self, desde: pd.Timestamp) -> pd.DataFrame:
        return pd.DataFrame({"fecha": [HOY], "tasa_anual": [0.05]})


class RepositorioMemoria:
    """Repositorio en memoria para pruebas, sin Supabase."""

    def __init__(self, activos: list[dict]):
        self._activos = activos
        self.precios = pd.DataFrame(columns=["ticker", "fecha", "close", "adj_close", "volumen"])
        self.rf = pd.DataFrame(columns=["fecha", "tasa_anual"])
        self.corridas: list[dict] = []

    def listar_activos(self, activos_only: bool = True) -> list[dict]:
        return [a for a in self._activos if not activos_only or a["activo"]]

    def ultima_fecha_por_ticker(self) -> dict[str, pd.Timestamp]:
        if self.precios.empty:
            return {}
        return self.precios.groupby("ticker")["fecha"].max().to_dict()

    def upsert_precios(self, df: pd.DataFrame) -> int:
        self.precios = (
            pd.concat([self.precios, df], ignore_index=True)
            .drop_duplicates(subset=["ticker", "fecha"], keep="last")
            .reset_index(drop=True)
        )
        return len(df)

    def upsert_rf(self, df: pd.DataFrame) -> int:
        self.rf = (
            pd.concat([self.rf, df], ignore_index=True)
            .drop_duplicates(subset=["fecha"], keep="last")
            .reset_index(drop=True)
        )
        return len(df)

    def registrar_corrida(self, tipo, estado, filas_precios, detalle) -> None:
        self.corridas.append(
            {"tipo": tipo, "estado": estado, "filas_precios": filas_precios, "detalle": detalle}
        )


@pytest.fixture
def activos_dos_tickers():
    return [
        {"ticker": "A", "es_renta_fija": False, "activo": True},
        {"ticker": "B", "es_renta_fija": False, "activo": True},
    ]


def test_idempotencia_dos_corridas_mismas_filas(activos_dos_tickers):
    fechas = pd.bdate_range("2024-05-01", "2024-06-07")
    yahoo = FakeYahoo({"A": _panel("A", fechas), "B": _panel("B", fechas)})
    repo = RepositorioMemoria(activos_dos_tickers)

    r1 = ejecutar(yahoo, repo, PARAMS, fecha_corrida=HOY, historico_anios=1)
    filas_tras_r1 = len(repo.precios)
    assert r1.estado == "ok"

    r2 = ejecutar(yahoo, repo, PARAMS, fecha_corrida=HOY, historico_anios=1)
    filas_tras_r2 = len(repo.precios)

    assert r2.estado == "ok"
    assert filas_tras_r2 == filas_tras_r1


def test_segunda_corrida_pide_con_solapamiento_de_5_dias(activos_dos_tickers):
    fechas = pd.bdate_range("2024-05-01", "2024-06-07")
    yahoo = FakeYahoo({"A": _panel("A", fechas), "B": _panel("B", fechas)})
    repo = RepositorioMemoria(activos_dos_tickers)

    ejecutar(yahoo, repo, PARAMS, fecha_corrida=HOY, historico_anios=1)
    ultima_fecha_a = repo.precios[repo.precios["ticker"] == "A"]["fecha"].max()

    yahoo.llamadas_desde.clear()
    ejecutar(yahoo, repo, PARAMS, fecha_corrida=HOY, historico_anios=1)

    assert yahoo.llamadas_desde[0] == ultima_fecha_a - pd.Timedelta(days=5)


def test_ticker_fallido_da_estado_parcial_sin_romper_los_demas(activos_dos_tickers):
    fechas = pd.bdate_range("2024-05-01", "2024-06-07")
    yahoo = FakeYahoo({"A": _panel("A", fechas), "B": _panel("B", fechas)}, fallidos={"B"})
    repo = RepositorioMemoria(activos_dos_tickers)

    reporte = ejecutar(yahoo, repo, PARAMS, fecha_corrida=HOY, historico_anios=1)

    assert reporte.estado == "parcial"
    assert reporte.detalle["A"]["estado"] == "ok"
    assert reporte.detalle["B"]["estado"] == "error"
    assert (repo.precios["ticker"] == "A").any()
    assert not (repo.precios["ticker"] == "B").any()


def test_dry_run_no_escribe_en_el_repositorio(activos_dos_tickers):
    fechas = pd.bdate_range("2024-05-01", "2024-06-07")
    yahoo = FakeYahoo({"A": _panel("A", fechas), "B": _panel("B", fechas)})
    repo = RepositorioMemoria(activos_dos_tickers)

    ejecutar(yahoo, repo, PARAMS, fecha_corrida=HOY, historico_anios=1, dry_run=True)

    assert repo.precios.empty
    assert repo.corridas == []
