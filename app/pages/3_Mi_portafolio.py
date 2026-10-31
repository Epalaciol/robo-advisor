"""Mi portafolio — placeholder (se implementa en E10)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st  # noqa: E402
from ui.auth import requerir_sesion  # noqa: E402
from ui.estilos import pie_de_pagina  # noqa: E402

st.set_page_config(page_title="Mi portafolio", page_icon="💼")
requerir_sesion()

st.title("Mi portafolio")
st.info("Próximamente (E10).")
pie_de_pagina()
