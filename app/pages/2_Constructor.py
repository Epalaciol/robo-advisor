"""Constructor de portafolio: selección de activos, cálculo y guardado (E09)."""

import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402
from ui.auth import cliente_sesion_actual, requerir_sesion  # noqa: E402
from ui.constructor import armar_registro_portafolio  # noqa: E402
from ui.estilos import pie_de_pagina  # noqa: E402
from ui.graficos import figura_composicion, figura_frontera  # noqa: E402

from roboadvisor.config import ParametrosFinancieros  # noqa: E402
from roboadvisor.core.markowitz import (  # noqa: E402
    cal,
    frontera,
    min_varianza,
    portafolios_aleatorios,
    rama_ineficiente,
    tangente,
    w_max_efectivo,
)
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
    if st.button("Ir a la encuesta", type="primary"):
        st.switch_page("pages/1_Encuesta.py")
    st.stop()

if repo_usuario.obtener_portafolio() is not None:
    st.info("Ya tienes un portafolio guardado. No se puede armar otro.")
    if st.button("Ir a Mi portafolio", type="primary"):
        st.switch_page("pages/3_Mi_portafolio.py")
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

    w_max_usado, _ = w_max_efectivo(w_max, len(tickers_lista))

    port_min_var = min_varianza(est, w_max)
    port_tangente = tangente(est, w_max)
    front = frontera(est, w_max)
    rama_no_eficiente = rama_ineficiente(est, w_max)
    nube = portafolios_aleatorios(est, w_max)
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
        "rama_ineficiente": rama_no_eficiente,
        "nube": nube,
        "cal_pendiente": pendiente,
        "cal_intercepto": intercepto,
        "w_max_elegido": w_max,
        "w_max_usado": w_max_usado,
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
    f"{len(tickers_elegidos)}/{PARAMS.n_max_activos} seleccionados (mínimo {PARAMS.n_min_activos})"
)

