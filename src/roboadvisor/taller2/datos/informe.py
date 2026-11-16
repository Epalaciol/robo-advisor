"""Lectura del Informe Diario de TES (www.irc.gov.co) → tabla "Tasa Fija en Pesos" validada.

Fuentes soportadas:
- PDF del IRC (`leer_pdf`): texto con `pdfplumber`, todas las páginas.
- Excel del IRC (`leer_excel`): mismo criterio que el lector del `.py` del grupo.
- CSV con el formato de `tests/taller2/fixtures/tes_2026-10-02.csv` (`leer_csv`): la tabla
  del enunciado del taller.

Robustez frente al PDF: en el texto extraído la fecha de vencimiento de algunas filas queda
separada de su línea. Por eso cada fila se ancla en el **nemotécnico** (sus 6 últimos dígitos
son el vencimiento ddmmaa) y la fecha impresa, si está en la línea, solo se usa para validar.
"""

import csv
import datetime as dt
import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

from ..config import ParametrosTES
from ..core.flujos import cupon_corrido_papel, flujos_papel
from ..core.modelos import Papel
from ..core.rendimientos import tir

MESES = {
    "ene": 1,
    "feb": 2,
    "mar": 3,
    "abr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "ago": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dic": 12,
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}
NOMBRE_MES = {
    1: "enero",
    2: "febrero",
    3: "marzo",
    4: "abril",
    5: "mayo",
    6: "junio",
    7: "julio",
    8: "agosto",
    9: "septiembre",
    10: "octubre",
    11: "noviembre",
    12: "diciembre",
}

_NUM = r"-?[\d.]+,\d+"
PATRON_FILA = re.compile(
    r"(?:(?P<dia>\d{1,2})-(?P<mes>[a-zA-Z]{3})-(?P<anio>\d{2})\s+)?"
    r"(?P<nemo>T(?:CO|FIT|FVT)\d{6,})\s+"
    r"(?P<nominal>[\d.]+)\s+"
    rf"(?P<cupon>{_NUM})\s+(?P<limpio>{_NUM})\s+(?P<sucio>{_NUM})\s+(?P<duracion>{_NUM})\s+"
    rf"(?P<tasa>{_NUM})\s*%?\s+(?P<origen>VAL|SEN)\s+"
    rf"(?:(?P<tasa_prev>{_NUM})\s*%?\s+(?P<origen_prev>VAL|SEN)\s+)?"
    rf"(?P<var>{_NUM})"
)
PATRON_TOTAL = re.compile(r"Total\s+Tasa\s+Fija\s+en\s+Pesos\s+(?P<total>[\d.]+)", re.I)
PATRON_PROMEDIO = re.compile(r"Promedio\s+(?P<prom>-?\d+,\d+)")
PATRON_FECHA = re.compile(r"(\d{1,2})\s+de\s+([a-záéíóú]+)\s+(?:de|del)\s+(\d{4})", re.I)


@dataclass(frozen=True)
class FilaTES:
    vencimiento: dt.date
    nemotecnico: str
    valor_nominal_mm: int
    cupon: float
    precio_limpio: float
    precio_sucio: float
    duracion: float
    tasa_pub: float  # decimal
    origen_tasa: str
    tasa_prev: float | None
    origen_prev: str | None
    var_pb: float | None
    vencimiento_impreso: dt.date | None = None  # fecha de la columna, si se pudo leer
    cupon_original: float | None = None  # cupón impreso erróneo de un TCO (se corrige a 0)

    def __post_init__(self):
        # IRC imprimió a veces un cupón en un TCO (cero cupón) con limpio = sucio: es un error de
        # digitación (la TIR con cupón 0 cuadra con la tasa VAL); se corrige y validar() avisa.
        if (
            self.nemotecnico.startswith("TCO")
            and self.cupon != 0
            and abs(self.precio_limpio - self.precio_sucio) < 1e-9
        ):
            object.__setattr__(self, "cupon_original", self.cupon)
            object.__setattr__(self, "cupon", 0.0)

    def a_papel(self) -> Papel:
        return Papel(
            nemotecnico=self.nemotecnico,
            vencimiento=self.vencimiento,
            cupon=self.cupon,
            precio_sucio=self.precio_sucio,
            precio_limpio=self.precio_limpio,
            duracion_informe=self.duracion,
            tasa_pub=self.tasa_pub,
            origen_tasa=self.origen_tasa,
            valor_nominal_mm=self.valor_nominal_mm,
        )


