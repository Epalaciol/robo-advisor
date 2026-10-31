"""Estado de avance del usuario y barra lateral."""

import streamlit as st


def estado_usuario(repositorio_usuario) -> str:
    """`'sin_encuesta' | 'sin_portafolio' | 'completo'` según lo que ya guardó el usuario."""
    if repositorio_usuario.obtener_encuesta() is None:
        return "sin_encuesta"
    if repositorio_usuario.obtener_portafolio() is None:
        return "sin_portafolio"
    return "completo"


ETIQUETAS_ESTADO = {
    "sin_encuesta": "Falta la encuesta de aversión al riesgo",
    "sin_portafolio": "Falta armar tu portafolio",
    "completo": "Portafolio activo",
}


def mostrar_barra_lateral(alias: str, estado: str, info_pipeline: dict | None) -> None:
    with st.sidebar:
        st.write(f"**{alias}**")
        st.caption(ETIQUETAS_ESTADO.get(estado, estado))

        st.subheader("Estado de datos")
        if info_pipeline is None:
            st.caption("Sin información de corridas todavía.")
        else:
            st.caption(f"Última corrida: {info_pipeline.get('estado', 'desconocido')}")
            st.caption(f"Último precio: {info_pipeline.get('ultima_fecha_precio', 'sin dato')}")
