"""Convierte un README.md en PDF (para adjuntarlo a un correo) con pandoc + xelatex.

Los enlaces relativos del README se reescriben como enlaces absolutos al repositorio, para que
sigan funcionando fuera de GitHub.
"""

import re
import subprocess
from pathlib import Path

REPO_URL = "https://github.com/Epalaciol/robo-advisor"
RAMA = "master"
CABECERA = (
    "---\nlang: es\ngeometry: margin=2cm\nfontsize: 10.5pt\nmainfont: Arial\n"
    "monofont: Menlo\ncolorlinks: true\n---\n\n"
)


def _absolutos(md: str, carpeta: Path, raiz: Path) -> str:
    def cambia(m: re.Match) -> str:
        texto, destino = m.group(1), m.group(2)
        if re.match(r"^(https?:|mailto:|#)", destino):
            return m.group(0)
        ruta = (carpeta / destino.split("#")[0]).resolve().relative_to(raiz)
        tipo = "tree" if destino.endswith("/") or (raiz / ruta).is_dir() else "blob"
        return f"[{texto}]({REPO_URL}/{tipo}/{RAMA}/{ruta.as_posix()})"

    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", cambia, md)


def readme_a_pdf(readme: Path, salida: Path, raiz: Path) -> Path:
    md = readme.read_text(encoding="utf-8")
    md = re.sub(r"[\U0001F300-\U0001FAFF☀-➿]️?\s*", "", md)  # emojis: Arial no los tiene
    md = _absolutos(md, readme.parent.resolve(), raiz.resolve())
    tmp = salida.with_suffix(".md")
    tmp.write_text(CABECERA + md, encoding="utf-8")
    try:
        subprocess.run(
            ["pandoc", tmp.name, "-o", salida.name, "--pdf-engine=xelatex"],
            cwd=salida.parent,
            check=True,
        )
    finally:
        tmp.unlink(missing_ok=True)
    return salida
