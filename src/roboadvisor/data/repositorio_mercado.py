"""Lectura de datos de mercado (catálogo, precios, rf, fundamentales).

Usa el cliente del usuario autenticado: las tablas de mercado se leen igual
para cualquier usuario (RLS: `authenticated` lee, solo `service_role` escribe).
"""

import pandas as pd

from supabase import Client


class RepositorioMercado:
    def __init__(self, cliente: Client):
        self._cliente = cliente

    def listar_catalogo(self) -> list[dict]:
        """Activos invertibles y activos (excluye benchmark y `activo=false`)."""
        datos = (
            self._cliente.table("activos")
            .select("*")
            .eq("activo", True)
            .eq("rol", "invertible")
            .execute()
            .data
        )
        return sorted(datos, key=lambda a: (a["clase"], a["ticker"]))

    def precios(self, tickers: list[str], desde: str) -> pd.DataFrame:
        """Precios ajustados diarios de `tickers` desde `desde`: `DataFrame[fecha × ticker]`."""
        filas = (
            self._cliente.table("precios")
            .select("ticker, fecha, adj_close")
            .in_("ticker", tickers)
            .gte("fecha", desde)
            .execute()
            .data
        )
        if not filas:
            return pd.DataFrame(columns=tickers)

        df = pd.DataFrame(filas)
        df["fecha"] = pd.to_datetime(df["fecha"])
        return df.pivot(index="fecha", columns="ticker", values="adj_close").sort_index()

    def rf_ultima(self) -> float:
        """Tasa libre de riesgo anual (decimal) de la fecha más reciente."""
        fila = (
            self._cliente.table("tasa_libre_riesgo")
            .select("tasa_anual")
            .order("fecha", desc=True)
            .limit(1)
            .execute()
            .data
        )
        return float(fila[0]["tasa_anual"]) if fila else 0.0

    def fundamentales_ultimos(self, tickers: list[str]) -> pd.DataFrame:
        """Última fila de fundamentales por ticker."""
        filas = (
            self._cliente.table("fundamentales").select("*").in_("ticker", tickers).execute().data
        )
        if not filas:
            return pd.DataFrame(columns=["ticker", "fecha", "pe", "pb", "ev_ebitda", "div_yield"])

        df = pd.DataFrame(filas)
        df["fecha"] = pd.to_datetime(df["fecha"])
        return df.sort_values("fecha").groupby("ticker").tail(1).reset_index(drop=True)

    def ultima_fecha_precios(self) -> str | None:
        """Fecha (ISO) del precio más reciente en toda la tabla; clave de caché."""
        fila = (
            self._cliente.table("precios")
            .select("fecha")
            .order("fecha", desc=True)
            .limit(1)
            .execute()
            .data
        )
        return fila[0]["fecha"] if fila else None
