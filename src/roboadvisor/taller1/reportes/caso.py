"""Caso de referencia del Taller 1: 11 ETF → portafolio de riesgo óptimo → portafolio completo.

Función pura sobre DataFrames (sin red ni Supabase): recibe precios y tasa libre de riesgo y
devuelve todo lo que necesitan el Excel y el PDF. Usa exactamente el motor de la app (`core`).
"""

from dataclasses import dataclass

import pandas as pd

from roboadvisor.taller1.config import UNIVERSO_REFERENCIA, ParametrosFinancieros
from roboadvisor.taller1.core.cuestionario import PERFILES, puntuar
from roboadvisor.taller1.core.markowitz import Portafolio, cal, frontera, min_varianza, tangente
from roboadvisor.taller1.core.portafolio_completo import (
    PortafolioCompleto,
    componer,
    escenarios_por_a,
)
from roboadvisor.taller1.core.retornos import Estimacion, estimar, retornos_diarios
from roboadvisor.taller1.core.riesgo import beta_portafolio, betas, duration_portafolio

# Duration (años) de los ETF de renta fija, tomadas del catálogo `supabase/seed/activos.csv`.
DURATIONS: dict[str, float] = {"LQD": 8.4, "HYG": 3.5, "EMB": 7.0}
BENCHMARK = "ACWI"
VALORES_A = [8, 6, 4, 3, 1]


@dataclass(frozen=True)
class CasoReferencia:
    params: ParametrosFinancieros
    universo: dict[str, str]
    est: Estimacion
    tangente: Portafolio
    min_var: Portafolio
    frontera: pd.DataFrame
    cal_pendiente: float
    rf: float
    escenarios: pd.DataFrame  # una fila por A (8, 6, 4, 3, 1)
    betas: pd.Series  # β de cada ETF de renta variable frente a ACWI
    beta_port: dict
    duration_port: dict
    precios: pd.DataFrame
    ventana: tuple[pd.Timestamp, pd.Timestamp]


def calcular_caso(
    precios: pd.DataFrame, rf: float, params: ParametrosFinancieros | None = None
) -> CasoReferencia:
    """Calcula el caso con el motor de la app. `precios`: fecha × ticker (incluye ACWI)."""
    params = params or ParametrosFinancieros()
    tickers = list(UNIVERSO_REFERENCIA)
    est = estimar(precios[tickers], rf, params.ventana_dias, params.min_dias)
    tang = tangente(est, params.w_max, params.w_min)
    minv = min_varianza(est, params.w_max, params.w_min)
    fr = frontera(est, params.w_max, w_min=params.w_min)
    pendiente, _ = cal(tang, rf)
    esc = escenarios_por_a(tang, rf, VALORES_A)

    ret = (
        retornos_diarios(precios[[*tickers, BENCHMARK]]).dropna(how="any").tail(params.ventana_dias)
    )
    acciones = [t for t in tickers if t not in DURATIONS and t not in ("GLD", "VNQ")]
    b = betas(ret[acciones], ret[BENCHMARK])
    dur = pd.Series(DURATIONS)
    return CasoReferencia(
        params=params,
        universo=dict(UNIVERSO_REFERENCIA),
        est=est,
        tangente=tang,
        min_var=minv,
        frontera=fr,
        cal_pendiente=pendiente,
        rf=rf,
        escenarios=esc,
        betas=b,
        beta_port=beta_portafolio(b, tang.w),
        duration_port=duration_portafolio(dur, tang.w),
        precios=precios,
        ventana=(ret.index[0], ret.index[-1]),
    )


def portafolio_de_voluntario(caso: CasoReferencia, respuestas: dict[str, str]) -> dict:
    """Puntaje → perfil → A → portafolio completo de un voluntario."""
    r = puntuar(respuestas)
    pc: PortafolioCompleto = componer(caso.tangente, caso.rf, r.a)
    return {
        "puntaje": r.puntaje,
        "perfil": r.etiqueta,
        "a": r.a,
        "y": pc.y,
        "peso_rf": pc.peso_rf,
        "retorno": pc.retorno,
        "sigma": pc.sigma,
        "utilidad": pc.utilidad,
    }


TABLA_PERFILES = [(a, b, etiqueta, A) for a, b, _clave, etiqueta, A in PERFILES]


ACCIONES_REFERENCIA = ["QQQ", "SMH", "COLO", "ILF", "EFA", "EEM"]


