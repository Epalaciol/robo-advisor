"""Estado de avance del usuario y barra lateral."""

import streamlit as st

from .estilos import barra_superior


def estado_usuario(repositorio_usuario) -> str:
    """`'sin_encuesta' | 'sin_portafolio' | 'completo'` según lo que ya guardó el usuario."""
    if repositorio_usuario.obtener_encuesta() is None:
        return "sin_encuesta"
    if repositorio_usuario.obtener_portafolio() is None:
        return "sin_portafolio"
    return "completo"


ETIQUETAS_ESTADO = {
    "sin_encuesta": "Pendiente: perfil de riesgo",
    "sin_portafolio": "Pendiente: construcción de portafolio",
    "completo": "Portafolio constituido",
}


def bloque_usuario(alias: str, estado: str | None = None) -> None:
    """Usuario en sesión: bloque en la barra lateral y chip arriba a la derecha."""
    correo = st.session_state.get("correo", "")
    barra_superior(alias, correo)
    with st.sidebar:
        st.markdown(f"**{alias}**")
        if correo:
            st.markdown(
                f'<div style="font-size:0.8rem;opacity:0.7">{correo}</div>', unsafe_allow_html=True
            )
        if estado:
            st.caption(ETIQUETAS_ESTADO.get(estado, estado))
        if correo and st.button("Cerrar sesión", key="cerrar_sesion_lateral", width="stretch"):
            from .auth import cerrar_sesion

            cerrar_sesion()
            st.switch_page("Inicio.py")


def mostrar_usuario_en_barra() -> None:
    """Para las páginas protegidas: busca el alias y el estado del usuario y los muestra."""
    from roboadvisor.data.repositorio_usuario import RepositorioUsuario

    from .auth import cliente_sesion_actual

    repositorio = RepositorioUsuario(cliente_sesion_actual())
    perfil = repositorio.obtener_perfil()
    bloque_usuario(perfil["alias"] if perfil else "—", estado_usuario(repositorio))


def mostrar_barra_lateral(alias: str, estado: str, info_pipeline: dict | None) -> None:
    bloque_usuario(alias, estado)
    with st.sidebar:
        st.subheader("Estado de los datos de mercado")
        if info_pipeline is None:
            st.caption("Sin registro de actualizaciones.")
        else:
            st.caption(f"Última actualización: {info_pipeline.get('estado', 'desconocido')}")
            st.caption(f"Último precio: {info_pipeline.get('ultima_fecha_precio', 'sin dato')}")
