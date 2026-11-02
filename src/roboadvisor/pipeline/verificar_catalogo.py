"""Verificación inicial del catálogo (antes de cargar la historia completa).

Para cada ticker `activo = true` descarga su historia disponible y reporta:
sin datos, historia corta (`< ventana_meses` meses) o última fecha vieja.
Con `--aplicar` marca `activo = false` en Supabase a los que fallan, pidiendo
confirmación interactiva. Ver docs/04 §Verificación inicial del catálogo.
"""

import argparse

import pandas as pd

from roboadvisor.config import ParametrosFinancieros
from roboadvisor.data import yahoo as yahoo_real
from roboadvisor.data.repositorio import repositorio_servicio

DIAS_STALE_VERIFICACION = 10


def verificar(
    yahoo,
    tickers: list[str],
    params: ParametrosFinancieros,
    fecha_corrida: pd.Timestamp | None = None,
    historico_anios: int = 6,
) -> list[dict]:
    """Descarga la historia disponible de cada ticker y clasifica su estado."""
    fecha_corrida = fecha_corrida or pd.Timestamp.today().normalize()
    desde = fecha_corrida - pd.DateOffset(years=historico_anios)

    reportes = []
    for ticker in tickers:
        try:
            df = yahoo.descargar_precios([ticker], desde)
        except Exception as error:  # noqa: BLE001 - se reporta y se sigue con los demás
            reportes.append({"ticker": ticker, "estado": "sin_datos", "motivo": str(error)})
            continue

        df = df[df["ticker"] == ticker] if not df.empty else df
        if df.empty:
            reportes.append({"ticker": ticker, "estado": "sin_datos", "motivo": "Sin precios"})
            continue

        meses_disponibles = df["fecha"].dt.to_period("M").nunique()
        ultima_fecha = df["fecha"].max()
        dias_atraso = (fecha_corrida - ultima_fecha).days

        if meses_disponibles < params.ventana_meses:
            reportes.append(
                {
                    "ticker": ticker,
                    "estado": "historia_corta",
                    "motivo": f"Solo {meses_disponibles} meses (< {params.ventana_meses})",
                }
            )
        elif dias_atraso > DIAS_STALE_VERIFICACION:
            reportes.append(
                {
                    "ticker": ticker,
                    "estado": "desactualizado",
                    "motivo": f"Último dato hace {dias_atraso} días",
                }
            )
        else:
            reportes.append({"ticker": ticker, "estado": "ok", "motivo": None})

    return reportes


def main() -> None:
    parser = argparse.ArgumentParser(description="Verifica el catálogo antes de la carga inicial")
    parser.add_argument(
        "--aplicar",
        action="store_true",
        help="Marca activo=false a los fallidos (con confirmación)",
    )
    args = parser.parse_args()

    repositorio = repositorio_servicio()
    activos = repositorio.listar_activos(activos_only=True)
    tickers = [a["ticker"] for a in activos]

    reportes = verificar(yahoo_real, tickers, ParametrosFinancieros())

    fallidos = [r for r in reportes if r["estado"] != "ok"]
    for r in reportes:
        print(f"  {r['ticker']}: {r['estado']}" + (f" — {r['motivo']}" if r["motivo"] else ""))

    if not fallidos:
        print("\nTodos los tickers activos pasaron la verificación.")
        return

    print(f"\n{len(fallidos)} ticker(s) fallaron la verificación.")
    if not args.aplicar:
        print("Vuelve a correr con --aplicar para desactivarlos (pide confirmación).")
        return

    respuesta = (
        input(f"¿Marcar activo=false a {[r['ticker'] for r in fallidos]}? [s/N]: ").strip().lower()
    )
    if respuesta != "s":
        print("Cancelado, no se modificó el catálogo.")
        return

    for r in fallidos:
        repositorio.desactivar_activo(
            r["ticker"], motivo=f"Desactivado por verificar_catalogo: {r['motivo']}"
        )
    print(f"{len(fallidos)} ticker(s) marcados activo=false.")


if __name__ == "__main__":
    main()
