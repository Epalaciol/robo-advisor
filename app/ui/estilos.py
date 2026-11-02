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
.mft-barra {{ display:flex; justify-content:space-between; align-items:center;
  padding: 0 0 0.6rem 0; margin-bottom: 0.8rem; border-bottom: 1px solid #2a2530; }}
.mft-migas {{ display:flex; align-items:center; gap:0.55rem; font-size:0.9rem; }}
.mft-sep {{ opacity:0.35; }}
.mft-pastilla {{ border:1px solid; border-radius:999px; padding:0.05rem 0.55rem;
  font-size:0.68rem; letter-spacing:0.06em; font-weight:600; }}
.mft-usuario {{ display:flex; align-items:center; gap:0.6rem; font-size:0.85rem;
  line-height:1.15; text-align:right; }}
.mft-correo {{ font-size:0.72rem; opacity:0.65; }}
.mft-avatar {{ width:2rem; height:2rem; border-radius:50%; display:flex; align-items:center;
  justify-content:center; font-weight:700; color:#fff;
  background: linear-gradient(135deg, #e8761e, #8a5cf5); }}
[data-testid="stSidebar"] {{ border-right: 1px solid #2a2530; }}
</style>
"""


_CSS_MENU = "<style>" + (ESTATICO / "menu.css").read_text(encoding="utf-8") + "</style>"


def configurar_pagina(titulo: str) -> None:
    """`set_page_config` con el ícono de la marca + logo + estilos. Llamar primero."""
    st.set_page_config(page_title=f"{titulo} · MFT Investments", page_icon=ICONO)
    st.logo(LOGO, icon_image=ICONO, size="large")
    st.markdown(_CSS, unsafe_allow_html=True)
    st.markdown(_CSS_MENU, unsafe_allow_html=True)


def barra_superior(alias: str | None = None, correo: str | None = None) -> None:
    """Barra superior tipo consola: migas de pan, entorno y usuario en sesión."""
    from roboadvisor.data.cliente import modo_mock_activo

    demo = modo_mock_activo()
    pastilla = ("DEMO", "#1fa79a") if demo else ("PRODUCCIÓN", "#e8761e")
    usuario = ""
    if alias:
        inicial = alias.strip()[:1].upper() or "?"
        usuario = (
            f'<span class="mft-usuario"><span class="mft-avatar">{inicial}</span>'
            f"<span><b>{alias}</b>"
            + (f'<br><span class="mft-correo">{correo}</span>' if correo else "")
            + "</span></span>"
        )
    st.markdown(
        f"""
<div class="mft-barra">
  <div class="mft-migas">
    <span>MFT Investments</span><span class="mft-sep">/</span>
    <span>Robo-advisor</span><span class="mft-sep">/</span>
    <span class="mft-pastilla" style="color:{pastilla[1]};border-color:{pastilla[1]}">
      {pastilla[0]}</span>
  </div>
  {usuario}
</div>""",
        unsafe_allow_html=True,
    )


def logo_grande() -> None:
    """Logo completo, centrado y grande (pantalla de inicio)."""
    _, centro, _ = st.columns([1, 6, 1])
    centro.image(LOGO, use_container_width=True)


def pie_de_pagina() -> None:
    st.divider()
    st.caption(f"MFT Investments · Quantitative Research & Asset Management. {AVISO_ACADEMICO}")
