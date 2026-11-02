"""Login/registro y enrutamiento según el avance del usuario. Ver E07."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st  # noqa: E402
from ui.auth import (  # noqa: E402
    RANGOS_EDAD,
    TEXTO_CONSENTIMIENTO,
    cerrar_sesion,
    cliente_sesion_actual,
    guardar_sesion,
    hay_sesion,
    iniciar_sesion,
    registrar,
)
from ui.estado import estado_usuario, mostrar_barra_lateral  # noqa: E402
from ui.estilos import configurar_pagina, logo_grande, pie_de_pagina  # noqa: E402

from roboadvisor.config import Settings  # noqa: E402
from roboadvisor.data.cliente import modo_mock_activo  # noqa: E402
from roboadvisor.data.cliente_mock import (  # noqa: E402
    CLAVE_A3,
    CLAVE_PRUEBA,
    CORREO_A3,
    CORREO_PRUEBA,
)
from roboadvisor.data.repositorio_usuario import RepositorioUsuario  # noqa: E402

configurar_pagina("Robo-advisor")


def _mostrar_instrucciones_configuracion() -> None:
    st.title("MFT Investments")
    st.error(
        "Faltan las credenciales de Supabase. Copia `.env.example` a "
        "`.env` y completa `SUPABASE_URL` y `SUPABASE_ANON_KEY` antes de arrancar "
        "la app."
    )


def _pagina_login_registro() -> None:
    logo_grande()
    st.caption(
        "Quantitative Research & Asset Management · Plataforma de asignación de "
        "portafolios bajo el marco media-varianza de Markowitz. Ejercicio académico "
        "(Inversiones, EAFIT); no constituye asesoría de inversión."
    )
    if modo_mock_activo():
        st.info(
            "**Entorno de demostración** (datos en memoria). Usuarios disponibles:\n\n"
            f"- **Perfil de riesgo pendiente** (admin): `{CORREO_PRUEBA}` · "
            f"clave `{CLAVE_PRUEBA}`\n"
            f"- **Construcción de portafolio** (perfil definido, A = 3): "
            f"`{CORREO_A3}` · clave `{CLAVE_A3}`"
        )

    tab_login, tab_registro = st.tabs(["Iniciar sesión", "Crear cuenta"])

    with tab_login:
        with st.form("login"):
            correo = st.text_input("Correo", key="login_correo")
            contrasena = st.text_input("Contraseña", type="password", key="login_contrasena")
            enviado = st.form_submit_button("Iniciar sesión")
        if enviado:
            try:
                datos = iniciar_sesion(correo, contrasena)
                guardar_sesion(datos)
                st.rerun()
            except ValueError as error:
                st.error(str(error))

    with tab_registro:
        with st.form("registro"):
            correo_r = st.text_input("Correo", key="registro_correo")
            contrasena_r = st.text_input(
                "Contraseña (mínimo 8 caracteres)", type="password", key="registro_contrasena"
            )
            alias_r = st.text_input(
                "Alias de usuario",
                key="registro_alias",
                help="Un nombre o apodo; no se requiere el nombre completo.",
            )
            edad_r = st.selectbox("Rango de edad", RANGOS_EDAD, index=1, key="registro_edad")
            st.caption(TEXTO_CONSENTIMIENTO)
            consentimiento_r = st.checkbox(
                "Autorizo el tratamiento de mis datos", key="registro_consiente"
            )
            enviado_r = st.form_submit_button("Crear cuenta")
        if enviado_r:
            try:
                datos = registrar(correo_r, contrasena_r, alias_r, edad_r, consentimiento_r)
                guardar_sesion(datos)
                st.rerun()
            except ValueError as error:
                st.error(str(error))


def _enrutar_segun_estado(estado: str) -> None:
    destinos = {
        "sin_encuesta": "pages/1_Encuesta.py",
        "sin_portafolio": "pages/2_Constructor.py",
        "completo": "pages/3_Mi_portafolio.py",
    }
    st.success("Sesión iniciada.")
    if st.button("Continuar", type="primary"):
        st.switch_page(destinos[estado])
    if st.button("Cerrar sesión"):
        cerrar_sesion()
        st.rerun()


def main() -> None:
    if not modo_mock_activo():
        try:
            Settings()
        except Exception:
            _mostrar_instrucciones_configuracion()
            return

    if not hay_sesion():
        _pagina_login_registro()
        pie_de_pagina()
        return

    try:
        cliente = cliente_sesion_actual()
    except ValueError as error:
        st.warning(str(error))
        _pagina_login_registro()
        pie_de_pagina()
        return

    repositorio = RepositorioUsuario(cliente)
    perfil = repositorio.obtener_perfil()
    alias = perfil["alias"] if perfil else "—"
    estado = estado_usuario(repositorio)

    mostrar_barra_lateral(alias, estado, info_pipeline=repositorio.obtener_estado_pipeline())
    logo_grande()
    st.title(f"Bienvenido, {alias}")
    _enrutar_segun_estado(estado)
    pie_de_pagina()


main()
