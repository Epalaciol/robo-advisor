"""Encuesta de aversión al riesgo: formulario, cálculo de perfil y guardado (E08)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st  # noqa: E402
from ui.auth import cliente_sesion_actual, requerir_sesion  # noqa: E402
from ui.encuesta import construir_payload_encuesta  # noqa: E402
from ui.estilos import configurar_pagina, pie_de_pagina  # noqa: E402
from ui.graficos import figura_utilidad_vs_sigma  # noqa: E402

from roboadvisor.core.cuestionario import (  # noqa: E402
    FACTORES_SUGERIDOS,
    OPCIONES_FACTORES,
    PREGUNTAS,
    puntuar,
)
from roboadvisor.data.repositorio_usuario import RepositorioUsuario  # noqa: E402

configurar_pagina("Perfil de riesgo")
requerir_sesion()

repositorio = RepositorioUsuario(cliente_sesion_actual())
st.title("Perfil de riesgo del inversionista")


def _mostrar_resultado_existente(encuesta: dict) -> None:
    st.success(
        f"Cuestionario registrado el {encuesta['created_at'][:10]}. "
        "El perfil es definitivo y no admite nueva medición."
    )
    col1, col2, col3 = st.columns(3)
    col1.metric("Puntaje", encuesta["puntaje"])
    col2.metric("Perfil", encuesta["perfil"].replace("_", " ").title())
    col3.metric("Coeficiente A", encuesta["a"])

    st.markdown(
        "El portafolio completo se optimiza bajo utilidad media-varianza, "
        "**U = E(r) − ½·A·σ²**: a mayor coeficiente de aversión al riesgo (`A`), "
        "mayor la penalización de la utilidad por volatilidad (`σ`). La curva es "
        "**ilustrativa** (retorno esperado fijo) y muestra el efecto de su `A`."
    )
    st.plotly_chart(figura_utilidad_vs_sigma(float(encuesta["a"])), use_container_width=True)

    if st.button("Continuar al constructor de portafolio", type="primary"):
        st.switch_page("pages/2_Constructor.py")


def _formulario_nuevo() -> None:
    st.markdown(
        "Cuestionario de nueve preguntas para medir la tolerancia al riesgo. Las "
        "respuestas determinan el perfil del inversionista y el coeficiente de "
        "aversión al riesgo (`A`) con el que se asigna el portafolio completo."
    )

    respuestas: dict[str, str] = {}
    total = len(PREGUNTAS)
    for i, pregunta in enumerate(PREGUNTAS, start=1):
        with st.container(border=True):
            st.markdown(f"**Pregunta {i} de {total}**")
            st.markdown(pregunta.texto)
            seleccion = st.radio(
                label=f"pregunta_{pregunta.id}",
                options=list(pregunta.opciones.keys()),
                format_func=lambda letra, p=pregunta: f"{letra}) {p.opciones[letra]}",
                index=None,
                key=f"radio_{pregunta.id}",
                label_visibility="collapsed",
            )
        if seleccion is not None:
            respuestas[pregunta.id] = seleccion

    st.progress(len(respuestas) / total, text=f"{len(respuestas)} de {total} respondidas")

    st.divider()
    st.subheader("Información complementaria (opcional)")
    st.caption(
        "Variables que permiten analizar los determinantes de la aversión al "
        "riesgo. No se recolecta cédula, teléfono ni nombre completo."
    )
    factores: dict = {}
    for clave in FACTORES_SUGERIDOS:
        etiqueta = clave.replace("_", " ").capitalize()
        seleccion_factor = st.selectbox(
            etiqueta,
            OPCIONES_FACTORES[clave],
            index=None,
            placeholder="Seleccione...",
            key=f"factor_{clave}",
        )
        if seleccion_factor is not None:
            factores[clave] = seleccion_factor

    calcular = st.button("Calcular perfil", type="primary", disabled=len(respuestas) < total)

    if calcular:
        try:
            resultado = puntuar(respuestas)
        except ValueError as error:
            st.error(f"No fue posible calcular el perfil: {error}")
            return

        st.session_state["encuesta_pendiente"] = {
            "resultado": resultado,
            "respuestas": respuestas,
            "factores": factores,
        }

    pendiente = st.session_state.get("encuesta_pendiente")
    if pendiente:
        resultado = pendiente["resultado"]
        st.info(
            f"Puntaje **{resultado.puntaje}** · perfil **{resultado.etiqueta}** "
            f"(A = {resultado.a}). Al confirmar, el resultado queda registrado y no "
            "podrá modificarse."
        )
        col_confirmar, col_cancelar = st.columns(2)
        if col_confirmar.button("Confirmar y guardar", type="primary"):
            user_id = st.session_state["user_id"]
            payload = construir_payload_encuesta(user_id, resultado, pendiente["respuestas"])
            try:
                repositorio.guardar_encuesta(payload)
                repositorio.actualizar_factores(user_id, pendiente["factores"])
            except ValueError as error:
                st.error(str(error))
            except Exception:
                st.error("No fue posible guardar el cuestionario. Intente de nuevo.")
            else:
                del st.session_state["encuesta_pendiente"]
                st.success("Perfil registrado.")
                st.rerun()
        if col_cancelar.button("Cancelar"):
            del st.session_state["encuesta_pendiente"]
            st.rerun()


encuesta_existente = repositorio.obtener_encuesta()
if encuesta_existente:
    _mostrar_resultado_existente(encuesta_existente)
else:
    _formulario_nuevo()

pie_de_pagina()
