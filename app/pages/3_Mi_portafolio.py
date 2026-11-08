"""Mi portafolio: seguimiento, comportamiento y recomendaciones (E10)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402
from ui.auth import cliente_sesion_actual, requerir_sesion  # noqa: E402
from ui.estilos import AVISO_ACADEMICO, configurar_pagina, pie_de_pagina  # noqa: E402
from ui.graficos import (  # noqa: E402
    MODO_BASE_100,
    MODO_PORCENTAJE,
    figura_comportamiento,
    figura_composicion,
)

from roboadvisor.config import ParametrosFinancieros  # noqa: E402
from roboadvisor.data.cliente import modo_mock_activo  # noqa: E402
from roboadvisor.data.repositorio_mercado import RepositorioMercado  # noqa: E402
from roboadvisor.data.repositorio_usuario import RepositorioUsuario  # noqa: E402
from roboadvisor.data.servicio_portafolio import ResumenPortafolio, construir_resumen  # noqa: E402

PARAMS = ParametrosFinancieros()
ICONOS_SEVERIDAD = {"accion": "🔴", "aviso": "🟡", "info": "🔵"}

configurar_pagina("Mi portafolio")
requerir_sesion()

cliente = cliente_sesion_actual()
repo_usuario = RepositorioUsuario(cliente)
repo_mercado = RepositorioMercado(cliente)

_perfil_usuario = repo_usuario.obtener_perfil()
_alias = _perfil_usuario["alias"] if _perfil_usuario else ""
st.title(f"Seguimiento de portafolio · {_alias}" if _alias else "Seguimiento de portafolio")

if repo_usuario.obtener_encuesta() is None:
    st.info(
        f"{_alias + ', a' if _alias else 'A'}ún no conocemos tu perfil de riesgo. "
        "Son nueve preguntas "
        "breves sobre cómo vives la incertidumbre al invertir; con tus respuestas "
        "definimos un punto de partida a tu medida. Cuando termines, aquí podrás "
        "ver cómo evoluciona tu portafolio."
    )
    if st.button("Conocer mi perfil de riesgo", type="primary"):
        st.switch_page("pages/1_Encuesta.py")
    st.stop()

if repo_usuario.obtener_portafolio() is None:
    st.info(
        "Ya conocemos tu perfil; el siguiente paso es construir tu portafolio. "
        "Elige los activos que te interesan y calculamos juntos la mejor combinación "
        "para ti. En cuanto lo registres, este espacio mostrará cómo evoluciona."
    )
    if st.button("Construir mi portafolio", type="primary"):
        st.switch_page("pages/2_Constructor.py")
    st.stop()


@st.cache_data(show_spinner="Actualizando seguimiento...")
def _construir(
    _repo_usuario: RepositorioUsuario,
    _repo_mercado: RepositorioMercado,
    user_id: str,
    ultima_fecha_precios: str | None,
) -> ResumenPortafolio:
    return construir_resumen(_repo_usuario, _repo_mercado, PARAMS)


def _debug_envejecimiento_mock(resumen: ResumenPortafolio) -> None:
    """Solo en `MOCK_DATA=true`: mueve `fecha_base` hacia atrás para probar el
    seguimiento sin esperar días reales (mismo proceso que `streamlit run`,
    así que sí afecta el mock en memoria que está sirviendo esta página)."""
    if not modo_mock_activo():
        return
    with st.expander("Modo de demostración: simular antigüedad del portafolio"):
        st.caption(
            "Desplaza `fecha_base` hacia atrás para evaluar el seguimiento sin "
            "esperar días reales. Solo disponible con `MOCK_DATA=true`."
        )
        dias_atras = st.number_input("Días atrás", min_value=1, max_value=365, value=30)
        if st.button("Envejecer portafolio"):
            nueva_fecha_ts = resumen.fecha_base - pd.Timedelta(days=int(dias_atras))
            nueva_fecha = nueva_fecha_ts.date().isoformat()
            cliente.table("portafolios").update({"fecha_base": nueva_fecha}).eq(
                "user_id", st.session_state["user_id"]
            ).execute()
            _construir.clear()
            st.rerun()


col_titulo, col_actualizar = st.columns([3, 1])
with col_actualizar:
    if st.button("Actualizar"):
        _construir.clear()
        st.rerun()

try:
    resumen = _construir(
        repo_usuario,
        repo_mercado,
        st.session_state["user_id"],
        repo_mercado.ultima_fecha_precios(),
    )
except ValueError as error:
    st.error(str(error))
    st.stop()
except Exception:
    st.error(
        "No fue posible actualizar el seguimiento en este momento. "
        "Intente nuevamente en unos segundos."
    )
    st.stop()

perfil = resumen.perfil
encuesta = resumen.encuesta
portafolio = resumen.portafolio

st.caption(
    f"Perfil **{encuesta['perfil']}** (A = {encuesta['a']}) · portafolio armado con datos al "
    f"**{resumen.fecha_base.date()}** ({resumen.dias_desde_base} días atrás) · "
    f"último dato: **{resumen.ultima_fecha_precio or '—'}**"
)

if not resumen.seguimiento.suficiente:
    st.info(
        "Aún no hay observaciones suficientes posteriores a la constitución del "
        "portafolio para medir su desempeño. Se muestra la composición inicial."
    )
    st.subheader("Composición")
    st.plotly_chart(
        figura_composicion(resumen.pesos_iniciales, "Portafolio de riesgo (constitución)"),
        use_container_width=True,
    )
    _debug_envejecimiento_mock(resumen)
    pie_de_pagina()
    st.stop()

tab_comportamiento, tab_composicion, tab_recomendaciones, tab_referencia = st.tabs(
    ["Comportamiento", "Composición", "Recomendaciones", "Referencia a la fecha"]
)

with tab_composicion:
    st.markdown(
        "**Qué es esto.** Al armar el portafolio se compró cada ETF con un peso fijo. "
        "Desde entonces *no se rebalanceó* (nadie vendió ni compró): cada activo sube o "
        "baja por su cuenta, así que su peso cambia: "
        "el activo que rinde mejor pesa más, el que rinde peor pesa menos."
    )
    st.caption(
        "Pesos sobre la parte de riesgo (suman 100 %, sin contar la parte en tasa libre "
        "de riesgo). Solo se muestran los activos que el optimizador sí eligió."
    )
    activos_con_peso = (
        resumen.pesos_iniciales[resumen.pesos_iniciales > 0.0005]
        .sort_values(ascending=False)
        .index.tolist()
    )
    # Mismo orden en ambas dona para que cada activo conserve su color.
    inicial = resumen.pesos_iniciales.reindex(activos_con_peso)
    actual = resumen.pesos_actuales_riesgo.reindex(activos_con_peso).fillna(0.0)
    col1, col2 = st.columns(2)
    col1.plotly_chart(
        figura_composicion(inicial, "Al armar el portafolio"), use_container_width=True
    )
    col2.plotly_chart(figura_composicion(actual, "Hoy (peso actual)"), use_container_width=True)
    retorno_activo = resumen.evolucion_activos.iloc[-1] / 100 - 1
    tabla = pd.DataFrame(
        {
            "Peso al armar": resumen.pesos_iniciales,
            "Peso hoy": resumen.pesos_actuales_riesgo,
            "Retorno del activo desde la fecha base": retorno_activo,
        }
    ).loc[activos_con_peso]
    tabla["Cambio de peso"] = tabla["Peso hoy"] - tabla["Peso al armar"]
    tabla = tabla[
        [
            "Peso al armar",
            "Peso hoy",
            "Cambio de peso",
            "Retorno del activo desde la fecha base",
        ]
    ]
    st.dataframe(
        tabla.style.format(
            {
                "Peso al armar": "{:.1%}",
                "Peso hoy": "{:.1%}",
                "Cambio de peso": "{:+.1%}",
                "Retorno del activo desde la fecha base": "{:+.1%}",
            }
        )
    )
    sin_peso = [t for t in resumen.pesos_iniciales.index if t not in activos_con_peso]
    if sin_peso:
        st.caption(
            f"No se muestran {', '.join(sorted(sin_peso))}: estaban en el universo pero el "
            "optimizador les asignó 0 % al armar el portafolio."
        )

with tab_comportamiento:
    seg = resumen.seguimiento
    st.caption(
        "Cómo ha evolucionado tu portafolio desde la fecha en que se armó, comparado con "
        f"el benchmark ({resumen.benchmark}, mercado global). Es el punto de partida para "
        "entender la pestaña *Composición*."
    )
    col_modo, col_activos = st.columns([2, 2])
    modo = col_modo.radio(
        "Escala",
        [MODO_BASE_100, MODO_PORCENTAJE],
        horizontal=True,
        help="Base 100: el portafolio parte de 100 (115 = ganó 15 %). "
        "Porcentaje: variación acumulada desde la fecha base (+15 % = ganó 15 %).",
    )
    ver_activos = col_activos.checkbox(
        "Mostrar cada activo del portafolio",
        value=True,
        help="Líneas finas: cómo le fue a cada ETF por separado. "
        "Explican por qué el portafolio subió o bajó.",
    )
    activos_con_peso = [t for t, w in resumen.pesos_iniciales.items() if w > 0.0005]
    st.plotly_chart(
        figura_comportamiento(
            seg.valor,
            resumen.seguimiento_benchmark.valor if resumen.seguimiento_benchmark else None,
            resumen.benchmark,
            resumen.evolucion_activos[activos_con_peso] if ver_activos else None,
            modo,
        ),
        use_container_width=True,
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Retorno acumulado", f"{seg.retorno_acum:.1%}")
    col2.metric(
        "Retorno anualizado",
        f"{seg.retorno_anualizado:.1%}" if seg.retorno_anualizado is not None else "—",
        help="Se calcula con al menos 1 año de observaciones.",
    )
    col3.metric("Volatilidad realizada", f"{seg.vol_realizada:.1%}")
    col4.metric("Max drawdown", f"{seg.max_drawdown:.1%}")

    sharpe_txt = (
        f"{seg.sharpe_realizado:.2f}" if seg.sharpe_realizado is not None else "— (mínimo 60 obs.)"
    )
    st.caption(f"Sharpe realizado: {sharpe_txt}")

    st.markdown("**Esperado (a la constitución) vs. realizado**")
    st.caption(
        "En horizontes cortos las métricas no son comparables: el retorno esperado "
        "es un promedio de largo plazo, no un pronóstico de corto plazo."
    )
    col1, col2 = st.columns(2)
    col1.metric("Retorno esperado (constitución)", f"{resumen.retorno_esperado:.1%}")
    col2.metric("σ esperada (constitución)", f"{resumen.sigma_esperado:.1%}")

    if seg.contribucion is not None:
        st.markdown("**Contribución al valor por activo** (puntos, base 100)")
        st.dataframe(seg.contribucion.rename("contribución").to_frame().style.format("{:.2f}"))

with tab_recomendaciones:
    st.caption(AVISO_ACADEMICO)
    for rec in resumen.recomendaciones:
        icono = ICONOS_SEVERIDAD.get(rec.severidad, "ℹ️")
        titulo = f"{icono} {rec.titulo}" + (f" — {rec.ticker}" if rec.ticker else "")
        st.markdown(f"**{titulo}**")
        st.write(rec.detalle)
        with st.expander("Ver números"):
            st.json(rec.datos)
        st.divider()

    if resumen.senales_multiplos:
        st.subheader("Valoración relativa (P/E)")
        filas = [
            {
                "ticker": s.ticker,
                "P/E": s.pe,
                "mediana comparables": s.mediana_peers,
                "z": s.z,
                "señal": s.senal,
            }
            for s in resumen.senales_multiplos
        ]
        st.dataframe(pd.DataFrame(filas))

with tab_referencia:
    st.caption(
        "Portafolio tangente recalculado **a la fecha** con los mismos activos y los "
        "datos más recientes, como referencia frente a las ponderaciones registradas."
    )
    if resumen.tangente_hoy is None:
        st.info("No fue posible recalcular el óptimo a la fecha (historia insuficiente).")
    else:
        comparacion = pd.DataFrame(
            {
                "registrado": resumen.pesos_iniciales,
                "óptimo a la fecha": resumen.tangente_hoy.w,
            }
        ).fillna(0.0)
        comparacion = comparacion[(comparacion > 0.0005).any(axis=1)].sort_values(
            "registrado", ascending=False
        )
        st.dataframe(comparacion.style.format("{:.1%}"))
        st.caption(
            f"Sharpe del óptimo a la fecha: {resumen.tangente_hoy.sharpe:.2f} · "
            f"σ: {resumen.tangente_hoy.sigma:.1%} · retorno: {resumen.tangente_hoy.retorno:.1%}"
        )

_debug_envejecimiento_mock(resumen)
pie_de_pagina()
