"""Carga diaria de precios (y rf) desde Yahoo a Supabase. Ver docs/04 §Algoritmo.

CLI: `python -m roboadvisor.pipeline.update_prices [--dry-run] [--desde F] [--tickers A,B]`.
`ejecutar()` recibe `yahoo` y `repositorio` por inyección de dependencias para
poder probarse sin red ni Supabase (ver `tests/pipeline/test_update_prices.py`).
"""

import argparse
import sys
from dataclasses import dataclass, field

import pandas as pd

from roboadvisor.config import ParametrosFinancieros
from roboadvisor.data import yahoo as yahoo_real
from roboadvisor.data.repositorio import repositorio_servicio
from roboadvisor.pipeline.validators import validar_precios

HISTORICO_ANIOS = 6
DIAS_SOLAPAMIENTO = 5


@dataclass(frozen=True)
class ReporteCorrida:
    """Resultado de una corrida del pipeline de precios."""

    estado: str  # "ok" | "parcial" | "error"
    filas_precios: int
    detalle: dict = field(default_factory=dict)


def ejecutar(
    yahoo,
    repositorio,
    params: ParametrosFinancieros,
    tickers: list[str] | None = None,
    desde: pd.Timestamp | None = None,
    dry_run: bool = False,
    fecha_corrida: pd.Timestamp | None = None,
    historico_anios: int = HISTORICO_ANIOS,
) -> ReporteCorrida:
    """1) lee catálogo, 2) por ticker pide a Yahoo desde `última_fecha - 5 días`
    (o `historico_anios` atrás si no hay datos), 3) valida, 4) upsert de los
    válidos, 5) descarga rf, 6) registra la corrida. `dry_run` descarga y
    valida pero no escribe en Supabase.
    """
    fecha_corrida = fecha_corrida or pd.Timestamp.today().normalize()

    activos = repositorio.listar_activos(activos_only=True)
    catalogo = {a["ticker"]: a for a in activos}
    tickers_objetivo = tickers or list(catalogo.keys())

    ultimas_fechas = repositorio.ultima_fecha_por_ticker()

    detalle: dict = {}
    filas_cargadas_total = 0
    hubo_error = False

    for ticker in tickers_objetivo:
        ultima = ultimas_fechas.get(ticker)
        if ultima is not None:
            desde_ticker = ultima - pd.Timedelta(days=DIAS_SOLAPAMIENTO)
        else:
            desde_ticker = desde or (fecha_corrida - pd.DateOffset(years=historico_anios))

        try:
            df_ticker = yahoo.descargar_precios([ticker], desde_ticker)
        except Exception as error:  # noqa: BLE001 - un ticker fallido no rompe los demás (parcial)
            detalle[ticker] = {"estado": "error", "errores": [str(error)], "advertencias": []}
            continue

        df_ticker = df_ticker[df_ticker["ticker"] == ticker] if not df_ticker.empty else df_ticker
        es_renta_fija = bool(catalogo.get(ticker, {}).get("es_renta_fija", False))
        reporte = validar_precios(df_ticker, es_renta_fija, fecha_corrida, params.dias_stale)

        if not reporte.valido:
            detalle[ticker] = {
                "estado": "invalido",
                "errores": reporte.errores,
                "advertencias": reporte.advertencias,
            }
            continue

        filas_ticker = len(df_ticker)
        if not dry_run:
            filas_ticker = repositorio.upsert_precios(df_ticker)
            filas_cargadas_total += filas_ticker

        detalle[ticker] = {
            "estado": "ok",
            "errores": [],
            "advertencias": reporte.advertencias,
            "filas": filas_ticker,
        }

    if not dry_run:
        try:
            rf_df = yahoo.descargar_rf(fecha_corrida - pd.DateOffset(years=1))
            repositorio.upsert_rf(rf_df)
        except Exception as error:  # noqa: BLE001 - no bloquea el resto de la corrida
            detalle["_rf"] = {"estado": "error", "errores": [str(error)]}
            hubo_error = True

    estados_tickers = [info["estado"] for t, info in detalle.items() if t != "_rf"]
    if hubo_error:
        estado_final = "error"
    elif any(e in ("invalido", "error") for e in estados_tickers):
        estado_final = "parcial"
    else:
        estado_final = "ok"

    if not dry_run:
        repositorio.registrar_corrida("precios", estado_final, filas_cargadas_total, detalle)

    return ReporteCorrida(estado=estado_final, filas_precios=filas_cargadas_total, detalle=detalle)


def main() -> None:
    parser = argparse.ArgumentParser(description="Carga diaria de precios desde Yahoo Finance")
    parser.add_argument("--dry-run", action="store_true", help="Descarga y valida, no escribe")
    parser.add_argument("--desde", help="Fecha inicial YYYY-MM-DD (solo tickers sin historia)")
    parser.add_argument("--tickers", help="Lista separada por comas; por defecto todo el catálogo")
    args = parser.parse_args()

    tickers = args.tickers.split(",") if args.tickers else None
    desde = pd.Timestamp(args.desde) if args.desde else None

    reporte = ejecutar(
        yahoo_real,
        repositorio_servicio(),
        ParametrosFinancieros(),
        tickers=tickers,
        desde=desde,
        dry_run=args.dry_run,
    )

    print(f"Estado: {reporte.estado} · filas cargadas: {reporte.filas_precios}")
    for ticker, info in reporte.detalle.items():
        print(f"  {ticker}: {info}")

    sys.exit(1 if reporte.estado == "error" else 0)


if __name__ == "__main__":
    main()
