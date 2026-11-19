"""Crea en Supabase el portafolio de referencia de usuarios que ya respondieron la encuesta.

Para cada usuario con encuesta y sin portafolio: toma el portafolio de riesgo óptimo (tangente) de
los 11 ETF de referencia (`UNIVERSO_REFERENCIA`), lo combina con el activo libre de riesgo según el
A de su encuesta (y* = (E(Rp) − rf)/(A·σp²), tope 100 %) y guarda el registro con el mismo formato
que el Constructor. El cálculo es el del paquete `core` (Python), no el del Excel.

Por defecto **solo simula** (imprime lo que insertaría). Para escribir hay que pasar `--aplicar`.
Hay que indicar a quién: `--correo X` (uno o varios) o `--todos` (usuarios reales; excluye los
`@local.test`). Nunca toca a quien ya tiene portafolio (es inmutable: `unique(user_id)`).

Usa `service_role`: correr solo desde la máquina del administrador, nunca desde la app.

    python scripts/taller1/crear_portafolios_voluntarios.py --todos               # simula
    python scripts/taller1/crear_portafolios_voluntarios.py --correo a@b.com --aplicar
"""

import argparse
import sys
from dataclasses import replace
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "app"))  # `armar_registro_portafolio` vive en app/ui (sin Streamlit)

from ui.taller1.constructor import armar_registro_portafolio  # noqa: E402

from roboadvisor.comun.cliente import cliente_servicio  # noqa: E402
from roboadvisor.taller1.config import UNIVERSO_REFERENCIA, ParametrosFinancieros  # noqa: E402
from roboadvisor.taller1.core.markowitz import tangente, w_max_efectivo, w_min_efectivo  # noqa: E402
from roboadvisor.taller1.core.portafolio_completo import componer  # noqa: E402
from roboadvisor.taller1.core.retornos import estimar  # noqa: E402
from roboadvisor.taller1.data.repositorio_mercado import RepositorioMercado  # noqa: E402

SUFIJO_DEMO = "@local.test"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--correo", action="append", default=[], help="correo a procesar (repetible)")
    ap.add_argument("--todos", action="store_true", help="todos los usuarios reales con encuesta")
    ap.add_argument("--aplicar", action="store_true", help="escribir en Supabase (si no, simula)")
    a = ap.parse_args()
    if not a.correo and not a.todos:
        ap.error("indica --correo o --todos")

    c = cliente_servicio()
    p = ParametrosFinancieros()
    correos = {u.id: (u.email or "") for u in c.auth.admin.list_users(per_page=1000)}
    objetivo = {m.lower() for m in a.correo}
    encuestas = c.table("encuestas").select("id, user_id, a, perfil").execute().data
    con_portafolio = {r["user_id"] for r in c.table("portafolios").select("user_id").execute().data}

    # Portafolio de riesgo óptimo del universo de referencia (el mismo para todos)
    repo = RepositorioMercado(c)
    tickers = list(UNIVERSO_REFERENCIA)
    desde = (pd.Timestamp.today() - pd.DateOffset(months=p.meses_historia)).date().isoformat()
    est = estimar(repo.precios(tickers, desde), repo.rf_ultima(), p.ventana_dias, p.min_dias)
    w_max, _ = w_max_efectivo(p.w_max, len(tickers))
    w_min, _ = w_min_efectivo(p.w_min, len(tickers))
    tang = tangente(est, p.w_max, p.w_min)
    params_usados = replace(p, w_max=w_max, w_min=w_min)
    fecha_base = repo.ultima_fecha_precios()
    print(
        f"Tangente de {len(tickers)} ETF: E(Rp)={tang.retorno:.1%}, σp={tang.sigma:.1%}, "
        f"{est.n_obs} días, fecha base {fecha_base}"
    )

    hechos = 0
    for e in encuestas:
        correo = correos.get(e["user_id"], "")
        elegido = (
            correo.lower() in objetivo if objetivo else a.todos and not correo.endswith(SUFIJO_DEMO)
        )
        if not elegido:
            continue
        if e["user_id"] in con_portafolio:
            print(f"  - {correo}: ya tiene portafolio, se omite")
            continue
        completo = componer(tang, est.rf, float(e["a"]))
        payload = armar_registro_portafolio(
            e["user_id"], e["id"], float(e["a"]), e["perfil"], est, tang, completo,
            params_usados, fecha_base,
        )  # fmt: skip
        print(
            f"  - {correo}: A={e['a']} ({e['perfil']}) → y*={payload['y_star']:.1%}, "
            f"rf={payload['peso_rf']:.1%}, activos={', '.join(payload['tickers'])}"
        )
        if a.aplicar:
            c.table("portafolios").insert(payload).execute()
            hechos += 1
    print(f"{hechos} portafolios creados." if a.aplicar else "Simulación: no se escribió nada.")


if __name__ == "__main__":
    main()