@dataclass
class InformeTES:
    fecha: dt.date
    filas: list[FilaTES]
    total_nominal_mm: int | None
    promedio_var_pb: float | None
    via: str  # "pdf", "excel" o "csv"
    fuente: str
    sha256: str | None = None
    avisos_lectura: list[str] = field(default_factory=list)

    def papeles(self) -> list[Papel]:
        """Papeles para la curva: excluye los que vencen en o antes de la fecha del informe."""
        return [f.a_papel() for f in self.filas if f.vencimiento > self.fecha]


class SinTexto(ValueError):
    """El PDF no trae texto extraíble o ninguna fila de TES tasa fija (p. ej. es una imagen)."""


@dataclass(frozen=True)
class Hallazgo:
    codigo: str
    nivel: str  # "error" | "advertencia"
    mensaje: str
    nemotecnico: str | None = None


# ----------------------------------------------------------------------------------- utilidades
def a_numero(texto: str) -> float:
    """Formato colombiano: '5.351.599' → 5351599 ; '99,430' → 99.43 ; '-2,2' → -2.2."""
    t = str(texto).strip().replace("%", "")
    if not t or not re.fullmatch(r"-?[\d.,]+", t):
        raise ValueError(f"No es un número: {texto!r}")
    return float(t.replace(".", "").replace(",", "."))


def a_fecha(texto: str) -> dt.date:
    """'20-oct-26' → 2026-10-20 (años de 2 dígitos son 20xx)."""
    m = re.fullmatch(r"(\d{1,2})-([a-zA-Z]{3})-(\d{2})", texto.strip())
    if not m or m.group(2).lower() not in MESES:
        raise ValueError(f"Fecha no reconocida: {texto!r}")
    return dt.date(2000 + int(m.group(3)), MESES[m.group(2).lower()], int(m.group(1)))


def fecha_en_texto(texto: str) -> dt.date | None:
    """Primera fecha 'viernes, 2 de octubre de 2026' del texto."""
    for m in PATRON_FECHA.finditer(texto):
        mes = m.group(2).lower()
        if mes in MESES:
            return dt.date(int(m.group(3)), MESES[mes], int(m.group(1)))
    return None


def vencimiento_de_nemotecnico(nemo: str) -> dt.date:
    """Últimos 6 dígitos del nemotécnico = vencimiento ddmmaa (TCO364201026 → 20-oct-26)."""
    d = nemo[-6:]
    return dt.date(2000 + int(d[4:6]), int(d[2:4]), int(d[0:2]))


def sha256(datos: bytes) -> str:
    return hashlib.sha256(datos).hexdigest()


# --------------------------------------------------------------------------------------- texto
PATRON_NEMO = re.compile(r"T(?:CO|FIT|FVT)\d{6,}")


def parsear_texto(texto: str, fuente: str = "texto", via: str = "pdf") -> InformeTES:
    """Extrae la tabla "Tasa Fija en Pesos" de un texto (función pura; la que se prueba)."""
    filas, avisos, vistos = [], [], set()
    for m in PATRON_FILA.finditer(texto):
        nemo = m.group("nemo")
        if nemo in vistos:
            avisos.append(f"{nemo} aparece más de una vez; se toma la primera")
            continue
        vistos.add(nemo)
        impreso = None
        if m.group("dia"):
            try:
                impreso = a_fecha(f"{m.group('dia')}-{m.group('mes')}-{m.group('anio')}")
            except ValueError:
                impreso = None
        filas.append(
            FilaTES(
                vencimiento=vencimiento_de_nemotecnico(nemo),
                nemotecnico=nemo,
                valor_nominal_mm=int(a_numero(m.group("nominal"))),
                cupon=a_numero(m.group("cupon")),
                precio_limpio=a_numero(m.group("limpio")),
                precio_sucio=a_numero(m.group("sucio")),
                duracion=a_numero(m.group("duracion")),
                tasa_pub=a_numero(m.group("tasa")) / 100,
                origen_tasa=m.group("origen"),
                tasa_prev=a_numero(m.group("tasa_prev")) / 100 if m.group("tasa_prev") else None,
                origen_prev=m.group("origen_prev"),
                var_pb=a_numero(m.group("var")),
                vencimiento_impreso=impreso,
            )
        )
    if not filas:
        raise SinTexto(f"{fuente}: no se encontró ninguna fila de TES tasa fija en pesos")
    filas.sort(key=lambda f: (f.vencimiento, f.nemotecnico))
    total = PATRON_TOTAL.search(texto)
    prom = PATRON_PROMEDIO.search(texto, total.end()) if total else None
    fecha = fecha_en_texto(texto)
    if fecha is None:
        raise ValueError(f"{fuente}: no se encontró la fecha del informe")
    for linea in texto.splitlines():  # que ninguna fila quede sin leer en silencio
        for nemo in PATRON_NEMO.findall(linea):
            if nemo not in vistos:
                avisos.append(f"fila no leída: {linea.strip()}")
                break
    return InformeTES(
        fecha=fecha,
        filas=filas,
        total_nominal_mm=int(a_numero(total.group("total"))) if total else None,
        promedio_var_pb=a_numero(prom.group("prom")) if prom else None,
        via=via,
        fuente=fuente,
        avisos_lectura=avisos,
    )