w_max_pct = st.slider(
    "Tope máximo por activo",
    min_value=10,
    max_value=100,
    value=int(PARAMS.w_max * 100),
    step=5,
    format="%d%%",
    help=(
        "Qué tanto puede concentrarse Markowitz en un solo activo. Más bajo = más "
        "diversificado (obligado); 100% = sin tope, puede poner todo en 1-2 activos "
        f"si eso maximiza el Sharpe. Valor por defecto del taller: {PARAMS.w_max:.0%}."
    ),
)
w_max_usuario = w_max_pct / 100

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
            w_max_usuario,
            PARAMS.ventana_meses,
            PARAMS.min_meses,
            PARAMS.benchmark,
        )
    except ValueError as error:
        st.error(f"No se pudo calcular: {error}")
    except Exception:
        st.error(
            "No se pudo calcular el portafolio con esta combinación de activos. "
            "Prueba quitando o cambiando alguno, o inténtalo de nuevo en unos segundos."
        )
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
        st.markdown(
            f"### En palabras simples\n"
            f"De cada \\$100 que inviertas, **\\${port_completo.y * 100:,.0f} van a activos "
            f"con riesgo** (acciones, bonos, oro...) y **\\${port_completo.peso_rf * 100:,.0f} "
            f"se guardan en algo seguro**. Con esa mezcla, en un año típico esperarías ganar "
            f"alrededor de **{port_completo.retorno:.1%}**, aunque el valor real puede subir o "
            f"bajar unos **{port_completo.sigma:.1%}** respecto a ese promedio — así de "
            f'"movido" es este portafolio.'
        )

        col1, col2, col3 = st.columns(3)
        col1.metric("% en riesgo (y*)", f"{port_completo.y:.1%}")
        col1.caption("Qué parte de tu plata va a activos con riesgo vs. algo seguro.")
        col2.metric("Retorno esperado", f"{port_completo.retorno:.1%}")
        col2.caption("Ganancia promedio esperada por año. No está garantizada.")
        col3.metric("σ — qué tan movido", f"{port_completo.sigma:.1%}")
        col3.caption("Qué tanto puede variar el valor de un año a otro.")

        with st.expander("Ver también: Sharpe y Utilidad (métricas técnicas)"):
            col4, col5 = st.columns(2)
            col4.metric("Sharpe (riesgo)", f"{port_tangente.sharpe:.2f}")
            col4.caption("Ganancia extra por cada unidad de riesgo tomado. Más alto es mejor.")
            col5.metric("Utilidad", f"{port_completo.utilidad:.4f}")
            col5.caption(
                "Puntaje interno que combina tu ganancia esperada y tu tolerancia al riesgo; "
                "solo sirve para comparar opciones, no tiene una unidad propia."
            )

        if port_completo.apalancamiento_requerido:
            st.warning(
                "Tu perfil de riesgo pediría invertir más del 100% en activos con riesgo "
                "(pedir prestado para invertir más). Por seguridad, se recortó a un máximo "
                "de 100%: no se pide dinero prestado."
            )
        if port_tangente.advertencia:
            st.warning(port_tangente.advertencia)

    with tab_composicion:
        w_max_elegido = resultado["w_max_elegido"]
        w_max_usado = resultado["w_max_usado"]
        st.caption(
            "Cada barra representa el 100% de tu plata: el ancho de cada color es "
            "la parte que le toca a ese activo."
        )

        if abs(w_max_usado - w_max_elegido) > 1e-9:
            st.warning(
                f"**Pediste un tope de {w_max_elegido:.0%}**, pero con "
                f"{len(port_tangente.w)} activos elegidos el mínimo matemáticamente "
                f"posible es **{w_max_usado:.0%}** (= 1/{len(port_tangente.w)}: si "
                "cada uno pesara menos que eso, no alcanzaría para sumar 100%). "
                f"Se usó **{w_max_usado:.0%}** en este cálculo — no fue elegido por "
                "la optimización, es un límite matemático con pocos activos. Para "
                "que tu tope de {:.0%} sí se respete, elige más activos.".format(w_max_elegido)
            )
        else:
            st.info(
                f"**Regla que elegiste:** ningún activo puede pesar más de "
                f"**{w_max_usado:.0%}** de la parte de riesgo (evita que Markowitz "
                'concentre todo en 1 o 2 activos; ajustable arriba, en "Tope máximo '
                'por activo"). Si un activo llega justo a ese número, es porque tocó '
                'el tope — no porque sea la "mejor" combinación matemática pura.'
            )

        activos_en_el_tope = [t for t, w in port_tangente.w.items() if w >= w_max_usado - 1e-6]
        if activos_en_el_tope:
            st.caption(f"🔒 En el tope ({w_max_usado:.0%}): {', '.join(activos_en_el_tope)}")

        st.write("**Solo la parte de riesgo**")
        st.plotly_chart(
            figura_composicion(port_tangente.w, "Portafolio de riesgo (100%)"),
            use_container_width=True,
        )
        st.dataframe(port_tangente.w.rename("peso").to_frame().style.format("{:.2%}"))

        st.write("**Tu plata completa (riesgo + seguro)**")
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
            "Cómo leerlo: la nube de puntitos tenues son miles de combinaciones "
            "posibles entre tus activos — casi todas **no son eficientes** (para ese "
            "riesgo, se podría ganar más). La línea gris curva conecta las mejores "
            "combinaciones posibles: la **frontera eficiente**; su continuación "
            "punteada hacia abajo es la rama dominada (la misma matemática, pero del "
            'lado malo) — juntas forman la clásica "bala" de Markowitz, con la '
            "mínima varianza como punta. Los puntos grises marcados son tus activos "
            "individuales. La línea punteada clara es la CAL (mezcla la frontera con "
            "algo seguro). La curva punteada naranja es **tu curva de indiferencia**: "
            "todos los puntos ahí te dan la misma utilidad; toca la CAL exactamente en "
            "tu portafolio, porque ese es — dado tu nivel de aversión al riesgo — el "
            "mejor punto alcanzable sobre la CAL. El **diamante naranja es tu "
            "portafolio real** — mientras más a la derecha, más riesgo; mientras más "
            "arriba, más ganancia esperada."
        )
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
            ),
            use_container_width=True,
        )

    with tab_riesgo:
        if resultado["betas"].empty:
            st.caption("Sin activos de renta variable (acciones) seleccionados.")
        else:
            st.write("**Beta — qué tan fuerte se mueve cada acción frente al mercado global**")
            st.caption(
                "Beta = 1: se mueve igual que el mercado (ACWI). Beta > 1: se mueve más "
                "fuerte (más riesgoso). Beta < 1: se mueve menos (más tranquilo)."
            )
            st.dataframe(resultado["betas"].rename("beta").to_frame().style.format("{:.2f}"))
            beta_normalizada = resultado["beta_portafolio"]["beta_normalizada"]
            st.metric("Beta de tu portafolio", f"{beta_normalizada:.2f}")

        if resultado["duration"].empty:
            st.caption("Sin activos de renta fija (bonos) seleccionados.")
        else:
            st.write("**Duration — qué tan sensible es cada bono a cambios en las tasas**")
            st.caption(
                "En años: a mayor duration, más le afecta el precio del bono cuando suben "
                "o bajan las tasas de interés. Un bono con duration 8 es más sensible que "
                "uno con duration 3."
            )
            st.dataframe(resultado["duration"].rename("duration").to_frame().style.format("{:.2f}"))
            st.metric(
                "Duration de tu portafolio (parte de renta fija)",
                f"{resultado['duration_portafolio']['duration_rf_normalizada']:.2f}",
            )

    with tab_supuestos:
        st.write(f"Ventana: {PARAMS.ventana_meses} meses (mínimo {PARAMS.min_meses})")
        st.write(f"Meses efectivamente usados: {est.n_meses}")
        st.write(f"Tasa libre de riesgo: {est.rf:.2%}")
        st.write("Shrinkage de covarianza: Ledoit-Wolf")
        if abs(resultado["w_max_usado"] - resultado["w_max_elegido"]) > 1e-9:
            st.write(
                f"Tope por activo (w_max) elegido: {resultado['w_max_elegido']:.0%} — "
                f"tope realmente usado: {resultado['w_max_usado']:.0%} "
                "(ajustado al mínimo matemático posible, ver advertencia arriba)"
            )
        else:
            st.write(f"Tope por activo (w_max): {resultado['w_max_usado']:.0%} (elegido por ti)")
        st.write(f"Fecha de datos (fecha_base): {resultado['fecha_base']}")

    st.subheader("3. Guardar")
    confirmar = st.checkbox(
        "Entiendo que el portafolio se guarda una sola vez y no se puede editar."
    )
    if st.button("Confirmar y guardar", type="primary", disabled=not confirmar):
        params_usados = replace(PARAMS, w_max=resultado["w_max_usado"])
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
            st.error("No se pudo guardar el portafolio. Inténtalo de nuevo en unos segundos.")
        else:
            del st.session_state["constructor_resultado"]
            st.success("¡Portafolio guardado!")
            if st.button("Ver mi portafolio", type="primary"):
                st.switch_page("pages/3_Mi_portafolio.py")

pie_de_pagina()