def escenarios_extendidos(c: CasoReferencia) -> pd.DataFrame:
    """Escenarios por A con lo que pasaría **sin** el tope de 100 % (apalancándose a rf).

    Sin tope: `y = (E(Rp) − rf)/(A·σp²)`, `1 − y < 0` es lo que se pediría prestado,
    `E(Rc) = rf + y(E(Rp) − rf)`, `σc = y·σp` y `U* = rf + Sharpe²/(2A)`.
    """
    e = c.escenarios.copy()
    t = c.tangente
    y = e["y_sin_recorte"]
    e["retorno_sin_tope"] = c.rf + y * (t.retorno - c.rf)
    e["sigma_sin_tope"] = y * t.sigma
    e["utilidad_sin_tope"] = c.rf + t.sharpe**2 / (2 * e["a"])
    e["prestamo_sin_tope"] = (y - 1).clip(lower=0)  # fracción del capital propio que se pediría
    return e


def composicion_completa(c: CasoReferencia, umbral: float = 0.0005) -> pd.DataFrame:
    """Portafolio completo por A: `y*·w_i` para cada activo con peso y `1 − y*` en rf."""
    w = c.tangente.w[c.tangente.w > umbral].sort_values(ascending=False)
    filas = {f"A = {int(r.a)}": [*(r.y * w).tolist(), r.peso_rf] for r in c.escenarios.itertuples()}
    return pd.DataFrame(filas, index=[*w.index, "Libre de riesgo (T-note 10a)"])


def multiplos_referencia(c: CasoReferencia, fundamentales: pd.DataFrame) -> dict:
    """Análisis de múltiplos de las acciones del universo frente al P/E del índice mundial ACWI.

    Usa la última foto semanal de P/E (Yahoo Finance, la misma información que publica
    investing.com). Devuelve la tabla de señales y el portafolio de riesgo ajustado (tilt de
    ±`tilt_multiplos`, renormalizado; no se recalcula Markowitz).
    """
    from roboadvisor.taller1.core.multiplos import peso_ajustado, senales_relativas

    f = fundamentales.copy()
    f["fecha"] = pd.to_datetime(f["fecha"])
    ultima = f.sort_values("fecha").groupby("ticker").tail(1).set_index("ticker")
    fotos = int(f["fecha"].nunique())
    pe_ref = float(ultima.loc[BENCHMARK, "pe"])
    pe = ultima["pe"].reindex(ACCIONES_REFERENCIA)
    senales = senales_relativas(pe, pe_ref, c.params)
    ajustado = peso_ajustado(c.tangente.w, senales, c.params.tilt_multiplos)
    tabla = pd.DataFrame(
        {
            "ticker": [s.ticker for s in senales],
            "pe": [s.pe for s in senales],
            "rendimiento_utilidades": [None if not s.pe else 1 / s.pe for s in senales],
            "pe_relativo": [s.z for s in senales],
            "dividend_yield": ultima["div_yield"].reindex(ACCIONES_REFERENCIA).to_numpy() / 100,
            "senal": [s.senal for s in senales],
            "peso_neutral": c.tangente.w.reindex(ACCIONES_REFERENCIA).to_numpy(),
            "peso_ajustado": ajustado.reindex(ACCIONES_REFERENCIA).to_numpy(),
        }
    )
    return {
        "tabla": tabla,
        "pe_acwi": pe_ref,
        "fecha": ultima.loc[BENCHMARK, "fecha"],
        "fotos": fotos,
        "ajustado": ajustado,
    }


def estadisticas_universo(c: CasoReferencia) -> pd.DataFrame:
    """Por activo (y el portafolio óptimo): retorno medio anual, σ, Sharpe, CAGR y caída máxima.

    Retorno medio = media diaria × 252 (el μ que usa Markowitz); CAGR = crecimiento anual
    compuesto realmente obtenido en la ventana; caída máxima = peor pérdida desde un máximo.
    """
    tickers = list(c.est.tickers)
    # mismos retornos que `estimar` (sin rellenar huecos), para que μ coincida con el de Markowitz
    r = c.precios[tickers].sort_index().pct_change().dropna(how="any").tail(c.est.n_obs)
    r["Óptimo"] = (r[tickers] * c.tangente.w.reindex(tickers).fillna(0)).sum(axis=1)
    valor = (1 + r).cumprod()
    anos = len(r) / 252
    mu = r.mean() * 252
    sigma = r.std(ddof=1) * 252**0.5
    return pd.DataFrame(
        {
            "retorno_medio": mu,
            "sigma": sigma,
            "sharpe": (mu - c.rf) / sigma,
            "cagr": valor.iloc[-1] ** (1 / anos) - 1,
            "caida_maxima": (valor / valor.cummax() - 1).min(),
        }
    )


