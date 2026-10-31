"""Textos y estilos compartidos de la app."""

import streamlit as st

AVISO_ACADEMICO = "Ejercicio académico; no constituye asesoría financiera."


def pie_de_pagina() -> None:
    st.divider()
    st.caption(AVISO_ACADEMICO)
