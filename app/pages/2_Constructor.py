"""Constructor de portafolio: selección de activos, cálculo y guardado (E09)."""

import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402
from ui.auth import cliente_sesion_actual, requerir_sesion  # noqa: E402
from ui.constructor import armar_registro_portafolio  # noqa: E402
from ui.estilos import configurar_pagina, pie_de_pagina  # noqa: E402
from ui.graficos import figura_composicion, figura_frontera  # noqa: E402

from roboadvisor.config import ParametrosFinancieros  # noqa: E402
from roboadvisor.core.cuestionario import PERFILES  # noqa: E402
from roboadvisor.core.markowitz import (  # noqa: E402
    cal,
    frontera,
    min_varianza,
    portafolios_aleatorios,
    rama_ineficiente,
    tangente,
    w_max_efectivo,
    w_min_efectivo,
)
from roboadvisor.core.portafolio_completo import componer, escenarios_por_a  # noqa: E402
from roboadvisor.core.retornos import estimar, retornos_diarios  # noqa: E402
from roboadvisor.core.riesgo import beta_portafolio, betas, duration_portafolio  # noqa: E402
from roboadvisor.data.repositorio_mercado import RepositorioMercado  # noqa: E402
from roboadvisor.data.repositorio_usuario import RepositorioUsuario  # noqa: E402

PARAMS = ParametrosFinancieros()
EJEMPLO_DIVERSIFICADO = ["SPY", "EFA", "EMB", "LQD", "VNQ", "GLD"]

configurar_pagina("Constructor")
requerir_sesion()

cliente = cliente_sesion_actual()
repo_usuario = RepositorioUsuario(cliente)
repo_mercado = RepositorioMercado(cliente)

st.title("Construcción de portafolio")

encuesta = repo_usuario.obtener_encuesta()
if encuesta is None:
    st.info(
        "Antes de construir tu portafolio necesitamos conocer tu perfil de riesgo: "
        "son nueve preguntas breves y nos permiten ajustar la propuesta a tu forma "
        "de invertir."
    )
    if st.button("Conocer mi perfil de riesgo", type="primary"):
        st.switch_page("pages/1_Encuesta.py")
    st.stop()

if repo_usuario.obtener_portafolio() is not None:
    st.info(
        "Tu portafolio ya está registrado. Puedes seguir su evolución en la sección de seguimiento."
    )
    if st.button("Ver el seguimiento de mi portafolio", type="primary"):
        st.switch_page("pages/3_Mi_portafolio.py")
    st.stop()

a_usuario = float(encuesta["a"])
perfil_usuario = encuesta["perfil"]
st.caption(f"Perfil: **{perfil_usuario}** · coeficiente de aversión al riesgo A = {a_usuario}.")