def optimo_sin_apalancamiento(c: CasoReferencia) -> pd.DataFrame:
    """Para cada A, el punto de máxima utilidad si **no** se puede pedir prestado.

    Conjunto factible: la CAL entre rf y P (y ∈ [0, 1]) más la frontera eficiente a la derecha
    de P. Si y* ≤ 1 el óptimo está en la CAL; si y* > 1 está en la frontera, en un portafolio
    de riesgo más agresivo que P (BKM: CAL "quebrada" cuando no se puede apalancar).
    """
    t = c.tangente
    f = c.frontera[c.frontera["sigma"] >= t.sigma - 1e-9]
    filas = []
    for r in c.escenarios.itertuples():
        u_frontera = f["retorno"] - 0.5 * r.a * f["sigma"] ** 2
        i = u_frontera.idxmax()
        if r.y_sin_recorte > 1 and u_frontera[i] > r.utilidad:
            filas.append(
                {"a": r.a, "donde": "frontera", "retorno": f.loc[i, "retorno"],
                 "sigma": f.loc[i, "sigma"], "utilidad": u_frontera[i]}
            )  # fmt: skip
        else:
            filas.append(
                {"a": r.a, "donde": "CAL", "retorno": r.retorno, "sigma": r.sigma,
                 "utilidad": r.utilidad}
            )  # fmt: skip
    return pd.DataFrame(filas)


APALANCADOS = {"TQQQ", "UPRO", "TNA", "TECL", "SOXL", "UCO"}


def sharpe_catalogo_elegible(c: CasoReferencia, catalogo: list[dict]) -> dict:
    """Sharpe máximo con **todos** los activos del catálogo sin apalancamiento y con historia
    completa en la ventana (mismas restricciones). Sirve para justificar el universo de 11."""
    elegibles = [
        a["ticker"]
        for a in catalogo
        if a["activo"]
        and a["rol"] == "invertible"
        and a["ticker"] not in APALANCADOS
        and a["ticker"] in c.precios.columns
        and c.precios[a["ticker"]].first_valid_index() is not None
        and c.precios[a["ticker"]].first_valid_index() <= c.ventana[0]
    ]
    est = estimar(c.precios[elegibles], c.rf, c.params.ventana_dias, c.params.min_dias)
    tang = tangente(est, c.params.w_max, 0.0)  # sin piso: el máximo Sharpe "puro" del catálogo
    sharpe_ind = (est.mu - c.rf) / pd.Series(
        [est.sigma.loc[t, t] ** 0.5 for t in est.tickers], index=est.tickers
    )
    return {"n": len(elegibles), "sharpe": tang.sharpe, "pesos": tang.w[tang.w > 0.005],
            "sharpe_individual": sharpe_ind}  # fmt: skip


def comparacion_piso(c: CasoReferencia) -> pd.DataFrame:
    """Óptimo de los 11 ETF sin piso (w ∈ [0, w_max]) frente al usado (w ∈ [w_min, w_max]).

    Muestra el costo en Sharpe y la ganancia en diversificación de exigir un peso mínimo.
    """
    filas = []
    for nombre, w_min in (("Sin piso", 0.0), ("Con piso", c.params.w_min)):
        p = tangente(c.est, c.params.w_max, w_min)
        r = c.precios[list(c.est.tickers)].sort_index().pct_change().dropna(how="any")
        r = (r.tail(c.est.n_obs) * p.w.reindex(c.est.tickers).fillna(0)).sum(axis=1)
        valor = (1 + r).cumprod()
        filas.append(
            {
                "caso": nombre,
                "w_min": w_min,
                "activos": int((p.w > 0.005).sum()),
                "peso_max": float(p.w.max()),
                "top3": float(p.w.sort_values(ascending=False).head(3).sum()),
                "retorno": p.retorno,
                "sigma": p.sigma,
                "sharpe": p.sharpe,
                "caida_maxima": float((valor / valor.cummax() - 1).min()),
                "pesos": p.w,
            }
        )
    return pd.DataFrame(filas)
