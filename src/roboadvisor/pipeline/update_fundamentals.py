"""Carga semanal de fundamentales (P/E, P/B, EV/EBITDA, div yield) desde Yahoo.

CLI: `python -m roboadvisor.pipeline.update_fundamentals [--dry-run] [--tickers A,B]`.
Muchos ETF no traen P/E: se guarda `NULL`, nunca `0`.
"""

import argparse
import sys
from dataclasses import dataclass, field

import pandas as pd

from roboadvisor.data import yahoo as yahoo_real
from roboadvisor.data.repositorio import repositorio_servicio


@dataclass(frozen=True)
class ReporteCorrida:
    """Resultado de una corrida del pipeline de fundamentales."""

    estado: str  # "ok" | "parcial" | "error"
    filas: int
    detalle: dict = field(default_factory=dict)


def ejecutar(
    yahoo,
    repositorio,
    tickers: list[str] | None = None,
    dry_run: bool = False,
    fecha_corrida: pd.Timestamp | None = None,
) -> ReporteCorrida:
    fecha_corrida = fecha_corrida or pd.Timestamp.today().normalize()

    activos = repositorio.listar_activos(activos_only=True)
    tickers_objetivo = tickers or [a["ticker"] for a in activos]

    filas_validas: list[dict] = []
    detalle: dict = {}
    hubo_error = False

    for ticker in tickers_objetivo:
        try:
            datos = yahoo.descargar_fundamentales(ticker)
        except Exception as error:  # noqa: BLE001 - se reporta y se sigue con los demás
            detalle[ticker] = {"estado": "error", "errores": [str(error)]}
            hubo_error = True
            continue

        if datos is None:
            detalle[ticker] = {"estado": "sin_dato", "errores": []}
            continue

        filas_validas.append(
            {
                "ticker": ticker,
                "fecha": fecha_corrida.date().isoformat(),
                "pe": datos.get("pe"),
                "pb": datos.get("pb"),
                "ev_ebitda": datos.get("ev_ebitda"),
                "div_yield": datos.get("div_yield"),
                "fuente": "yahoo",
            }
        )
        detalle[ticker] = {"estado": "ok", "errores": []}

    filas_cargadas = 0
    if not dry_run:
        filas_cargadas = repositorio.upsert_fundamentales(filas_validas)

    estados = [info["estado"] for info in detalle.values()]
    if hubo_error:
        estado_final = "error"
    elif "error" in estados:
        estado_final = "parcial"
    else:
        estado_final = "ok"

    if not dry_run:
        repositorio.registrar_corrida("fundamentales", estado_final, filas_cargadas, detalle)

    return ReporteCorrida(estado=estado_final, filas=filas_cargadas, detalle=detalle)


def main() -> None:
    parser = argparse.ArgumentParser(description="Carga semanal de fundamentales desde Yahoo")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--tickers")
    args = parser.parse_args()

    tickers = args.tickers.split(",") if args.tickers else None
    reporte = ejecutar(yahoo_real, repositorio_servicio(), tickers=tickers, dry_run=args.dry_run)

    print(f"Estado: {reporte.estado} · filas: {reporte.filas}")
    for ticker, info in reporte.detalle.items():
        print(f"  {ticker}: {info}")

    sys.exit(1 if reporte.estado == "error" else 0)


if __name__ == "__main__":
    main()