@st.cache_data(show_spinner="Optimizando portafolio...")
def _calcular(
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
) -> dict:
    tickers_lista = list(tickers)
    desde = (pd.Timestamp.today() - pd.DateOffset(months=ventana_dias // 21 + 6)).date().isoformat()

    precios = _repo_mercado.precios([*tickers_lista, benchmark], desde)
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


def _etiqueta_activo(a: dict) -> str:
    extra = f", duration {a['duration']}" if a.get("duration") else ""
    return f"{a['ticker']} — {a['nombre']} ({a['clase']}, {a['moneda']}{extra})"


catalogo = repo_mercado.listar_catalogo()
catalogo_por_ticker = {a["ticker"]: a for a in catalogo}
etiquetas_por_ticker = {a["ticker"]: _etiqueta_activo(a) for a in catalogo}
tickers_por_etiqueta = {v: k for k, v in etiquetas_por_ticker.items()}

st.subheader("1. Universo de inversión (3 a 11 activos)")
if st.button("Cargar selección diversificada de referencia"):
    st.session_state["constructor_seleccion"] = [
        etiquetas_por_ticker[t] for t in EJEMPLO_DIVERSIFICADO if t in etiquetas_por_ticker
    ]

seleccion_etiquetas = st.multiselect(
    "Universo de activos (por clase)",
    options=sorted(etiquetas_por_ticker.values()),
    max_selections=PARAMS.n_max_activos,
    select_all=False,  # "Select all" chocaría con el máximo de activos
    key="constructor_seleccion",
)
tickers_elegidos = [tickers_por_etiqueta[e] for e in seleccion_etiquetas]
st.caption(
    f"{len(tickers_elegidos)}/{PARAMS.n_max_activos} activos (mínimo {PARAMS.n_min_activos})"
)

# Límites dinámicos según el número de activos n: el mínimo por activo no puede
# superar 1/n y el máximo no puede ser menor que 1/n (si no, no suman 100 %).
n_ref = max(len(tickers_elegidos), PARAMS.n_min_activos)
tope_min_pct = 100 // n_ref  # piso de 1/n
piso_max_pct = -(-100 // n_ref)  # techo de 1/n
st.session_state["constructor_w_min"] = min(
    max(st.session_state.get("constructor_w_min", int(PARAMS.w_min * 100)), 0), tope_min_pct
)
st.session_state["constructor_w_max"] = min(
    max(st.session_state.get("constructor_w_max", int(PARAMS.w_max * 100)), piso_max_pct), 100
)

col_min, col_max = st.columns(2)
w_min_pct = col_min.slider(
    "Peso mínimo por activo (w_min)",
    min_value=0,
    max_value=max(tope_min_pct, 1),
    step=1,
    format="%d%%",
    key="constructor_w_min",
    help=(
        "Cada activo elegido tendrá al menos este peso en el portafolio de riesgo: obliga a "
        "incluirlos a todos. 0% deja que el optimizador descarte activos. "
        f"Con {n_ref} activos el máximo posible es {tope_min_pct}% (= 1/{n_ref})."
    ),
)
w_max_pct = col_max.slider(
    "Peso máximo por activo (w_max)",
    min_value=piso_max_pct,
    max_value=100,
    step=1,
    format="%d%%",
    key="constructor_w_max",
    help=(
        "Concentración máxima por activo en la optimización de Markowitz. Un tope menor "
        "impone mayor diversificación; 100% elimina la restricción. "
        f"Con {n_ref} activos el mínimo posible es {piso_max_pct}% (= 1/{n_ref}). "
        f"Valor de referencia: {PARAMS.w_max:.0%}."
    ),
)
w_min_usuario = w_min_pct / 100
w_max_usuario = w_max_pct / 100
st.caption(
    f"Los límites se ajustan solos al número de activos ({n_ref}): el mínimo va de 0% a "
    f"{tope_min_pct}% y el máximo de {piso_max_pct}% a 100%."
)

puede_calcular = PARAMS.n_min_activos <= len(tickers_elegidos) <= PARAMS.n_max_activos
if st.button("Optimizar portafolio", disabled=not puede_calcular, type="primary"):
    ultima_fecha = repo_mercado.ultima_fecha_precios()
    rf = repo_mercado.rf_ultima()
    try:
        resultado = _calcular(
            repo_mercado,
            catalogo_por_ticker,
            tuple(sorted(tickers_elegidos)),
            ultima_fecha,
            rf,
            w_max_usuario,
            w_min_usuario,
            PARAMS.ventana_dias,
            PARAMS.min_dias,
            PARAMS.benchmark,
        )
    except ValueError as error:
        st.error(f"No fue posible optimizar el portafolio: {error}")
    except Exception:
        st.error(
            "No fue posible optimizar el portafolio con esta combinación de activos. "
            "Modifique la selección o intente nuevamente en unos segundos."
        )
    else:
        st.session_state["constructor_resultado"] = resultado

resultado = st.session_state.get("constructor_resultado")
if resultado:
    st.subheader("2. Resultados de la optimización")
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
            f"libre de riesgo. El retorno esperado anualizado es de "
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
            st.info(
                f"**Ventana más corta de lo habitual:** se estimó con {est.n_obs} días "
                f"(el estándar es {PARAMS.ventana_dias}) porque "
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
            "activo libre de riesgo). La curva punteada naranja es la **curva de "
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
            f"Ventana de estimación: {PARAMS.ventana_dias} días hábiles (mínimo {PARAMS.min_dias})"
        )
        st.write(f"Días efectivamente utilizados: {est.n_obs}")
        st.write(f"Tasa libre de riesgo: {est.rf:.2%}")
        st.write("Estimador de covarianza: Ledoit-Wolf (shrinkage)")
        if abs(resultado["w_max_usado"] - resultado["w_max_elegido"]) > 1e-9:
            st.write(
                f"w_max solicitado: {resultado['w_max_elegido']:.0%} · "
                f"w_max aplicado: {resultado['w_max_usado']:.0%} "
                "(ajustado a la cota factible; ver advertencia en Composición)"
            )
        else:
            st.write(f"Peso máximo por activo (w_max): {resultado['w_max_usado']:.0%}")
        st.write(f"Fecha de corte de los datos (fecha_base): {resultado['fecha_base']}")

    st.subheader("3. Registro del portafolio")
    confirmar = st.checkbox(
        "Entiendo que el portafolio se registra una única vez y no podrá modificarse."
    )
    if st.button("Confirmar y registrar", type="primary", disabled=not confirmar):
        params_usados = replace(
            PARAMS, w_max=resultado["w_max_usado"], w_min=resultado["w_min_usado"]
        )
        payload = armar_registro_portafolio(
            user_id=st.session_state["user_id"],
            encuesta_id=encuesta["id"],
            a_usado=a_usuario,
            perfil_usado=perfil_usuario,
            est=est,
            port_riesgo=port_tangente,
            port_completo=port_completo,
            params=params_usados,
            fecha_base=resultado["fecha_base"],
        )
        try:
            repo_usuario.guardar_portafolio(payload)
        except ValueError as error:
            st.error(str(error))
        except Exception:
            st.error("No fue posible registrar el portafolio. Intente nuevamente en unos segundos.")
        else:
            del st.session_state["constructor_resultado"]
            st.success("Portafolio registrado.")
            if st.button("Ver seguimiento del portafolio", type="primary"):
                st.switch_page("pages/3_Mi_portafolio.py")

pie_de_pagina()
