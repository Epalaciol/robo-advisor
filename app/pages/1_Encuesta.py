"""Encuesta de aversión al riesgo: formulario, cálculo de perfil y guardado (E08)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st  # noqa: E402
from ui.auth import cliente_sesion_actual, requerir_sesion  # noqa: E402
from ui.encuesta import construir_payload_encuesta  # noqa: E402
from ui.estilos import pie_de_pagina  # noqa: E402
from ui.graficos import figura_utilidad_vs_sigma  # noqa: E402

from roboadvisor.core.cuestionario import FACTORES_SUGERIDOS, PREGUNTAS, puntuar  # noqa: E402
from roboadvisor.data.repositorio_usuario import RepositorioUsuario  # noqa: E402

st.set_page_config(page_title="Encuesta", page_icon="📝")
requerir_sesion()

repositorio = RepositorioUsuario(cliente_sesion_actual())
st.title("Encuesta de aversión al riesgo")


def _mostrar_resultado_existente(encuesta: dict) -> None:
    st.success(
        f"Ya respondiste la encuesta el {encuesta['created_at'][:10]}. "
        "No se puede repetir."
    )
    col1, col2, col3 = st.columns(3)
    col1.metric("Puntaje", encuesta["puntaje"])
    col2.metric("Perfil", encuesta["perfil"].replace("_", " ").title())
    col3.metric("Coeficiente A", encuesta["a"])

    st.markdown(
        "La utilidad media-varianza que usa el portafolio completo es "
        "**U = E(r) − ½·A·σ²**: a mayor aversión al riesgo (`A`), más penaliza "
        "la utilidad la volatilidad (`σ`) del portafolio. La curva siguiente es "
        "**ilustrativa** (a un retorno esperado fijo) solo para mostrar el efecto de tu `A`."
    )
    st.plotly_chart(figura_utilidad_vs_sigma(float(encuesta["a"])), use_container_width=True)

    if st.button("Ir al Constructor", type="primary"):
        st.switch_page("pages/2_Constructor.py")


def _formulario_nuevo() -> None:
    st.markdown(
        "Responde las 9 preguntas tal como aparecen en el formato del taller. "
        "Tus respuestas determinan tu perfil de inversionista y el coeficiente "
        "de aversión al riesgo (`A`) que usará el portafolio completo."
    )

    with st.form("encuesta"):
        respuestas: dict[str, str] = {}
        for i, pregunta in enumerate(PREGUNTAS, start=1):
            st.markdown(f"**{i}. {pregunta.texto}**")
            opciones = list(pregunta.opciones.items())
            seleccion = st.radio(
                label=f"pregunta_{pregunta.id}",
                options=opciones,
                format_func=lambda o: f"{o[0]}) {o[1]}",
                index=None,
                key=f"radio_{pregunta.id}",
                label_visibility="collapsed",
            )
            if seleccion is not None:
                respuestas[pregunta.id] = seleccion[0]

        st.divider()
        st.subheader("Un poco sobre ti (opcional)")
        st.caption(
            "Ayuda a entender qué explica tu aversión al riesgo. No se recolecta "
            "cédula, teléfono ni nombre completo."
        )
        factores: dict = {}
        for clave in FACTORES_SUGERIDOS:
            etiqueta = clave.replace("_", " ").capitalize()
            if clave == "colchon_emergencia":
                factores[clave] = st.checkbox(etiqueta, key=f"factor_{clave}")
            elif clave == "experiencia_invirtiendo_anios":
                factores[clave] = st.number_input(
                    etiqueta, min_value=0, max_value=80, step=1, key=f"factor_{clave}"
                )
            else:
                factores[clave] = st.text_input(etiqueta, key=f"factor_{clave}")

        calcular = st.form_submit_button("Calcular mi perfil")

    if calcular:
        try:
            resultado = puntuar(respuestas)
        except ValueError as error:
            st.error(f"No se pudo calcular tu perfil: {error}")
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
            f"Tu puntaje es **{resultado.puntaje}**, perfil **{resultado.etiqueta}** "
            f"(A = {resultado.a}). ¿Confirmas y guardas? No podrás repetir la encuesta."
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
                st.error("No se pudo guardar la encuesta. Inténtalo de nuevo en unos segundos.")
            else:
                del st.session_state["encuesta_pendiente"]
                st.success("¡Encuesta guardada!")
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
