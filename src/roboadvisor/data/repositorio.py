"""Acceso a Supabase para el pipeline (`service_role`, ignora RLS).

Nunca se usa desde la app; solo desde `pipeline/` y scripts de administración.
"""

from datetime import UTC, datetime

import pandas as pd

from roboadvisor.data.cliente import cliente_servicio
from roboadvisor.data.paginacion import leer_todo
from supabase import Client

TAMANO_LOTE_PRECIOS = 500


class Repositorio:
    """Lecturas/escrituras del pipeline sobre las tablas de mercado."""

    def __init__(self, cliente: Client):
        self._cliente = cliente

    def listar_activos(self, activos_only: bool = True) -> list[dict]:
        consulta = self._cliente.table("activos").select("*")
        if activos_only:
            consulta = consulta.eq("activo", True)
        return consulta.execute().data

    def ultima_fecha_por_ticker(self) -> dict[str, pd.Timestamp]:
        filas = leer_todo(
            lambda: (
                self._cliente.table("precios")
                .select("ticker, fecha")
                .order("ticker")
                .order("fecha")
            )
        )
        if not filas:
            return {}
        df = pd.DataFrame(filas)
        maximos = df.groupby("ticker")["fecha"].max()
        return {ticker: pd.Timestamp(fecha) for ticker, fecha in maximos.items()}

    def upsert_precios(self, df: pd.DataFrame, lote: int = TAMANO_LOTE_PRECIOS) -> int:
        if df.empty:
            return 0
        filas = [
            {
                "ticker": fila["ticker"],
                "fecha": pd.Timestamp(fila["fecha"]).date().isoformat(),
                "close": None if pd.isna(fila["close"]) else float(fila["close"]),
                "adj_close": float(fila["adj_close"]),
                "volumen": None if pd.isna(fila["volumen"]) else int(fila["volumen"]),
            }
            for _, fila in df.iterrows()
        ]
        for inicio in range(0, len(filas), lote):
            trozo = filas[inicio : inicio + lote]
            self._cliente.table("precios").upsert(trozo, on_conflict="ticker,fecha").execute()
        return len(filas)

    def upsert_rf(self, df: pd.DataFrame) -> int:
        if df.empty:
            return 0
        filas = [
            {"fecha": pd.Timestamp(fecha).date().isoformat(), "tasa_anual": float(tasa)}
            for fecha, tasa in zip(df["fecha"], df["tasa_anual"], strict=True)
        ]
        self._cliente.table("tasa_libre_riesgo").upsert(filas, on_conflict="fecha").execute()
        return len(filas)

    def upsert_fundamentales(self, filas: list[dict]) -> int:
        if not filas:
            return 0
        self._cliente.table("fundamentales").upsert(filas, on_conflict="ticker,fecha").execute()
        return len(filas)

    def desactivar_activo(self, ticker: str, motivo: str) -> None:
        self._cliente.table("activos").update({"activo": False, "notas": motivo}).eq(
            "ticker", ticker
        ).execute()

    def registrar_corrida(self, tipo: str, estado: str, filas_precios: int, detalle: dict) -> None:
        self._cliente.table("pipeline_runs").insert(
            {
                "tipo": tipo,
                "terminado_at": datetime.now(UTC).isoformat(),
                "estado": estado,
                "filas_precios": filas_precios,
                "detalle": detalle,
            }
        ).execute()


def repositorio_servicio() -> Repositorio:
    """`Repositorio` con `service_role` (ignora RLS); solo para el pipeline."""
    return Repositorio(cliente_servicio())