def leer_pdf(ruta: str | Path) -> InformeTES:
    import pdfplumber

    ruta = Path(ruta)
    with pdfplumber.open(ruta) as pdf:
        texto = "\n".join(page.extract_text() or "" for page in pdf.pages)
    if not texto.strip():
        raise SinTexto(f"{ruta.name}: el PDF no tiene texto extraíble (¿es una imagen?)")
    inf = parsear_texto(texto, fuente=ruta.name, via="pdf")
    inf.sha256 = sha256(ruta.read_bytes())
    return inf


# ----------------------------------------------------------------------------------------- CSV
def leer_csv(ruta: str | Path) -> InformeTES:
    """Formato del fixture del enunciado (una fila por papel, tasas en decimal)."""
    ruta = Path(ruta)
    filas, fechas = [], set()
    with open(ruta, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            fechas.add(r["fecha_informe"])
            filas.append(
                FilaTES(
                    vencimiento=dt.date.fromisoformat(r["vencimiento"]),
                    nemotecnico=r["nemotecnico"],
                    valor_nominal_mm=int(r["valor_nominal_mm"]),
                    cupon=float(r["cupon"]),
                    precio_limpio=float(r["precio_limpio"]),
                    precio_sucio=float(r["precio_sucio"]),
                    duracion=float(r["duracion"]),
                    tasa_pub=float(r["tasa_pub"]),
                    origen_tasa=r["origen_tasa"],
                    tasa_prev=float(r["tasa_prev"]) if r.get("tasa_prev") else None,
                    origen_prev=r.get("origen_prev") or None,
                    var_pb=float(r["var_pb"]) if r.get("var_pb") else None,
                    vencimiento_impreso=dt.date.fromisoformat(r["vencimiento"]),
                )
            )
    if len(fechas) != 1:
        raise ValueError(f"{ruta.name}: el CSV debe tener una sola fecha_informe ({fechas})")
    var = [f.var_pb for f in filas if f.var_pb is not None]
    return InformeTES(
        fecha=dt.date.fromisoformat(fechas.pop()),
        filas=sorted(filas, key=lambda f: (f.vencimiento, f.nemotecnico)),
        total_nominal_mm=sum(f.valor_nominal_mm for f in filas),
        promedio_var_pb=round(sum(var) / len(var), 1) if var else None,
        via="csv",
        fuente=ruta.name,
        sha256=sha256(ruta.read_bytes()),
    )


def escribir_csv(inf: InformeTES, ruta: str | Path) -> None:
    columnas = [
        "fecha_informe",
        "nemotecnico",
        "tipo",
        "vencimiento",
        "cupon",
        "valor_nominal_mm",
        "precio_limpio",
        "precio_sucio",
        "duracion",
        "tasa_pub",
        "origen_tasa",
        "tasa_prev",
        "origen_prev",
        "var_pb",
    ]
    with open(ruta, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(columnas)
        for f in inf.filas:
            w.writerow(
                [
                    inf.fecha.isoformat(),
                    f.nemotecnico,
                    f.a_papel().tipo,
                    f.vencimiento.isoformat(),
                    f.cupon,
                    f.valor_nominal_mm,
                    f.precio_limpio,
                    f.precio_sucio,
                    f.duracion,
                    f.tasa_pub,
                    f.origen_tasa,
                    "" if f.tasa_prev is None else f.tasa_prev,
                    f.origen_prev or "",
                    "" if f.var_pb is None else f.var_pb,
                ]
            )


# --------------------------------------------------------------------------------------- Excel
def leer_excel(ruta: str | Path, fecha: dt.date | None = None) -> InformeTES:
    """Excel del IRC (las columnas cambian de lugar según el día): en cada fila busca una
    fecha seguida de un nemotécnico y lee los números que le siguen (criterio del .py del grupo).
    """
    import openpyxl

    ruta = Path(ruta)
    wb = openpyxl.load_workbook(ruta, data_only=True)
    filas, fecha_leida = [], None
    for ws in wb.worksheets:
        for row in ws.iter_rows(values_only=True):
            celdas = [c for c in row if c is not None]
            if fecha_leida is None:
                for c in celdas:
                    if isinstance(c, str):
                        fecha_leida = fecha_en_texto(c) or fecha_leida
            for i, nemo in enumerate(celdas):
                if isinstance(nemo, str) and re.fullmatch(r"T(?:CO|FIT|FVT)\d{6,}", nemo.strip()):
                    resto = celdas[i + 1 :]
                    nums = [x for x in resto if isinstance(x, int | float)]
                    origenes = [x for x in resto if x in ("SEN", "VAL")]
                    if len(nums) < 6:
                        continue
                    tasa = nums[5] / 100 if nums[5] > 1 else nums[5]
                    prev = nums[6] / 100 if len(nums) > 6 and nums[6] > 1 else None
                    filas.append(
                        FilaTES(
                            vencimiento=vencimiento_de_nemotecnico(nemo.strip()),
                            nemotecnico=nemo.strip(),
                            valor_nominal_mm=int(nums[0]),
                            cupon=float(nums[1]),
                            precio_limpio=float(nums[2]),
                            precio_sucio=float(nums[3]),
                            duracion=float(nums[4]),
                            tasa_pub=float(tasa),
                            origen_tasa=origenes[0] if origenes else None,
                            tasa_prev=prev,
                            origen_prev=origenes[1] if len(origenes) > 1 else None,
                            var_pb=float(nums[7]) if len(nums) > 7 else None,
                        )
                    )
                    break
        if filas:
            break
    fecha = fecha or fecha_leida
    if fecha is None:
        raise ValueError(f"{ruta.name}: no encontré la fecha del informe; pásala con --fecha")
    return InformeTES(
        fecha=fecha,
        filas=sorted(filas, key=lambda f: (f.vencimiento, f.nemotecnico)),
        total_nominal_mm=None,
        promedio_var_pb=None,
        via="excel",
        fuente=ruta.name,
        sha256=sha256(ruta.read_bytes()),
    )


def leer(ruta: str | Path, fecha: dt.date | None = None) -> InformeTES:
    ruta = Path(ruta)
    sufijo = ruta.suffix.lower()
    if sufijo == ".pdf":
        return leer_pdf(ruta)
    if sufijo == ".csv":
        return leer_csv(ruta)
    if sufijo in (".xlsx", ".xlsm"):
        return leer_excel(ruta, fecha)
    raise ValueError(f"Formato no soportado: {ruta.name}")


# ---------------------------------------------------------------------------------- validación
def validar(
    inf: InformeTES,
    tol_cupon_corrido: float = 0.01,
    tol_sen_pb: float = 3.0,
    tol_total_por_fila_mm: float | None = None,
):
    """V1–V6 de docs/taller-2/08-pipeline-tes.md §3. Devuelve la lista de hallazgos."""
    h: list[Hallazgo] = []
    n = len(inf.filas)
    if not 15 <= n <= 45:
        h.append(Hallazgo("V2", "error", f"{n} filas; se esperan entre 15 y 45"))
    suma = sum(f.valor_nominal_mm for f in inf.filas)
    if inf.total_nominal_mm is None:
        if inf.via == "pdf":
            h.append(Hallazgo("V1", "advertencia", "No se encontró la fila de total"))
    elif suma != inf.total_nominal_mm:
        if tol_total_por_fila_mm is None:
            tol_total_por_fila_mm = ParametrosTES().tol_total_por_fila_mm
        dif = inf.total_nominal_mm - suma
        if abs(dif) <= tol_total_por_fila_mm * n:
            h.append(
                Hallazgo(
                    "V1",
                    "advertencia",
                    f"Total del informe difiere en {dif:+,} de la suma de filas "
                    "(redondeo/arrastre de la fuente)",
                )
            )
        else:
            h.append(
                Hallazgo(
                    "V1",
                    "error",
                    f"Σ nominal {suma:,} ≠ total del informe {inf.total_nominal_mm:,}",
                )
            )
    var = [f.var_pb for f in inf.filas if f.var_pb is not None]
    if inf.promedio_var_pb is not None and var:
        prom = sum(var) / len(var)
        if abs(prom - inf.promedio_var_pb) > 0.051:
            h.append(
                Hallazgo("V4", "error", f"Promedio var {prom:.2f} ≠ informe {inf.promedio_var_pb}")
            )
    for f in inf.filas:
        e = f.nemotecnico
        if f.vencimiento == inf.fecha:
            h.append(Hallazgo("V2", "advertencia", "Vence hoy: se excluye de la curva", e))
            continue
        if f.vencimiento < inf.fecha:
            h.append(Hallazgo("V2", "error", "Vence antes de la fecha del informe", e))
            continue
        if f.vencimiento_impreso is not None and f.vencimiento_impreso != f.vencimiento:
            h.append(
                Hallazgo("V3", "error", f"Fecha impresa {f.vencimiento_impreso} ≠ nemotécnico", e)
            )
        if not (f.precio_sucio >= f.precio_limpio > 0):
            h.append(Hallazgo("V2", "error", "Se espera sucio ≥ limpio > 0", e))
        if f.cupon_original is not None:
            h.append(
                Hallazgo(
                    "V2c",
                    "advertencia",
                    f"TCO con cupón {f.cupon_original:g} en el informe: "
                    "se corrige a 0 (cero cupón)",
                    e,
                )
            )
        if e.startswith("TCO") and (f.cupon != 0 or abs(f.precio_sucio - f.precio_limpio) > 1e-9):
            h.append(Hallazgo("V2", "error", "TCO con cupón o con limpio ≠ sucio", e))
        tol_hoy = ParametrosTES().tol_cupon_hoy
        corrido = cupon_corrido_papel(f.a_papel(), inf.fecha, tol=tol_hoy)
        dif = f.precio_limpio + corrido - f.precio_sucio
        if abs(dif) > tol_cupon_corrido:
            h.append(Hallazgo("V5", "advertencia", f"Cupón corrido no cuadra por {dif:+.3f}", e))
        if f.origen_tasa == "SEN":
            y = tir(f.precio_sucio, flujos_papel(f.a_papel(), inf.fecha, tol=tol_hoy))
            if abs(y - f.tasa_pub) * 1e4 > tol_sen_pb:
                h.append(
                    Hallazgo(
                        "V6",
                        "advertencia",
                        f"TIR del precio {y:.4%} vs tasa SEN {f.tasa_pub:.4%}",
                        e,
                    )
                )
    for a in inf.avisos_lectura:
        h.append(Hallazgo("L", "advertencia", a))
    return h


def errores(hallazgos) -> list[Hallazgo]:
    return [x for x in hallazgos if x.nivel == "error"]


# --------------------------------------------------------------------------------- diagnóstico
def texto_pdf(ruta: str | Path) -> str:
    import pdfplumber

    with pdfplumber.open(Path(ruta)) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def _diagnostico(argv=None) -> int:
    """python -m roboadvisor.taller2.datos.informe ARCHIVO.pdf
    Muestra lo leído y las validaciones, y guarda el texto extraído en exports/taller2/diagnostico/
    (para ajustar el lector si el formato del PDF de IRC cambia)."""
    import argparse

    ap = argparse.ArgumentParser(description="Diagnóstico del lector del Informe Diario de TES")
    ap.add_argument("archivo", type=Path)
    a = ap.parse_args(argv)
    if a.archivo.suffix.lower() == ".pdf":
        destino = Path(__file__).resolve().parents[4] / "exports" / "taller2" / "diagnostico"
        destino.mkdir(parents=True, exist_ok=True)
        salida = destino / f"{a.archivo.stem}.txt"
        salida.write_text(texto_pdf(a.archivo), encoding="utf-8")
        print(f"Texto extraído: {salida}")
    inf = leer(a.archivo)
    print(
        f"Fecha {inf.fecha} · {len(inf.filas)} papeles · total {inf.total_nominal_mm} · "
        f"promedio {inf.promedio_var_pb}"
    )
    for f in inf.filas:
        print(
            f"  {f.vencimiento} {f.nemotecnico:14} {f.valor_nominal_mm:>12,} {f.cupon:6.2f} "
            f"{f.precio_limpio:8.3f} {f.precio_sucio:8.3f} {f.duracion:5.2f} "
            f"{f.tasa_pub:.5f} {f.origen_tasa} {f.var_pb}"
        )
    h = validar(inf)
    for x in h:
        print(f"  [{x.codigo} {x.nivel}] {x.nemotecnico or ''} {x.mensaje}")
    return 1 if errores(h) else 0


if __name__ == "__main__":
    import sys

    sys.exit(_diagnostico())
