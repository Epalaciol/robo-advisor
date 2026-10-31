"""Encuesta de aversión al riesgo — placeholder (se implementa en E08)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st  # noqa: E402
from ui.auth import requerir_sesion  # noqa: E402
from ui.estilos import pie_de_pagina  # noqa: E402

st.set_page_config(page_title="Encuesta", page_icon="📝")
requerir_sesion()

st.title("Encuesta de aversión al riesgo")
st.info("Próximamente (E08).")
pie_de_pagina()
