"""Acceso a las tablas del Taller 2 en Supabase (prefijo `t2_`, migración 0003).

Escritura: solo con `service_role` (pipeline y comandos de validación).
Lectura: la página pública usa el cliente `anon` (RLS permite SELECT en `t2_*`).
"""

import dataclasses
import datetime as dt

import pandas as pd

from roboadvisor.comun.paginacion import leer_todo

from ..core.analisis import ResultadoTES
from ..core.modelos import Betas
from .informe import Hallazgo, InformeTES


def _f(x):
    return None if x is None or (isinstance(x, float) and pd.isna(x)) else float(x)


class RepositorioTES:
    def __init__(self, cliente):
        self._c = cliente

    # ---------------------------------------------------------------------------- escritura
    def guardar_informe(self, inf: InformeTES, hallazgos: list[Hallazgo], url: str | None = None):
        fecha = inf.fecha.isoformat()
        self._c.table("t2_informes").upsert(
            {
                "fecha": fecha,
                "total_nominal_mm": inf.total_nominal_mm,
                "promedio_var_pb": inf.promedio_var_pb,
                "n_papeles": len(inf.filas),
                "via": inf.via,
                "fuente": inf.fuente,
                "url": url,
                "sha256": inf.sha256,
                "validado": not any(h.nivel == "error" for h in hallazgos),
                "hallazgos": [dataclasses.asdict(h) for h in hallazgos],
            },
            on_conflict="fecha",
        ).execute()
        filas = [
            {
                "fecha": fecha,
                "nemotecnico": f.nemotecnico,
                "tipo": f.a_papel().tipo,
                "vencimiento": f.vencimiento.isoformat(),
                "cupon": f.cupon,
                "valor_nominal_mm": f.valor_nominal_mm,
                "precio_limpio": f.precio_limpio,
                "precio_sucio": f.precio_sucio,
                "duracion": f.duracion,
                "tasa_pub": f.tasa_pub,
                "origen_tasa": f.origen_tasa,
                "tasa_prev": f.tasa_prev,
                "origen_prev": f.origen_prev,
                "var_pb": f.var_pb,
            }
            for f in inf.filas
        ]
        self._c.table("t2_cotizaciones").delete().eq("fecha", fecha).execute()
        self._c.table("t2_cotizaciones").insert(filas).execute()

    def guardar_resultado(self, r: ResultadoTES, params) -> None:
        fecha = r.fecha.isoformat()
        c = r.calibracion
        self._c.table("t2_curvas").upsert(
            {
                "fecha": fecha,
                "b0": c.betas.b0,
                "b1": c.betas.b1,
                "b2": c.betas.b2,
                "tau": c.tau,
                "sse": c.sse,
                "rmse": c.rmse,
                "n_papeles": c.n,
                "usar_origen": c.usar_origen,
                "ponderacion": c.ponderacion,
                "regla_umbral": r.regla_umbral,
                "umbral_pb": r.umbral_pb,
                "convergio": c.convergio,
            },
            on_conflict="fecha",
        ).execute()
        columnas = [
            "nemotecnico",
            "plazo_anos",
            "precio_estimado",
            "tir_observada",
            "tir_estimada",
            "spread_pb",
            "senal",
            "duracion_macaulay",
            "duracion_modificada",
            "convexidad",
            "dv01_cop",
            "dv01_curva_cop",
        ]
        filas = [
            {
                "fecha": fecha,
                **{k: (v if k in ("nemotecnico", "senal") else _f(v)) for k, v in fila.items()},
            }
            for fila in r.tabla[columnas].to_dict(orient="records")
        ]
        self._c.table("t2_resultados").delete().eq("fecha", fecha).execute()
        self._c.table("t2_resultados").insert(filas).execute()

    def registrar_corrida(self, estado: str, modo: str, detalle: dict, iniciado: dt.datetime):
        self._c.table("t2_corridas").insert(
            {
                "iniciado_at": iniciado.isoformat(),
                "terminado_at": dt.datetime.now(dt.UTC).isoformat(),
                "estado": estado,
                "modo": modo,
                "detalle": detalle,
            }
        ).execute()

    # ------------------------------------------------------------------------------ lectura
    def curvas(self) -> pd.DataFrame:
        filas = leer_todo(lambda: self._c.table("t2_curvas").select("*").order("fecha"))
        df = pd.DataFrame(filas)
        if not df.empty:
            df["fecha"] = pd.to_datetime(df["fecha"]).dt.date
        return df

    def fechas(self) -> list[dt.date]:
        df = self.curvas()
        return [] if df.empty else sorted(df["fecha"])

    def betas(self, fecha: dt.date) -> tuple[Betas, float] | None:
        df = self.curvas()
        fila = df[df["fecha"] == fecha] if not df.empty else df
        if fila.empty:
            return None
        f = fila.iloc[0]
        return Betas(float(f["b0"]), float(f["b1"]), float(f["b2"])), float(f["tau"])

    def tabla_dia(self, fecha: dt.date) -> pd.DataFrame:
        """Cotizaciones del informe unidas a los resultados del modelo (una fila por papel)."""
        f = fecha.isoformat()
        cot = pd.DataFrame(
            self._c.table("t2_cotizaciones").select("*").eq("fecha", f).execute().data
        )
        res = pd.DataFrame(self._c.table("t2_resultados").select("*").eq("fecha", f).execute().data)
        if cot.empty or res.empty:
            return pd.DataFrame()
        df = cot.merge(res, on=["fecha", "nemotecnico"])
        df["vencimiento"] = pd.to_datetime(df["vencimiento"]).dt.date
        return df.sort_values(["vencimiento", "nemotecnico"]).reset_index(drop=True)

    def informe(self, fecha: dt.date) -> dict | None:
        datos = self._c.table("t2_informes").select("*").eq("fecha", fecha.isoformat()).execute()
        return datos.data[0] if datos.data else None

    def ultima_corrida(self) -> dict | None:
        datos = (
            self._c.table("t2_corridas")
            .select("*")
            .order("iniciado_at", desc=True)
            .limit(1)
            .execute()
        )
        return datos.data[0] if datos.data else None
