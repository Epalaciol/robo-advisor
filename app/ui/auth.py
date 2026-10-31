"""Registro, login/logout y protección de páginas.

Los clientes de datos se construyen **con el JWT del usuario** (`cliente_usuario`)
para que las políticas RLS apliquen; esta app solo usa la clave pública `anon`.
"""

from datetime import UTC, datetime

import streamlit as st

from roboadvisor.data.cliente import cliente_anon, cliente_usuario
from roboadvisor.data.repositorio_usuario import RepositorioUsuario

RANGOS_EDAD = ["25-34", "35-44", "45-54", "55-64", "65-74", "otro"]
MIN_LARGO_CONTRASENA = 8

TEXTO_CONSENTIMIENTO = (
    "Autorizo el tratamiento de mi alias, rango de edad y las respuestas de la "
    "encuesta de aversión al riesgo, únicamente con fines académicos para este "
    "taller de Inversiones (EAFIT). No se recolectan cédula, teléfono ni nombre "
    "completo. Puedo solicitar la eliminación de mis datos en cualquier momento "
    "(habeas data, Ley 1581 de 2012)."
)


def validar_registro(
    correo: str, contrasena: str, alias: str, rango_edad: str, consentimiento: bool
) -> list[str]:
    """Reglas del formulario de registro. Sin efectos de red; fácil de probar."""
    errores = []

    if "@" not in correo or "." not in correo.split("@")[-1]:
        errores.append("Correo inválido")
    if len(contrasena) < MIN_LARGO_CONTRASENA:
        errores.append(f"La contraseña debe tener al menos {MIN_LARGO_CONTRASENA} caracteres")
    if not alias or not alias.strip():
        errores.append("El alias es obligatorio")
    if rango_edad not in RANGOS_EDAD:
        errores.append("Rango de edad inválido")
    if not consentimiento:
        errores.append("Debes aceptar el consentimiento para continuar")

    return errores


def registrar(
    correo: str, contrasena: str, alias: str, rango_edad: str, consentimiento: bool
) -> dict:
    """Crea el usuario en Supabase Auth y su perfil. Lanza `ValueError` si el
    formulario es inválido (mensaje amigable, sin trazas ni claves).
    """
    errores = validar_registro(correo, contrasena, alias, rango_edad, consentimiento)
    if errores:
        raise ValueError("; ".join(errores))

    anon = cliente_anon()
    try:
        resultado = anon.auth.sign_up({"email": correo, "password": contrasena})
    except Exception as error:
        raise ValueError(f"No se pudo registrar: {error}") from error

    if resultado.session is None:
        raise ValueError(
            "Registro creado; confirma tu correo antes de iniciar sesión."
        )

    cliente = cliente_usuario(resultado.session.access_token)
    RepositorioUsuario(cliente).crear_perfil(
        user_id=resultado.user.id,
        alias=alias.strip(),
        edad_rango=rango_edad,
        consentimiento_at=datetime.now(UTC).isoformat(),
    )

    return {
        "user_id": resultado.user.id,
        "access_token": resultado.session.access_token,
        "refresh_token": resultado.session.refresh_token,
    }


def iniciar_sesion(correo: str, contrasena: str) -> dict:
    """Login con correo/contraseña. Lanza `ValueError` con mensaje amigable si falla."""
    anon = cliente_anon()
    try:
        resultado = anon.auth.sign_in_with_password({"email": correo, "password": contrasena})
    except Exception as error:
        raise ValueError("Correo o contraseña incorrectos.") from error

    return {
        "user_id": resultado.user.id,
        "access_token": resultado.session.access_token,
        "refresh_token": resultado.session.refresh_token,
    }


def guardar_sesion(datos: dict) -> None:
    st.session_state["user_id"] = datos["user_id"]
    st.session_state["access_token"] = datos["access_token"]
    st.session_state["refresh_token"] = datos["refresh_token"]


def cerrar_sesion() -> None:
    for clave in ("user_id", "access_token", "refresh_token"):
        st.session_state.pop(clave, None)


def hay_sesion() -> bool:
    return "access_token" in st.session_state


def cliente_sesion_actual():
    """Cliente `anon` + JWT del usuario en sesión, con el token refrescado si venció."""
    cliente = cliente_anon()
    try:
        cliente.auth.set_session(
            st.session_state["access_token"], st.session_state["refresh_token"]
        )
    except Exception as error:
        cerrar_sesion()
        raise ValueError("Tu sesión expiró. Inicia sesión de nuevo.") from error
    return cliente


def requerir_sesion() -> None:
    """Para usar al inicio de cada página protegida: si no hay sesión, redirige a Inicio."""
    if not hay_sesion():
        st.warning("Debes iniciar sesión para ver esta página.")
        st.page_link("Inicio.py", label="Ir a Inicio")
        st.stop()

    try:
        cliente_sesion_actual()
    except ValueError as error:
        st.warning(str(error))
        st.page_link("Inicio.py", label="Ir a Inicio")
        st.stop()
