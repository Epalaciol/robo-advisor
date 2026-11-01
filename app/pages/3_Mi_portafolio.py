"""Mi portafolio: seguimiento, comportamiento y recomendaciones (E10)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402
from ui.auth import cliente_sesion_actual, requerir_sesion  # noqa: E402
from ui.estilos import pie_de_pagina  # noqa: E402
from ui.graficos import figura_composicion, figura_valor_vs_benchmark  # noqa: E402

from roboadvisor.config import ParametrosFinancieros  # noqa: E402
from roboadvisor.data.cliente import modo_mock_activo  # noqa: E402
from roboadvisor.data.repositorio_mercado import RepositorioMercado  # noqa: E402
from roboadvisor.data.repositorio_usuario import RepositorioUsuario  # noqa: E402
from roboadvisor.data.servicio_portafolio import ResumenPortafolio, construir_resumen  # noqa: E402

PARAMS = ParametrosFinancieros()
AVISO_ACADEMICO = "Ejercicio académico; no constituye asesoría financiera."
ICONOS_SEVERIDAD = {"accion": "🔴", "aviso": "🟡", "info": "🔵"}

st.set_page_config(page_title="Mi portafolio", page_icon="💼")
requerir_sesion()

cliente = cliente_sesion_actual()
repo_usuario = RepositorioUsuario(cliente)
repo_mercado = RepositorioMercado(cliente)

st.title("Mi portafolio")

if repo_usuario.obtener_encuesta() is None:
    st.warning("Primero debes responder la encuesta de aversión al riesgo.")
    if st.button("Ir a la encuesta", type="primary"):
        st.switch_page("pages/1_Encuesta.py")
    st.stop()

if repo_usuario.obtener_portafolio() is None:
    st.warning("Todavía no armas tu portafolio.")
    if st.button("Ir al Constructor", type="primary"):
        st.switch_page("pages/2_Constructor.py")
    st.stop()


@st.cache_data(show_spinner="Calculando el estado de tu portafolio...")
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
    with st.expander("🧪 Solo en modo mock: simular envejecimiento"):
        st.caption(
            "Mueve `fecha_base` de tu portafolio hacia atrás para probar el "
            "seguimiento sin esperar días reales. Solo disponible con `MOCK_DATA=true`."
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
    if st.button("🔄 Actualizar vista"):
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
        "No se pudo calcular el estado de tu portafolio en este momento. "
        "Intenta de nuevo en unos segundos."
    )
    st.stop()

perfil = resumen.perfil
encuesta = resumen.encuesta
portafolio = resumen.portafolio

st.caption(
    f"Perfil **{encuesta['perfil']}** (A = {encuesta['a']}) · creado el "
    f"{portafolio.get('created_at', '—')[:10]} · datos desde **{resumen.fecha_base.date()}** "
    f"({resumen.dias_desde_base} días) · último dato: **{resumen.ultima_fecha_precio or '—'}**"
)

if not resumen.seguimiento.suficiente:
    st.info(
        "Aún no hay suficientes datos nuevos desde que creaste tu portafolio para "
        "mostrar su comportamiento. Vuelve en unos días — por ahora, esta es tu "
        "composición."
    )
    st.subheader("Composición")
    st.plotly_chart(
        figura_composicion(resumen.pesos_iniciales, "Portafolio de riesgo (al crearlo)"),
        use_container_width=True,
    )
    _debug_envejecimiento_mock(resumen)
    pie_de_pagina()
    st.stop()

tab_composicion, tab_comportamiento, tab_recomendaciones, tab_referencia = st.tabs(
    ["Composición", "Comportamiento", "Recomendaciones", "Referencia de hoy"]
)

with tab_composicion:
    st.caption("Pesos de la parte de riesgo: cómo empezaron vs. cómo están hoy (deriva).")
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(
            figura_composicion(resumen.pesos_iniciales, "Al crearlo"),
            use_container_width=True,
        )
    with col2:
        st.plotly_chart(
            figura_composicion(resumen.pesos_actuales_riesgo, "Hoy (con deriva)"),
            use_container_width=True,
        )
    tabla = pd.DataFrame(
        {
            "inicial": resumen.pesos_iniciales,
            "hoy": resumen.pesos_actuales_riesgo,
        }
    ).fillna(0.0)
    tabla["deriva"] = tabla["hoy"] - tabla["inicial"]
    st.dataframe(tabla.style.format("{:.2%}"))

with tab_comportamiento:
    seg = resumen.seguimiento
    st.plotly_chart(
        figura_valor_vs_benchmark(
            seg.valor,
            resumen.seguimiento_benchmark.valor if resumen.seguimiento_benchmark else None,
            resumen.benchmark,
        ),
        use_container_width=True,
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Retorno acumulado", f"{seg.retorno_acum:.1%}")
    col2.metric(
        "Retorno anualizado",
        f"{seg.retorno_anualizado:.1%}" if seg.retorno_anualizado is not None else "—",
        help="Solo se calcula con al menos 1 año de datos.",
    )
    col3.metric("Volatilidad realizada", f"{seg.vol_realizada:.1%}")
    col4.metric("Max drawdown", f"{seg.max_drawdown:.1%}")

    sharpe_txt = (
        f"{seg.sharpe_realizado:.2f}" if seg.sharpe_realizado is not None else "— (mínimo 60 obs.)"
    )
    st.caption(f"Sharpe realizado: {sharpe_txt}")

    st.markdown("**Esperado (al crear) vs. realizado**")
    st.caption(
        "En periodos cortos no son comparables: lo esperado es un promedio de "
        "largo plazo, no una predicción para pocos días."
    )
    col1, col2 = st.columns(2)
    col1.metric("Retorno esperado (al crear)", f"{resumen.retorno_esperado:.1%}")
    col2.metric("σ esperado (al crear)", f"{resumen.sigma_esperado:.1%}")

    if seg.contribucion is not None:
        st.markdown("**Contribución al valor por activo** (en puntos, sobre base 100)")
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
        st.subheader("Múltiplos (P/E)")
        filas = [
            {
                "ticker": s.ticker,
                "P/E": s.pe,
                "mediana peers": s.mediana_peers,
                "z": s.z,
                "señal": s.senal,
            }
            for s in resumen.senales_multiplos
        ]
        st.dataframe(pd.DataFrame(filas))

with tab_referencia:
    st.caption(
        "El portafolio tangente recalculado **hoy** con los mismos activos y los "
        "datos más recientes — para comparar contra los pesos que guardaste."
    )
    if resumen.tangente_hoy is None:
        st.info("No se pudo recalcular el óptimo de hoy (historia insuficiente).")
    else:
        comparacion = pd.DataFrame(
            {
                "guardado": resumen.pesos_iniciales,
                "óptimo hoy": resumen.tangente_hoy.w,
            }
        ).fillna(0.0)
        st.dataframe(comparacion.style.format("{:.2%}"))
        st.caption(
            f"Sharpe del óptimo de hoy: {resumen.tangente_hoy.sharpe:.2f} · "
            f"σ: {resumen.tangente_hoy.sigma:.1%} · retorno: {resumen.tangente_hoy.retorno:.1%}"
        )

_debug_envejecimiento_mock(resumen)
pie_de_pagina()
