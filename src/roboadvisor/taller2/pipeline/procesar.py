"""Procesa un rango de días: obtener informes → validar → calibrar (encadenando betas) → exportar.

Lo usan el pipeline diario (`update_tes`) y los comandos de validación (`validacion`).
Los PDF se guardan en `data_local/tes/` (caché: no se vuelven a descargar).
"""

import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from ..config import ParametrosTES
from ..core.analisis import ResultadoTES, analizar
from ..core.modelos import Betas
from ..datos import informe as inf_mod
from ..datos.informe import Hallazgo, InformeTES, errores, validar

RAIZ = Path(__file__).resolve().parents[4]
CARPETA_INFORMES = RAIZ / "data_local" / "tes"
CARPETA_EXPORTS = RAIZ / "exports" / "taller2"


@dataclass
class DiaTES:
    fecha: dt.date
    estado: str  # ok | error_validacion | no_convergio | no_publicado | error_lectura | sin_texto
    informe: InformeTES | None = None
    hallazgos: list[Hallazgo] = field(default_factory=list)
    resultado: ResultadoTES | None = None
    url: str | None = None
    mensaje: str = ""


def dias_habiles(desde: dt.date, hasta: dt.date) -> list[dt.date]:
    return [
        desde + dt.timedelta(d)
        for d in range((hasta - desde).days + 1)
        if (desde + dt.timedelta(d)).weekday() < 5
    ]


def leer_carpeta(carpeta: Path = CARPETA_INFORMES) -> dict[dt.date, tuple[InformeTES | None, str]]:
    """Lee todos los PDF/XLSX/CSV de la carpeta. La fecha sale del contenido del informe."""
    salida: dict[dt.date, tuple[InformeTES | None, str]] = {}
    if not carpeta.exists():
        return salida
    for ruta in sorted(carpeta.iterdir()):
        if ruta.suffix.lower() not in (".pdf", ".xlsx", ".csv") or ruta.name.startswith("_"):
            continue
        try:
            inf = inf_mod.leer(ruta)
        except Exception as e:  # noqa: BLE001 — se reporta y se sigue con los demás
            salida.setdefault(dt.date.min, (None, f"{ruta.name}: {e}"))
            continue
        salida.setdefault(inf.fecha, (inf, str(ruta)))
    return salida


def obtener_informes(
    desde: dt.date,
    hasta: dt.date,
    carpeta: Path = CARPETA_INFORMES,
    descargar: bool = True,
    cliente_irc=None,
    log=print,
) -> list[DiaTES]:
    """Un `DiaTES` por día hábil del rango: desde la carpeta local o descargado de IRC."""
    carpeta.mkdir(parents=True, exist_ok=True)
    locales = leer_carpeta(carpeta)
    if dt.date.min in locales:
        log(f"  ! No se pudo leer un archivo local: {locales[dt.date.min][1]}")
    dias = []
    for fecha in dias_habiles(desde, hasta):
        if fecha in locales:
            inf, origen = locales[fecha]
            dias.append(DiaTES(fecha, "leido", inf, mensaje=f"local: {Path(origen).name}"))
            continue
        if not descargar:
            dias.append(DiaTES(fecha, "no_publicado", mensaje="no está en la carpeta local"))
            continue
        from ..datos.irc import ClienteIRC, NoPublicado

        cliente_irc = cliente_irc or ClienteIRC()
        try:
            datos, url = cliente_irc.descargar(fecha)
        except NoPublicado as e:
            dias.append(DiaTES(fecha, "no_publicado", mensaje=str(e)))
            log(f"  {fecha}: no publicado")
            continue
        ruta = carpeta / f"informe_{fecha.isoformat()}.pdf"
        ruta.write_bytes(datos)
        try:
            inf = inf_mod.leer_pdf(ruta)
        except inf_mod.SinTexto:
            dias.append(
                DiaTES(
                    fecha,
                    "sin_texto",
                    url=url,
                    mensaje="PDF sin texto extraíble (posible imagen); día omitido",
                )
            )
            log(f"  {fecha}: PDF sin texto extraíble; día omitido")
            continue
        except Exception as e:  # noqa: BLE001
            dias.append(DiaTES(fecha, "error_lectura", url=url, mensaje=str(e)))
            continue
        if inf.fecha != fecha:
            dias.append(
                DiaTES(fecha, "error_lectura", inf, url=url, mensaje=f"el PDF dice {inf.fecha}")
            )
            continue
        dias.append(DiaTES(fecha, "leido", inf, url=url, mensaje="descargado de IRC"))
        log(f"  {fecha}: descargado ({len(inf.filas)} papeles)")
    return dias


def procesar(
    dias: list[DiaTES], params: ParametrosTES | None = None, betas_iniciales: Betas | None = None
) -> list[DiaTES]:
    """Valida y calibra en orden de fecha, partiendo de los betas del día anterior (Excel)."""
    params = params or ParametrosTES()
    previos = betas_iniciales
    for d in sorted(dias, key=lambda x: x.fecha):
        if d.informe is None or d.estado not in ("leido", "ok"):
            continue
        d.hallazgos = validar(d.informe)
        if errores(d.hallazgos):
            d.estado = "error_validacion"
            d.mensaje = "; ".join(h.mensaje for h in errores(d.hallazgos))[:300]
            continue
        d.resultado = analizar(d.informe.papeles(), d.fecha, params, previos)
        if not d.resultado.calibracion.convergio:
            d.estado = "no_convergio"
            continue
        d.estado = "ok"
        previos = d.resultado.calibracion.betas
    return sorted(dias, key=lambda x: x.fecha)


def exportar_dia(d: DiaTES, carpeta: Path = CARPETA_EXPORTS) -> Path:
    """resultado.csv, flujos.csv, curva.csv y parametros.csv del día."""
    destino = carpeta / d.fecha.isoformat()
    destino.mkdir(parents=True, exist_ok=True)
    r = d.resultado
    r.tabla.to_csv(destino / "resultado.csv", index=False)
    r.flujos.to_csv(destino / "flujos.csv", index=False)
    r.curva().to_csv(destino / "curva.csv", index=False)
    c = r.calibracion
    pd.DataFrame(
        {
            "parametro": [
                "fecha",
                "b0",
                "b1",
                "b2",
                "tau",
                "sse",
                "rmse",
                "n",
                "umbral_pb",
                "regla",
            ],
            "valor": [
                d.fecha,
                c.betas.b0,
                c.betas.b1,
                c.betas.b2,
                c.tau,
                c.sse,
                c.rmse,
                c.n,
                r.umbral_pb,
                r.regla_umbral,
            ],
        }
    ).to_csv(destino / "parametros.csv", index=False)
    return destino


def resumen(dias: list[DiaTES]) -> pd.DataFrame:
    filas = []
    for d in dias:
        fila = {"fecha": d.fecha, "estado": d.estado, "mensaje": d.mensaje}
        if d.informe:
            fila["papeles"] = len(d.informe.filas)
            fila["advertencias"] = sum(h.nivel == "advertencia" for h in d.hallazgos)
        if d.resultado:
            c = d.resultado.calibracion
            fila.update(
                b0=c.betas.b0,
                b1=c.betas.b1,
                b2=c.betas.b2,
                sse=c.sse,
                rmse=c.rmse,
                umbral_pb=d.resultado.umbral_pb,
                **d.resultado.conteo_senales(),
            )
        filas.append(fila)
    return pd.DataFrame(filas)
