"""Cálculo y vista de resultados de un portafolio (frontera, CAL, y*, composición, beta y duration).

Lo usan el Constructor (al optimizar) y la página de administración (para reconstruir el
portafolio registrado de una persona con sus mismos parámetros y datos). La UI no calcula
finanzas: llama a `core`.
"""

import pandas as pd
import streamlit as st

from roboadvisor.taller1.config import RF_NOMBRE, ParametrosFinancieros
from roboadvisor.taller1.core.cuestionario import PERFILES
from roboadvisor.taller1.core.markowitz import (
    cal,
    frontera,
    min_varianza,
    portafolios_aleatorios,
    rama_ineficiente,
    tangente,
    w_max_efectivo,
    w_min_efectivo,
)
from roboadvisor.taller1.core.portafolio_completo import componer, escenarios_por_a
from roboadvisor.taller1.core.retornos import estimar, retornos_diarios
from roboadvisor.taller1.core.riesgo import beta_portafolio, betas, duration_portafolio
from roboadvisor.taller1.data.repositorio_mercado import RepositorioMercado

from .graficos import figura_composicion, figura_frontera


@st.cache_data(show_spinner="Optimizando portafolio...")
def calcular_resultado(
    _repo_mercado: RepositorioMercado,
    _catalogo_por_ticker: dict,
    tickers: tuple[str, ...],
    ultima_fecha: str | None,
    rf: float,
    w_max: float,
    w_min: float,
    ventana_dias: int,
    min_dias: int,
    benchmark: str,
    hasta: str | None = None,
) -> dict:
    """Optimiza el universo `tickers` (Markowitz, CAL, betas, duration) como el Constructor.

    `hasta`: fecha de corte de los precios (para reconstruir un portafolio ya registrado con los
    datos que tenía su dueño); `None` usa todo lo disponible.
    """
    tickers_lista = list(tickers)
    desde = (pd.Timestamp.today() - pd.DateOffset(months=ventana_dias // 21 + 6)).date().isoformat()

    precios = _repo_mercado.precios([*tickers_lista, benchmark], desde)
    if hasta is not None:
        precios = precios.loc[: pd.Timestamp(hasta)]
    est = estimar(precios[tickers_lista], rf, ventana_dias, min_dias)
    # ETF más joven: su primer dato fija el inicio de la ventana común de todo el portafolio
    primeras = precios[tickers_lista].apply(lambda s: s.first_valid_index())
    ticker_limitante = str(primeras.idxmax())
    inicio_limitante = primeras.max()

    w_max_usado, _ = w_max_efectivo(w_max, len(tickers_lista))
    w_min_usado, _ = w_min_efectivo(w_min, len(tickers_lista))

    port_min_var = min_varianza(est, w_max, w_min)
    port_tangente = tangente(est, w_max, w_min)
    front = frontera(est, w_max, w_min=w_min)
    rama_no_eficiente = rama_ineficiente(est, w_max, w_min=w_min)
    nube = portafolios_aleatorios(est, w_max, w_min=w_min)
    pendiente, intercepto = cal(port_tangente, est.rf)

    retornos = retornos_diarios(precios).tail(est.n_obs)
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
        "rama_ineficiente": rama_no_eficiente,
        "nube": nube,
        "cal_pendiente": pendiente,
        "cal_intercepto": intercepto,
        "w_max_elegido": w_max,
        "w_max_usado": w_max_usado,
        "ventana_acortada": est.n_obs < ventana_dias,
        "ticker_limitante": ticker_limitante,
        "inicio_limitante": pd.Timestamp(inicio_limitante).date().isoformat(),
        "w_min_elegido": w_min,
        "w_min_usado": w_min_usado,
        "betas": betas_series,
        "duration": durations_series,
        "beta_portafolio": beta_port,
        "duration_portafolio": duration_port,
        "fecha_base": est.fecha_fin.date().isoformat(),
    }


def mostrar_resultado(
    resultado: dict, a_usuario: float, params: ParametrosFinancieros, clave: str = "constructor"
) -> None:
    """Pestañas Resumen · Composición · Frontera y CAL · Beta y duration · Metodología."""
    est = resultado["est"]
    port_tangente = resultado["port_tangente"]
    port_min_var = resultado["port_min_var"]
    port_completo = componer(port_tangente, est.rf, a_usuario)

    tab_resumen, tab_composicion, tab_frontera, tab_riesgo, tab_supuestos = st.tabs(
        ["Resumen", "Composición", "Frontera y CAL", "Beta y duration", "Metodología"]
    )

    with tab_resumen:
        st.markdown(
            f"### Síntesis de la asignación\n"
            f"Por cada \\$100 de capital, **\\${port_completo.y * 100:,.0f}** se asignan al "
            f"portafolio de riesgo óptimo y **\\${port_completo.peso_rf * 100:,.0f}** al activo "
            f"libre de riesgo (rinde la tasa del {RF_NOMBRE}, {est.rf:.2%}). "
            f"El retorno esperado anualizado es de "
            f"**{port_completo.retorno:.1%}**, con una volatilidad anualizada de "
            f"**{port_completo.sigma:.1%}**."
        )

        col1, col2, col3 = st.columns(3)
        col1.metric("Asignación a riesgo (y*)", f"{port_completo.y:.1%}")
        col1.caption("Fracción del capital en el portafolio de riesgo; el resto, libre de riesgo.")
        col2.metric("Retorno esperado", f"{port_completo.retorno:.1%}")
        col2.caption("Retorno anualizado esperado. No está garantizado.")
        col3.metric("Volatilidad (σ)", f"{port_completo.sigma:.1%}")
        col3.caption("Desviación estándar anualizada de los retornos del portafolio completo.")

        with st.expander("Métricas técnicas: Sharpe y utilidad"):
            col4, col5 = st.columns(2)
            col4.metric("Sharpe (portafolio de riesgo)", f"{port_tangente.sharpe:.2f}")
            col4.caption("Prima de riesgo por unidad de volatilidad. Mayor es mejor.")
            col5.metric("Utilidad", f"{port_completo.utilidad:.4f}")
            col5.caption(
                "U = E(r) − ½·A·σ². Medida ordinal para comparar alternativas bajo el A "
                "del inversionista; no tiene unidad propia."
            )

        if resultado["ventana_acortada"]:
            st.warning(
                f"**Ventana más corta de lo habitual:** se estimó con {est.n_obs} días "
                f"(el estándar es {params.ventana_dias}) porque "
                f"**{resultado['ticker_limitante']}** solo tiene datos desde "
                f"{resultado['inicio_limitante']} y la estimación usa "
                "el periodo común de todos los activos elegidos."
            )
        if port_completo.apalancamiento_requerido:
            st.warning(
                "El perfil de riesgo implicaría una asignación superior al 100% en el "
                "portafolio de riesgo (apalancamiento). Se restringió a y* = 100%: el "
                "modelo no admite endeudamiento."
            )
        if port_tangente.advertencia:
            st.warning(port_tangente.advertencia)

    with tab_composicion:
        w_max_elegido = resultado["w_max_elegido"]
        w_max_usado = resultado["w_max_usado"]
        st.caption(
            "Cada dona representa el 100% del capital; el tamaño de cada sector es "
            "la ponderación del activo."
        )

        if abs(w_max_usado - w_max_elegido) > 1e-9:
            st.warning(
                f"**El tope solicitado ({w_max_elegido:.0%}) es inviable** con "
                f"{len(port_tangente.w)} activos: el mínimo factible es "
                f"**{w_max_usado:.0%}** (= 1/{len(port_tangente.w)}), pues ponderaciones "
                f"menores no suman 100%. La optimización se ejecutó con {w_max_usado:.0%}; "
                "es una cota matemática, no un resultado del optimizador. Para respetar "
                "un tope de {:.0%}, amplíe el universo de activos.".format(w_max_elegido)
            )
        else:
            st.info(
                f"**Restricción activa:** ningún activo supera **{w_max_usado:.0%}** "
                "del portafolio de riesgo (parámetro `w_max`, ajustable arriba). Un "
                "activo que alcanza exactamente ese peso está en la restricción; no "
                "corresponde al óptimo sin restricciones."
            )

        activos_en_el_tope = [t for t, w in port_tangente.w.items() if w >= w_max_usado - 1e-6]
        if activos_en_el_tope:
            st.caption(f"Activos en el tope ({w_max_usado:.0%}): {', '.join(activos_en_el_tope)}")

        st.write("**Portafolio de riesgo (tangente)**")
        st.plotly_chart(
            figura_composicion(port_tangente.w, "Portafolio de riesgo (100%)"),
            use_container_width=True,
        )
        st.dataframe(port_tangente.w.rename("peso").to_frame().style.format("{:.2%}"))

        st.write("**Portafolio completo (riesgo + libre de riesgo)**")
        pesos_completo_rf = pd.concat(
            [port_completo.pesos_completo, pd.Series({"Libre de riesgo": port_completo.peso_rf})]
        )
        st.plotly_chart(
            figura_composicion(pesos_completo_rf, "Portafolio completo (100%)"),
            use_container_width=True,
        )
        st.dataframe(pesos_completo_rf.rename("peso").to_frame().style.format("{:.2%}"))

    with tab_frontera:
        st.caption(
            "La nube tenue corresponde a combinaciones factibles de los activos "
            "seleccionados, en su mayoría ineficientes. La curva gris es la **frontera "
            "eficiente**; su prolongación punteada es la rama dominada, y juntas "
            'conforman la "bala" de Markowitz, con el portafolio de mínima varianza en '
            "el vértice. Cada punto de color es un activo individual. En la leyenda, "
            "un clic oculta o "
            "muestra una serie y doble clic la aísla; arrastra para acercar y doble "
            "clic en el gráfico restablece la vista. La línea "
            "punteada clara es la **CAL** (combinación del portafolio tangente con el "
            f"activo libre de riesgo: {RF_NOMBRE}, {est.rf:.2%}). La curva punteada "
            "naranja es la **curva de "
            "indiferencia** del inversionista: **toca la CAL en un solo punto (es "
            "tangente)**, que es la mejor mezcla para su A. El **diamante naranja** es "
            "tu portafolio completo. Si ese punto de tangencia quedara más allá del "
            "100% en riesgo (necesitaría endeudarse), se marca con un diamante vacío y "
            "tu portafolio se queda en 100%. Los puntos de colores sobre la CAL muestran "
            "dónde quedaría **el mismo portafolio de riesgo con otros A**."
        )
        ver_curvas_a = st.checkbox(
            "Mostrar también la curva de utilidad de cada A",
            value=False,
            key=f"{clave}_curvas_por_a",
            help="Una curva por perfil (8, 6, 4, 3, 1); cada una es tangente a la CAL.",
        )
        valores_a = [p[4] for p in PERFILES]
        escenarios = escenarios_por_a(port_tangente, est.rf, valores_a)
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
                nube_no_eficientes=resultado["nube"],
                rama_ineficiente=resultado["rama_ineficiente"],
                a_usuario=a_usuario,
                escenarios=escenarios,
                curvas_por_a=ver_curvas_a,
            ),
            use_container_width=True,
            config={"displaylogo": False, "scrollZoom": False},
        )

        st.markdown("**El mismo portafolio de riesgo, con distintos A**")
        st.caption(
            "Todos los perfiles comparten el mismo portafolio tangente y se diferencian en "
            "cuánto se mezcla con el activo libre de riesgo (`y*`). Todos caen sobre la CAL: "
            "más A (más aversión), más libre de riesgo y menos volatilidad."
        )
        nombre_perfil = {p[4]: p[3] for p in PERFILES}
        vista = pd.DataFrame(
            {
                "Perfil": [nombre_perfil[a] for a in escenarios["a"]],
                "A": escenarios["a"],
                "En riesgo (y*)": escenarios["y"],
                "En libre de riesgo": escenarios["peso_rf"],
                "y* sin tope": escenarios["y_sin_recorte"],
                "Retorno esperado": escenarios["retorno"],
                "Volatilidad": escenarios["sigma"],
                "Utilidad": escenarios["utilidad"],
            }
        ).set_index("Perfil")

        def _resaltar_usuario(fila):
            es_usuario = fila["A"] == a_usuario
            return ["font-weight: 700" if es_usuario else ""] * len(fila)

        st.dataframe(
            vista.style.apply(_resaltar_usuario, axis=1).format(
                {
                    "A": "{:g}",
                    "En riesgo (y*)": "{:.1%}",
                    "En libre de riesgo": "{:.1%}",
                    "y* sin tope": "{:.0%}",
                    "Retorno esperado": "{:.1%}",
                    "Volatilidad": "{:.1%}",
                    "Utilidad": "{:.4f}",
                }
            )
        )
        st.caption(
            "**y\\* sin tope** mayor a 100% significa que ese perfil querría endeudarse para "
            "invertir más en el portafolio de riesgo; como no se permite apalancamiento, se "
            "queda en 100% (columna *En riesgo*). Tu fila está en negrita."
        )

    with tab_riesgo:
        if resultado["betas"].empty:
            st.caption("Sin activos de renta variable en la selección.")
        else:
            st.write("**Beta frente al mercado global (ACWI)**")
            st.caption(
                "β = 1: sensibilidad igual a la del mercado. β > 1: amplifica los "
                "movimientos del mercado (mayor riesgo sistemático). β < 1: los atenúa."
            )
            st.dataframe(resultado["betas"].rename("beta").to_frame().style.format("{:.2f}"))
            beta_normalizada = resultado["beta_portafolio"]["beta_normalizada"]
            st.metric("Beta del portafolio (renta variable)", f"{beta_normalizada:.2f}")

        if resultado["duration"].empty:
            st.caption("Sin activos de renta fija en la selección.")
        else:
            st.write("**Duration: sensibilidad a la tasa de interés**")
            st.caption(
                "Medida en años: a mayor duration, mayor variación del precio ante cambios "
                "en las tasas. Una duration de 8 implica aproximadamente el doble de "
                "sensibilidad que una de 4."
            )
            st.dataframe(resultado["duration"].rename("duration").to_frame().style.format("{:.2f}"))
            st.metric(
                "Duration del portafolio (renta fija)",
                f"{resultado['duration_portafolio']['duration_rf_normalizada']:.2f}",
            )

    with tab_supuestos:
        st.write(
            f"Ventana de estimación: {params.ventana_dias} días hábiles (mínimo {params.min_dias})"
        )
        st.write(f"Días efectivamente utilizados: {est.n_obs}")
        st.write(f"Tasa libre de riesgo: {est.rf:.2%} ({RF_NOMBRE}, `^TNX`)")
        st.write("Estimador de covarianza: muestral, retornos diarios × 252 (como en clase)")
        if abs(resultado["w_max_usado"] - resultado["w_max_elegido"]) > 1e-9:
            st.write(
                f"w_max solicitado: {resultado['w_max_elegido']:.0%} · "
                f"w_max aplicado: {resultado['w_max_usado']:.0%} "
                "(ajustado a la cota factible; ver advertencia en Composición)"
            )
        else:
            st.write(f"Peso máximo por activo (w_max): {resultado['w_max_usado']:.0%}")
        st.write(f"Fecha de corte de los datos (fecha_base): {resultado['fecha_base']}")
