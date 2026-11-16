"""Modelo completo de un día: curva, TIR observada vs. estimada, decisión, duración y DV01.

Entrada: papeles de la tabla "Tasa Fija en Pesos" y la fecha del informe.
Salida: `ResultadoTES` con la calibración, la tabla por papel y los flujos (hoja CalculoCurva).
"""

from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import date

import pandas as pd

from ..config import PB, ParametrosTES
from .calibracion import calibrar
from .flujos import cupon_corrido, flujos
from .modelos import Betas, Calibracion, Papel
from .nelson_siegel import curva, descuento, precio, spot
from .rendimientos import (
    convexidad,
    duracion_macaulay,
    dv01,
    dv01_curva,
    tir,
)
from .senales import senal, umbral_pb


@dataclass(frozen=True)
class ResultadoTES:
    fecha: date
    calibracion: Calibracion
    umbral_pb: float
    regla_umbral: str
    tabla: pd.DataFrame  # una fila por papel
    flujos: pd.DataFrame  # una fila por flujo (como la hoja CalculoCurva)

    def curva(self, dias: int = 10_950) -> pd.DataFrame:
        return curva(self.calibracion.betas, self.calibracion.tau, dias)

    def conteo_senales(self) -> dict[str, int]:
        return self.tabla["senal"].value_counts().to_dict()


def analizar(
    papeles: Sequence[Papel],
    fecha: date,
    params: ParametrosTES | None = None,
    betas_previos: Betas | None = None,
) -> ResultadoTES:
    params = params or ParametrosTES()
    pares = [(p, flujos(p.vencimiento, p.cupon, fecha, params.dias_ano)) for p in papeles]
    arranques = tuple(params.arranques)
    if betas_previos is not None:  # como en el Excel: se parte de los betas del día anterior
        arranques = (betas_previos.como_tupla(), *arranques)
    cal = calibrar(pares, params.tau, arranques, params.ponderacion, params.usar_origen)
    b, tau, n = cal.betas, cal.tau, params.nominal_dv01

    filas, filas_flujos = [], []
    for i, (p, f) in enumerate(pares, start=1):
        p_est = precio(f, b, tau)
        y_obs, y_est = tir(p.precio_sucio, f), tir(p_est, f)
        d_mac = duracion_macaulay(y_obs, f)
        d_inf = p.duracion_informe
        filas.append(
            {
                "bono": i,
                "nemotecnico": p.nemotecnico,
                "tipo": p.tipo,
                "vencimiento": p.vencimiento,
                "origen_tasa": p.origen_tasa,
                "usado_en_curva": params.usar_origen == "todos"
                or p.origen_tasa == params.usar_origen,
                "cupon": p.cupon,
                "n_flujos": len(f.t),
                "plazo_anos": float(f.t[-1]),
                "precio_limpio": p.precio_limpio,
                "precio_sucio": p.precio_sucio,
                "precio_estimado": p_est,
                "error": p.precio_sucio - p_est,
                "tir_observada": y_obs,
                "tir_estimada": y_est,
                "tasa_informe": p.tasa_pub,
                "spread_pb": (y_obs - y_est) / PB,
                "duracion_macaulay": d_mac,
                "duracion_informe": d_inf,
                "duracion_modificada": d_mac / (1 + y_obs),
                "convexidad": convexidad(y_obs, f),
                "dv01_cop": dv01(y_obs, f, n),
                "dv01_curva_cop": dv01_curva(f, b, tau, n),
                # Variante del Excel del grupo: duración del informe (2 decimales) / (1 + TIR)
                "dv01_excel_cop": (
                    None if d_inf is None else d_inf / (1 + y_obs) * p.precio_sucio * PB * n / 100
                ),
                "control_cupon_corrido": (
                    None
                    if p.precio_limpio is None
                    else p.precio_limpio
                    + cupon_corrido(p.vencimiento, p.cupon, fecha, params.dias_ano)
                    - p.precio_sucio
                ),
            }
        )
        for fecha_f, t, m in zip(f.fechas, f.t, f.montos, strict=True):
            filas_flujos.append(
                {
                    "bono": i,
                    "nemotecnico": p.nemotecnico,
                    "fecha_flujo": fecha_f,
                    "flujo": float(m),
                    "dias": int(round(t * params.dias_ano)),
                    "anos": float(t),
                    "tasa_spot": spot(float(t), b, tau),
                    "factor_descuento": descuento(float(t), b, tau),
                    "valor_presente": float(m) * descuento(float(t), b, tau),
                }
            )
    tabla = pd.DataFrame(filas)
    u = umbral_pb(tabla["spread_pb"], params.umbral)
    tabla["senal"] = [senal(s, u) for s in tabla["spread_pb"]]
    return ResultadoTES(
        fecha=fecha,
        calibracion=cal,
        umbral_pb=u,
        regla_umbral=str(params.umbral),
        tabla=tabla,
        flujos=pd.DataFrame(filas_flujos),
    )


def sensibilidad(
    papeles: Sequence[Papel], fecha: date, params: ParametrosTES | None = None
) -> pd.DataFrame:
    """Betas y conteo de decisiones por método de calibración y regla de umbral."""
    params = params or ParametrosTES()
    filas = []
    for nombre, cambios in (
        ("Excel (todos, sin ponderar)", {}),
        ("Ponderada por duración", {"ponderacion": "duracion"}),
        ("Solo SEN", {"usar_origen": "SEN"}),
    ):
        for regla in ("sigma", "sigma_robusta", 5.0, 10.0, 20.0):
            r = analizar(papeles, fecha, replace(params, umbral=regla, **cambios))
            c = r.conteo_senales()
            b = r.calibracion.betas
            filas.append(
                {
                    "calibracion": nombre,
                    "umbral": regla,
                    "umbral_pb": r.umbral_pb,
                    "b0": b.b0,
                    "b1": b.b1,
                    "b2": b.b2,
                    "sse": r.calibracion.sse,
                    "comprar": c.get("Comprar", 0),
                    "vender": c.get("Vender", 0),
                    "mantener": c.get("Mantener", 0),
                }
            )
    return pd.DataFrame(filas)


def sensibilidad_tau(
    papeles: Sequence[Papel],
    fecha: date,
    taus=(0.5, 1, 1.5, 2, 2.5, 3, 3.7, 4.5, 5, 6, 8, 10),
    params: ParametrosTES | None = None,
) -> pd.DataFrame:
    """SSE y betas para distintos τ (la joroba de β2 está en t ≈ 1,7934·τ años)."""
    params = params or ParametrosTES()
    pares = [(p, flujos(p.vencimiento, p.cupon, fecha, params.dias_ano)) for p in papeles]
    filas = []
    for tau in taus:
        c = calibrar(pares, tau, params.arranques, params.ponderacion, params.usar_origen)
        filas.append(
            {
                "tau": tau,
                "joroba_anos": 1.7934 * tau,
                "b0": c.betas.b0,
                "b1": c.betas.b1,
                "b2": c.betas.b2,
                "sse": c.sse,
                "rmse": c.rmse,
            }
        )
    return pd.DataFrame(filas)
