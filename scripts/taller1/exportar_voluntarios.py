"""Exporta de Supabase (solo lectura) los voluntarios del Taller 1, anonimizados.

Toma los usuarios reales (excluye los de demostración `@local.test`) que ya respondieron la
encuesta, los ordena por rango de edad y les asigna alias V1, V2, ... (sin correo ni alias real).
Escribe `entregas/taller-1/datos/voluntarios.csv` (ignorado por git: son datos personales) con las
respuestas q1..q7, los factores personales y, si ya armaron portafolio, sus activos, y* y si lo
armaron ellos (`propio`) o se les asignó el de referencia (`asignado`).
Usa `service_role`: correr solo desde la máquina del administrador, nunca desde la app.
"""

from pathlib import Path

import pandas as pd

from roboadvisor.comun.cliente import cliente_servicio
from roboadvisor.taller1.core.cuestionario import FACTORES_SUGERIDOS, IDS_PREGUNTAS

DESTINO = (
    Path(__file__).resolve().parents[2] / "entregas" / "taller-1" / "datos" / "voluntarios.csv"
)
RANGOS_ENUNCIADO = ["25-34", "35-44", "45-54", "55-64", "65-74"]


def main() -> None:
    c = cliente_servicio()
    usuarios = c.auth.admin.list_users()
    demo = {u.id for u in usuarios if (u.email or "").endswith("@local.test")}
    try:  # las cuentas de administrador no son voluntarios
        demo |= {r["user_id"] for r in c.table("administradores").select("user_id").execute().data}
    except Exception:
        pass
    perfiles = pd.DataFrame(
        c.table("perfiles").select("user_id, edad_rango, factores, created_at").execute().data
    )
    encuestas = pd.DataFrame(
        c.table("encuestas").select("user_id, respuestas, created_at").execute().data
    )
    portafolios = pd.DataFrame(
        c.table("portafolios")
        .select("user_id, tickers, y_star, fecha_base, parametros")
        .execute()
        .data
    )
    df = perfiles[~perfiles["user_id"].isin(demo)].merge(
        encuestas, on="user_id", suffixes=("", "_encuesta")
    )
    df = df.merge(portafolios, on="user_id", how="left")
    df = df.sort_values(["edad_rango", "created_at"]).reset_index(drop=True)

    filas = []
    for i, r in df.iterrows():
        fila = {"alias": f"V{i + 1}", "rango_edad": r["edad_rango"]}
        fila["fecha_encuesta"] = str(r["created_at_encuesta"])[:10]
        fila |= {q: r["respuestas"].get(q, "") for q in IDS_PREGUNTAS}
        fila |= {f: (r["factores"] or {}).get(f, "") for f in FACTORES_SUGERIDOS}
        fila["activos_elegidos"] = ", ".join(r["tickers"]) if isinstance(r["tickers"], list) else ""
        fila["y_guardado"] = "" if pd.isna(r["y_star"]) else float(r["y_star"])
        par = r["parametros"] if isinstance(r["parametros"], dict) else None
        fila["origen_portafolio"] = (
            ""
            if par is None
            else "asignado"
            if par.get("origen") == "asignado_referencia"
            else "propio"
        )
        filas.append(fila)
    salida = pd.DataFrame(filas)
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    salida.to_csv(DESTINO, index=False)

    print(f"{len(salida)} voluntarios con encuesta -> {DESTINO}")
    faltan = [r for r in RANGOS_ENUNCIADO if r not in set(salida["rango_edad"])]
    if faltan:
        print(f"Faltan rangos de edad del enunciado: {faltan}")


if __name__ == "__main__":
    main()
