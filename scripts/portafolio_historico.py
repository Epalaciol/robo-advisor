"""Registra un portafolio "como si se hubiera armado hace N meses", para ver en la app
cómo le ha ido desde entonces (página "Mi portafolio").

El portafolio es el tangente (Markowitz) estimado **solo con datos hasta `fecha_base`**
(sin mirar el futuro) y con la tasa libre de riesgo de ese día; luego se compone con el
A del usuario (CAL + y*). Reemplaza el portafolio que el usuario tuviera.

Usa `service_role` (ignora RLS): solo desde tu máquina, solo con usuarios `@local.test`.

Uso:
    python scripts/portafolio_historico.py --correo demo.a4@local.test \
        --tickers SMH,XBI,URA,KWEB,EWZ --meses 6
"""

import argparse
import sys
from dataclasses import replace
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "app"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from crear_usuario_prueba import _buscar_usuario  # noqa: E402
from ui.constructor import armar_registro_portafolio  # noqa: E402

from roboadvisor.config import ParametrosFinancieros  # noqa: E402
from roboadvisor.core.markowitz import tangente, w_max_efectivo  # noqa: E402
from roboadvisor.core.portafolio_completo import componer  # noqa: E402
from roboadvisor.core.retornos import estimar  # noqa: E402
from roboadvisor.data.cliente import cliente_servicio  # noqa: E402
from roboadvisor.data.repositorio_mercado import RepositorioMercado  # noqa: E402

SUFIJO_PERMITIDO = "@local.test"


def main() -> None:
    parser = argparse.ArgumentParser(description="Portafolio con fecha base en el pasado")
    parser.add_argument("--correo", required=True)
    parser.add_argument("--tickers", required=True, help="Lista separada por comas (3 a 11)")
    parser.add_argument("--meses", type=int, default=6)
    args = parser.parse_args()
    assert args.correo.endswith(SUFIJO_PERMITIDO), "Solo se permiten correos @local.test"

    params = ParametrosFinancieros()
    tickers = sorted(args.tickers.split(","))
    admin = cliente_servicio()
    mercado = RepositorioMercado(admin)

    user_id = _buscar_usuario(admin, args.correo)
    if user_id is None:
        raise SystemExit(f"No existe {args.correo}. Corre primero scripts/usuarios_demo.py")
    encuesta = admin.table("encuestas").select("*").eq("user_id", user_id).execute().data
    if not encuesta:
        raise SystemExit("El usuario no tiene encuesta.")
    encuesta = encuesta[0]
    a = float(encuesta["a"])

    objetivo = pd.Timestamp.today().normalize() - pd.DateOffset(months=args.meses)
    desde = objetivo - pd.DateOffset(months=params.meses_historia)
    precios = mercado.precios(tickers, desde.date().isoformat())
    precios = precios[precios.index <= objetivo]  # sin mirar el futuro
    fecha_base = precios.index.max()

    fila_rf = (
        admin.table("tasa_libre_riesgo")
        .select("fecha,tasa_anual")
        .lte("fecha", fecha_base.date().isoformat())
        .order("fecha", desc=True)
        .limit(1)
        .execute()
        .data
    )
    if not fila_rf:
        raise SystemExit("No hay tasa libre de riesgo disponible en esa fecha.")
    rf = float(fila_rf[0]["tasa_anual"])

    est = estimar(precios, rf, params.ventana_dias, params.min_dias)
    w_usado, _ = w_max_efectivo(params.w_max, len(tickers))
    tang = tangente(est, params.w_max)
    completo = componer(tang, est.rf, a)

    payload = armar_registro_portafolio(
        user_id=user_id,
        encuesta_id=encuesta["id"],
        a_usado=a,
        perfil_usado=encuesta["perfil"],
        est=est,
        port_riesgo=tang,
        port_completo=completo,
        params=replace(params, w_max=w_usado),
        fecha_base=fecha_base.date().isoformat(),
    )
    admin.table("portafolios").delete().eq("user_id", user_id).execute()
    admin.table("portafolios").insert(payload).execute()

    print(f"{args.correo} (A={a:g}, {encuesta['perfil']}) · fecha_base {payload['fecha_base']}")
    print(f"  rf {rf:.2%} · {est.n_obs} días de retornos hasta {est.fecha_fin.date()}")
    print(f"  tangente: { ({k: v for k, v in payload['pesos_riesgo'].items() if v > 0.001}) }")
    print(
        f"  E {tang.retorno:.1%} · σ {tang.sigma:.1%} · y* {payload['y_star']:.1%} "
        f"· rf {payload['peso_rf']:.1%}"
    )


if __name__ == "__main__":
    main()
