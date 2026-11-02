"""Marca MFT Investments, textos y estilos compartidos de la app."""

from pathlib import Path

import streamlit as st

AVISO_ACADEMICO = (
    "Ejercicio académico. Este material no constituye asesoría de inversión ni "
    "una recomendación de compra o venta de valores."
)

ESTATICO = Path(__file__).resolve().parent.parent / "static"
LOGO = str(ESTATICO / "logo_mft.png")
ICONO = str(ESTATICO / "icono_mft.png")

# Colores del logo (de izquierda a derecha en las barras).
COLORES_MARCA = ["#e8761e", "#1fa79a", "#e9a93a", "#8a5cf5"]

_CSS = f"""
<style>
h1, h2, h3 {{ letter-spacing: 0.01em; }}
hr {{ border: none; height: 2px;
  background: linear-gradient(90deg, {", ".join(COLORES_MARCA)}); opacity: 0.55; }}
[data-testid="stRadio"] label[data-baseweb="radio"] {{
  align-items: flex-start; padding: 0.35rem 0; }}
[data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child {{ margin-top: 0.2rem; }}
[data-testid="stSidebar"] {{ border-right: 1px solid #2a2530; }}
</style>
"""


def configurar_pagina(titulo: str) -> None:
    """`set_page_config` con el ícono de la marca + logo + estilos. Llamar primero."""
    st.set_page_config(page_title=f"{titulo} · MFT Investments", page_icon=ICONO)
    st.logo(LOGO, icon_image=ICONO, size="large")
    st.markdown(_CSS, unsafe_allow_html=True)


def logo_grande() -> None:
    """Logo completo, centrado y grande (pantalla de inicio)."""
    _, centro, _ = st.columns([1, 6, 1])
    centro.image(LOGO, use_container_width=True)


def pie_de_pagina() -> None:
    st.divider()
    st.caption(f"MFT Investments · Quantitative Research & Asset Management. {AVISO_ACADEMICO}")
