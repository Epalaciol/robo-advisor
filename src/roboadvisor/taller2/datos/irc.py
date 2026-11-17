"""Descarga del Informe Diario de TES desde www.irc.gov.co.

Cómo publica IRC (revisado el 16-nov-2026):
- Listado de 2026 en https://www.irc.gov.co/440 (biblioteca de documentos, paginada), con
  enlaces "Informe Diario TES 6 de Noviembre de 2026" → página del archivo (`view_file/<id>`).
- Cada archivo se descarga desde una URL "amigable" que suele seguir la fecha:
  https://www.irc.gov.co/documents/d/guest/informe-diario-6-de-noviembre-de-2026?download=true
  (no siempre: la del 2-oct no respondió así; por eso hay respaldo por el listado).
- Publica con retraso (el informe del 6-nov se subió el 13-nov): nunca asumir "el de ayer".

Sin API: se descarga como lo haría una persona, con pocas peticiones y pausas.
"""

import datetime as dt
import html
import re
import time
from html.parser import HTMLParser
from urllib.parse import urljoin

import httpx

from .informe import MESES, NOMBRE_MES

BASE = "https://www.irc.gov.co"
LISTADO_POR_ANIO = {2026: f"{BASE}/440"}
CABECERAS = {
    "User-Agent": "Mozilla/5.0 (compatible; roboadvisor-eafit/1.0; taller academico)",
    "Accept-Language": "es-CO,es;q=0.9",
}
PATRON_TITULO = re.compile(r"Informe\s+Diario\s+TES\s+(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})", re.I)


class NoPublicado(Exception):
    """El informe de esa fecha no está (aún) en el sitio: festivo o publicación atrasada."""


def url_directa(fecha: dt.date) -> str:
    slug = f"informe-diario-{fecha.day}-de-{NOMBRE_MES[fecha.month]}-de-{fecha.year}"
    return f"{BASE}/documents/d/guest/{slug}?download=true"


class _Enlaces(HTMLParser):
    def __init__(self):
        super().__init__()
        self.enlaces: list[tuple[str, str]] = []
        self._href: str | None = None
        self._texto: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            a = dict(attrs)
            self._href = a.get("href")
            self._texto = [a.get("title") or "", a.get("aria-label") or ""]

    def handle_data(self, data):
        if self._href is not None:
            self._texto.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            self.enlaces.append((html.unescape(self._href), " ".join(self._texto).strip()))
            self._href = None


def enlaces(html_texto: str) -> list[tuple[str, str]]:
    p = _Enlaces()
    p.feed(html_texto)
    return p.enlaces


def informes_en_listado(html_texto: str) -> dict[dt.date, str]:
    """{fecha: url de la página del archivo} a partir del HTML de una página del listado."""
    salida = {}
    for href, texto in enlaces(html_texto):
        m = PATRON_TITULO.search(texto)
        if m and "view_file" in href and m.group(2).lower() in MESES:
            f = dt.date(int(m.group(3)), MESES[m.group(2).lower()], int(m.group(1)))
            salida.setdefault(f, urljoin(BASE, href))
    return salida


def pagina_siguiente(html_texto: str) -> str | None:
    for href, texto in enlaces(html_texto):
        if "siguiente" in texto.lower() and href and not href.startswith("javascript"):
            return urljoin(BASE, href)
    return None


def enlace_descarga(html_texto: str) -> str | None:
    """En la página `view_file`, el botón Descargar apunta a /documents/...?download=true."""
    for href, _ in enlaces(html_texto):
        if "/documents/" in href and "download=true" in href:
            return urljoin(BASE, href)
    for href, _ in enlaces(html_texto):
        if "/documents/" in href:
            return urljoin(BASE, href)
    return None


class ClienteIRC:
    def __init__(self, http: httpx.Client | None = None, pausa_s: float = 1.0, max_paginas=30):
        self.http = http or httpx.Client(headers=CABECERAS, timeout=30, follow_redirects=True)
        self.pausa_s = pausa_s
        self.max_paginas = max_paginas
        self._indice: dict[dt.date, str] = {}
        self._paginas_leidas = 0
        self._siguiente: str | None = None

    def _get(self, url: str) -> httpx.Response:
        for intento in range(3):
            r = self.http.get(url)
            if r.status_code in (403, 429):
                raise PermissionError(
                    f"IRC respondió {r.status_code} a {url}. El sitio bloqueó la descarga "
                    "automática: baja los PDF a mano a data_local/tes/ y usa --sin-descarga."
                )
            if r.status_code < 500:
                return r
            time.sleep(self.pausa_s * (intento + 1))
        return r

    def _es_pdf(self, r: httpx.Response) -> bool:
        return r.status_code == 200 and r.content[:5] == b"%PDF-"

    def _ampliar_indice(self, hasta: dt.date) -> None:
        """Lee páginas del listado hasta cubrir `hasta` (o acabarse)."""
        if self._paginas_leidas == 0:
            self._siguiente = LISTADO_POR_ANIO.get(hasta.year)
        while self._siguiente and self._paginas_leidas < self.max_paginas:
            if self._indice and min(self._indice) <= hasta:
                return
            r = self._get(self._siguiente)
            self._paginas_leidas += 1
            self._indice.update(informes_en_listado(r.text))
            self._siguiente = pagina_siguiente(r.text)
            time.sleep(self.pausa_s)

    def descargar(self, fecha: dt.date) -> tuple[bytes, str]:
        """PDF del informe de `fecha` y la URL de donde salió. `NoPublicado` si no existe."""
        url = url_directa(fecha)
        r = self._get(url)
        if self._es_pdf(r):
            return r.content, url
        time.sleep(self.pausa_s)
        self._ampliar_indice(fecha)
        pagina = self._indice.get(fecha)
        if pagina is None:
            raise NoPublicado(f"No hay informe del {fecha} en el listado de IRC")
        r = self._get(pagina)
        destino = enlace_descarga(r.text)
        if destino is None:
            raise NoPublicado(f"No encontré el enlace de descarga en {pagina}")
        time.sleep(self.pausa_s)
        r = self._get(destino)
        if not self._es_pdf(r):
            raise NoPublicado(f"{destino} no devolvió un PDF (HTTP {r.status_code})")
        return r.content, destino

    def fechas_publicadas(self, desde: dt.date) -> list[dt.date]:
        """Fechas con informe en el listado desde `desde` (para detectar datos viejos)."""
        self._ampliar_indice(desde)
        return sorted(f for f in self._indice if f >= desde)
