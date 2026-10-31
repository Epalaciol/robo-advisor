"""Constructor de portafolio: selección de activos, cálculo y guardado (E09)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402
from ui.auth import cliente_sesion_actual, requerir_sesion  # noqa: E402
from ui.constructor import armar_registro_portafolio  # noqa: E402
from ui.estilos import pie_de_pagina  # noqa: E402
from ui.graficos import figura_frontera, figura_pesos  # noqa: E402

from roboadvisor.config import ParametrosFinancieros  # noqa: E402
from roboadvisor.core.markowitz import cal, frontera, min_varianza, tangente  # noqa: E402
from roboadvisor.core.portafolio_completo import componer  # noqa: E402
from roboadvisor.core.retornos import estimar, retornos_mensuales  # noqa: E402
from roboadvisor.core.riesgo import beta_portafolio, betas, duration_portafolio  # noqa: E402
from roboadvisor.data.repositorio_mercado import RepositorioMercado  # noqa: E402
from roboadvisor.data.repositorio_usuario import RepositorioUsuario  # noqa: E402

PARAMS = ParametrosFinancieros()
EJEMPLO_DIVERSIFICADO = ["SPY", "EFA", "EMB", "LQD", "VNQ", "GLD"]

st.set_page_config(page_title="Constructor", page_icon="🧮")
requerir_sesion()

cliente = cliente_sesion_actual()
repo_usuario = RepositorioUsuario(cliente)
repo_mercado = RepositorioMercado(cliente)

st.title("Constructor de portafolio")

encuesta = repo_usuario.obtener_encuesta()
if encuesta is None:
    st.warning("Primero debes responder la encuesta de aversión al riesgo.")
    st.page_link("pages/1_Encuesta.py", label="Ir a la encuesta")
    st.stop()

if repo_usuario.obtener_portafolio() is not None:
    st.info("Ya tienes un portafolio guardado. No se puede armar otro.")
    st.page_link("pages/3_Mi_portafolio.py", label="Ir a Mi portafolio")
    st.stop()

a_usuario = float(encuesta["a"])
perfil_usuario = encuesta["perfil"]
st.caption(f"Tu perfil: **{perfil_usuario}** (A = {a_usuario}) — no editable aquí.")


@st.cache_data(show_spinner="Calculando portafolio óptimo...")
def _calcular(
    _repo_mercado: RepositorioMercado,
    _catalogo_por_ticker: dict,
    tickers: tuple[str, ...],
    ultima_fecha: str | None,
    rf: float,
    w_max: float,
    ventana_meses: int,
    min_meses: int,
    benchmark: str,
) -> dict:
    tickers_lista = list(tickers)
    desde = (pd.Timestamp.today() - pd.DateOffset(months=ventana_meses + 6)).date().isoformat()

    precios = _repo_mercado.precios([*tickers_lista, benchmark], desde)
    est = estimar(precios[tickers_lista], rf, ventana_meses, min_meses)

    port_min_var = min_varianza(est, w_max)
    port_tangente = tangente(est, w_max)
    front = frontera(est, w_max)
    pendiente, intercepto = cal(port_tangente, est.rf)

    retornos = retornos_mensuales(precios).tail(est.n_meses)
    equity_tickers = [t for t in tickers_lista if not _catalogo_por_ticker[t]["es_renta_fija"]]
    rf_tickers = [t for t in tickers_lista if _catalogo_por_ticker[t]["es_renta_fija"]]

    betas_series = pd.Series(dtype=float)
    if equity_tickers and benchmark in retornos.columns:
        betas_series = betas(retornos[equity_tickers], retornos[benchmark])

    durations = {
        t: _catalogo_por_ticker[t]["duration"]
        for t in rf_tickers
        if _catalogo_por_ticker[t].get("duration") is not None
    }
    durations_series = pd.Series(durations, dtype=float)

    beta_port = (
        beta_portafolio(betas_series, port_tangente.w)
        if not betas_series.empty
        else {"beta_normalizada": 0.0, "contribucion_total": 0.0}
    )
    duration_port = (
        duration_portafolio(durations_series, port_tangente.w)
        if not durations_series.empty
        else {"duration_rf_normalizada": 0.0, "contribucion_total": 0.0}
    )

    return {
        "est": est,
        "port_min_var": port_min_var,
        "port_tangente": port_tangente,
        "frontera": front,
        "cal_pendiente": pendiente,
        "cal_intercepto": intercepto,
        "betas": betas_series,
        "duration": durations_series,
        "beta_portafolio": beta_port,
        "duration_portafolio": duration_port,
        "fecha_base": est.fecha_fin.date().isoformat(),
    }


def _etiqueta_activo(a: dict) -> str:
    extra = f", duration {a['duration']}" if a.get("duration") else ""
    return f"{a['ticker']} — {a['nombre']} ({a['clase']}, {a['moneda']}{extra})"


catalogo = repo_mercado.listar_catalogo()
catalogo_por_ticker = {a["ticker"]: a for a in catalogo}
etiquetas_por_ticker = {a["ticker"]: _etiqueta_activo(a) for a in catalogo}
tickers_por_etiqueta = {v: k for k, v in etiquetas_por_ticker.items()}

st.subheader("1. Elige de 3 a 11 activos")
if st.button("Usar ejemplo diversificado"):
    st.session_state["constructor_seleccion"] = [
        etiquetas_por_ticker[t] for t in EJEMPLO_DIVERSIFICADO if t in etiquetas_por_ticker
    ]

seleccion_etiquetas = st.multiselect(
    "Catálogo (agrupado por clase en el nombre)",
    options=sorted(etiquetas_por_ticker.values()),
    max_selections=PARAMS.n_max_activos,
    key="constructor_seleccion",
)
tickers_elegidos = [tickers_por_etiqueta[e] for e in seleccion_etiquetas]
st.caption(
    f"{len(tickers_elegidos)}/{PARAMS.n_max_activos} seleccionados "
    f"(mínimo {PARAMS.n_min_activos})"
)

puede_calcular = PARAMS.n_min_activos <= len(tickers_elegidos) <= PARAMS.n_max_activos
if st.button("Calcular", disabled=not puede_calcular, type="primary"):
    ultima_fecha = repo_mercado.ultima_fecha_precios()
    rf = repo_mercado.rf_ultima()
    try:
        resultado = _calcular(
            repo_mercado,
            catalogo_por_ticker,
            tuple(sorted(tickers_elegidos)),
            ultima_fecha,
            rf,
            PARAMS.w_max,
            PARAMS.ventana_meses,
            PARAMS.min_meses,
            PARAMS.benchmark,
        )
    except ValueError as error:
        st.error(f"No se pudo calcular: {error}")
    else:
        st.session_state["constructor_resultado"] = resultado

resultado = st.session_state.get("constructor_resultado")
if resultado:
    st.subheader("2. Resultados")
    est = resultado["est"]
    port_tangente = resultado["port_tangente"]
    port_min_var = resultado["port_min_var"]
    port_completo = componer(port_tangente, est.rf, a_usuario)

    tab_resumen, tab_composicion, tab_frontera, tab_riesgo, tab_supuestos = st.tabs(
        ["Resumen", "Composición", "Frontera y CAL", "Betas y duration", "Supuestos"]
    )

    with tab_resumen:
        col1, col2, col3 = st.columns(3)
        col1.metric("% en portafolio de riesgo (y*)", f"{port_completo.y:.1%}")
        col2.metric("% libre de riesgo", f"{port_completo.peso_rf:.1%}")
        col3.metric("Sharpe (riesgo)", f"{port_tangente.sharpe:.2f}")

        col4, col5, col6 = st.columns(3)
        col4.metric("Retorno esperado (riesgo)", f"{port_tangente.retorno:.1%}")
        col5.metric("σ (riesgo)", f"{port_tangente.sigma:.1%}")
        col6.metric("Utilidad", f"{port_completo.utilidad:.4f}")

        st.caption(
            f"Retorno esperado (completo): {port_completo.retorno:.1%} · "
            f"σ (completo): {port_completo.sigma:.1%}"
        )

        if port_completo.apalancamiento_requerido:
            st.warning(
                "Tu aversión al riesgo pediría más del 100% en el portafolio de riesgo "
                "(apalancamiento); se recortó a 100% sin apalancamiento."
            )
        if port_tangente.advertencia:
            st.warning(port_tangente.advertencia)

    with tab_composicion:
        st.write("**Portafolio de riesgo**")
        st.dataframe(port_tangente.w.rename("peso").to_frame().style.format("{:.2%}"))
        st.plotly_chart(
            figura_pesos(port_tangente.w, "Pesos del portafolio de riesgo"),
            use_container_width=True,
        )

        st.write("**Portafolio completo (incluye libre de riesgo)**")
        pesos_completo_rf = pd.concat(
            [port_completo.pesos_completo, pd.Series({"Libre de riesgo": port_completo.peso_rf})]
        )
        st.dataframe(pesos_completo_rf.rename("peso").to_frame().style.format("{:.2%}"))
        st.plotly_chart(
            figura_pesos(pesos_completo_rf, "Pesos del portafolio completo"),
            use_container_width=True,
        )

    with tab_frontera:
        st.plotly_chart(
            figura_frontera(
                resultado["frontera"],
                port_min_var,
                port_tangente,
                resultado["cal_pendiente"],
                resultado["cal_intercepto"],
                est.mu,
                est.sigma,
                punto_usuario=(port_completo.sigma, port_completo.retorno),
            ),
            use_container_width=True,
        )

    with tab_riesgo:
        if resultado["betas"].empty:
            st.caption("Sin activos de renta variable seleccionados.")
        else:
            st.write("**Betas vs ACWI**")
            st.dataframe(resultado["betas"].rename("beta").to_frame().style.format("{:.2f}"))
            beta_normalizada = resultado["beta_portafolio"]["beta_normalizada"]
            st.metric("Beta del portafolio", f"{beta_normalizada:.2f}")

        if resultado["duration"].empty:
            st.caption("Sin activos de renta fija seleccionados.")
        else:
            st.write("**Duration**")
            st.dataframe(resultado["duration"].rename("duration").to_frame().style.format("{:.2f}"))
            st.metric(
                "Duration del portafolio (renta fija)",
                f"{resultado['duration_portafolio']['duration_rf_normalizada']:.2f}",
            )

    with tab_supuestos:
        st.write(f"Ventana: {PARAMS.ventana_meses} meses (mínimo {PARAMS.min_meses})")
        st.write(f"Meses efectivamente usados: {est.n_meses}")
        st.write(f"Tasa libre de riesgo: {est.rf:.2%}")
        st.write("Shrinkage de covarianza: Ledoit-Wolf")
        st.write(f"Tope por activo (w_max): {PARAMS.w_max:.0%}")
        st.write(f"Fecha de datos (fecha_base): {resultado['fecha_base']}")

    st.subheader("3. Guardar")
    confirmar = st.checkbox(
        "Entiendo que el portafolio se guarda una sola vez y no se puede editar."
    )
    if st.button("Confirmar y guardar", type="primary", disabled=not confirmar):
        payload = armar_registro_portafolio(
            user_id=st.session_state["user_id"],
            encuesta_id=encuesta["id"],
            a_usado=a_usuario,
            perfil_usado=perfil_usuario,
            est=est,
            port_riesgo=port_tangente,
            port_completo=port_completo,
            params=PARAMS,
            fecha_base=resultado["fecha_base"],
        )
        try:
            repo_usuario.guardar_portafolio(payload)
        except ValueError as error:
            st.error(str(error))
        else:
            del st.session_state["constructor_resultado"]
            st.success("¡Portafolio guardado!")
            st.page_link("pages/3_Mi_portafolio.py", label="Ver mi portafolio")

pie_de_pagina()
