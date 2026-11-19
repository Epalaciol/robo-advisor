"""Análisis exploratorio (EDA) de las encuestas de aversión al riesgo del Taller 1.

Funciones puras sobre el CSV anonimizado de voluntarios (`scripts/taller1/exportar_voluntarios.py`):
no tocan red ni Supabase. Metodología (ver el informe, sección EDA):

1. **Calidad de datos:** respuestas completas, faltantes por factor, periodo de recolección.
2. **Univariado:** edad, puntaje (9–27), perfil y A; distribución de respuestas por pregunta.
3. **Confiabilidad del cuestionario:** alfa de Cronbach y correlación ítem-resto (cada pregunta
   frente al puntaje de las demás); coherencia de la pregunta 2 (más horizonte → menos venta).
4. **Bivariado:** puntaje frente a cada factor personal. Factores ordinales → correlación de
   Spearman (ρ); nominales → Kruskal-Wallis; binarios → Mann-Whitney. Valores p ajustados por
   Benjamini-Hochberg (varias pruebas a la vez). Con n ≈ 37 son indicios, no conclusiones.
5. **Resultado financiero:** y* que implica cada A sobre el portafolio de referencia y portafolios
   guardados (propios frente a asignados).
"""

from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402

from roboadvisor.taller1.core.cuestionario import (  # noqa: E402
    IDS_PREGUNTAS,
    OPCIONES_FACTORES,
    PERFILES,
    puntuar,
)

AZUL, NARANJA, GRIS, VERDE = "#1f4e79", "#d9822b", "#8a8a8a", "#3b7d3b"
COLORES_ABC = {"a": "#c0504d", "b": "#d9d9d9", "c": AZUL}

RANGOS_EDAD = ["18-24", "25-34", "35-44", "45-54", "55-64", "65-74", "75+"]
ORDEN_PERFIL = [e for _a, _b, _k, e, _A in PERFILES]  # Conservador → Agresivo
ETIQUETA_PREGUNTA = {
    "q1": "1. Cae 20 % a los 60 días",
    "q2a": "2A. Cae 20 %, objetivo a 5 años",
    "q2b": "2B. Cae 20 %, objetivo a 15 años",
    "q2c": "2C. Cae 20 %, objetivo a 30 años",
    "q3": "3. El fondo sube 25 %",
    "q4": "4. Ahorro para retiro en 15 años",
    "q5": "5. Premio: seguro o lotería",
    "q6": "6. Préstamo para invertir",
    "q7": "7. Acciones de la empresa",
}
ETIQUETA_FACTOR = {
    "rango_edad": "Edad",
    "ocupacion": "Ocupación",
    "rango_ingresos": "Ingresos (COP/mes)",
    "dependientes_economicos": "Dependientes",
    "nivel_educativo": "Nivel educativo",
    "experiencia_invirtiendo_anios": "Experiencia invirtiendo",
    "horizonte_principal_inversion": "Horizonte de inversión",
    "colchon_emergencia": "Colchón de emergencia",
}
# Factores con orden natural (se codifican 1, 2, 3...); "Prefiero no decir" queda como faltante.
ORDINALES = {
    "rango_edad": RANGOS_EDAD,
    "rango_ingresos": OPCIONES_FACTORES["rango_ingresos"][:-1],
    "dependientes_economicos": OPCIONES_FACTORES["dependientes_economicos"],
    "nivel_educativo": OPCIONES_FACTORES["nivel_educativo"],
    "experiencia_invirtiendo_anios": OPCIONES_FACTORES["experiencia_invirtiendo_anios"],
    "horizonte_principal_inversion": OPCIONES_FACTORES["horizonte_principal_inversion"],
}
NOMINALES = ["ocupacion"]
BINARIOS = {"colchon_emergencia": ("Sí", "No")}


def preparar(voluntarios: pd.DataFrame) -> pd.DataFrame:
    """Agrega puntaje, perfil, A y el número de respuestas a/b/c a cada encuestado."""
    d = voluntarios.copy().fillna("")
    res = [puntuar({q: str(r[q]) for q in IDS_PREGUNTAS}) for _, r in d.iterrows()]
    d["puntaje"] = [r.puntaje for r in res]
    d["perfil"] = pd.Categorical([r.etiqueta for r in res], ORDEN_PERFIL, ordered=True)
    d["a"] = [r.a for r in res]
    for letra in "abc":
        d[f"n_{letra}"] = [r.conteo[letra] for r in res]
    d["rango_edad"] = pd.Categorical(d["rango_edad"], RANGOS_EDAD, ordered=True)
    return d


# ------------------------------------------------------------------ tablas


def calidad(d: pd.DataFrame) -> pd.DataFrame:
    """Respuestas no vacías por variable (las 9 preguntas son obligatorias en la app)."""
    filas = [{"Variable": "Preguntas 1 a 7 (9 ítems)", "Con dato": len(d), "Faltantes": 0}]
    for f in ETIQUETA_FACTOR:
        if f == "rango_edad":
            continue
        vacio = d[f].astype(str).str.strip().isin(["", "Prefiero no decir"])
        filas.append(
            {
                "Variable": ETIQUETA_FACTOR[f],
                "Con dato": int((~vacio).sum()),
                "Faltantes": int(vacio.sum()),
            }
        )
    return pd.DataFrame(filas)


def resumen_puntaje(d: pd.DataFrame) -> dict:
    p = d["puntaje"]
    return {
        "n": int(len(p)),
        "media": float(p.mean()),
        "mediana": float(p.median()),
        "desv": float(p.std(ddof=1)),
        "min": int(p.min()),
        "max": int(p.max()),
        "q1": float(p.quantile(0.25)),
        "q3": float(p.quantile(0.75)),
        "asimetria": float(stats.skew(p, bias=False)),
        "shapiro_p": float(stats.shapiro(p).pvalue) if len(p) >= 3 else float("nan"),
    }


def tabla_perfiles(d: pd.DataFrame) -> pd.DataFrame:
    t = d["perfil"].value_counts().reindex(ORDEN_PERFIL).fillna(0).astype(int)
    a_de = {e: A for _a, _b, _k, e, A in PERFILES}
    rango = {e: f"{a}–{b}" for a, b, _k, e, _A in PERFILES}
    return pd.DataFrame(
        {
            "Perfil": t.index,
            "Puntaje": [rango[e] for e in t.index],
            "A": [a_de[e] for e in t.index],
            "Personas": t.to_numpy(),
            "%": t.to_numpy() / len(d),
        }
    )


def tabla_edad_perfil(d: pd.DataFrame) -> pd.DataFrame:
    t = pd.crosstab(d["rango_edad"], d["perfil"], dropna=False)
    t = t.reindex(index=RANGOS_EDAD, columns=ORDEN_PERFIL, fill_value=0)
    t["Total"] = t.sum(axis=1)
    t["Puntaje medio"] = (
        d.groupby("rango_edad", observed=False)["puntaje"].mean().reindex(RANGOS_EDAD)
    )
    return t


def tabla_items(d: pd.DataFrame) -> pd.DataFrame:
    """% de a/b/c por pregunta y valor medio (1–3)."""
    filas = []
    for q in IDS_PREGUNTAS:
        v = d[q].astype(str)
        filas.append(
            {
                "Pregunta": ETIQUETA_PREGUNTA[q],
                "a": (v == "a").mean(),
                "b": (v == "b").mean(),
                "c": (v == "c").mean(),
                "Media (1–3)": v.map({"a": 1, "b": 2, "c": 3}).mean(),
            }
        )
    return pd.DataFrame(filas)


def cronbach(d: pd.DataFrame) -> tuple[float, pd.DataFrame]:
    """Alfa de Cronbach `α = k/(k−1)·(1 − Σσ²ᵢ/σ²ₜ)` y correlación ítem-resto de cada pregunta."""
    x = d[IDS_PREGUNTAS].apply(lambda s: s.map({"a": 1, "b": 2, "c": 3})).astype(float)
    k = x.shape[1]
    total = x.sum(axis=1)
    alfa = k / (k - 1) * (1 - x.var(ddof=1).sum() / total.var(ddof=1))
    filas = []
    for q in IDS_PREGUNTAS:
        resto = total - x[q]
        r = x[q].corr(resto) if x[q].std() > 0 else float("nan")
        sin_q = x.drop(columns=q)
        a_sin = (k - 1) / (k - 2) * (1 - sin_q.var(ddof=1).sum() / sin_q.sum(axis=1).var(ddof=1))
        filas.append(
            {"Pregunta": ETIQUETA_PREGUNTA[q], "Correlación ítem-resto": r, "α sin el ítem": a_sin}
        )
    return float(alfa), pd.DataFrame(filas)


def coherencia_horizonte(d: pd.DataFrame) -> dict:
    """Pregunta 2: con más horizonte (5 → 15 → 30 años) la respuesta no debería bajar."""
    x = d[["q2a", "q2b", "q2c"]].apply(lambda s: s.map({"a": 1, "b": 2, "c": 3}))
    monotona = (x["q2a"] <= x["q2b"]) & (x["q2b"] <= x["q2c"])
    sube = x["q2c"] > x["q2a"]
    return {
        "n": int(len(x)),
        "monotonas": int(monotona.sum()),
        "suben": int(sube.sum()),
        "iguales": int((x.nunique(axis=1) == 1).sum()),
        "medias": x.mean().to_dict(),
    }


def _bh(p: list[float]) -> list[float]:
    """Valores p ajustados por Benjamini-Hochberg (tasa de falsos descubrimientos)."""
    p_arr = np.asarray(p, dtype=float)
    n = len(p_arr)
    orden = np.argsort(p_arr)
    aj = np.empty(n)
    acumulado = 1.0
    for rango, i in reversed(list(enumerate(orden, start=1))):
        acumulado = min(acumulado, p_arr[i] * n / rango)
        aj[i] = acumulado
    return aj.tolist()


def asociaciones(d: pd.DataFrame) -> pd.DataFrame:
    """Puntaje frente a cada factor personal, con la prueba adecuada a su escala."""
    filas = []
    for f, niveles in ORDINALES.items():
        codigo = d[f].astype(str).map({v: i for i, v in enumerate(niveles, start=1)})
        ok = codigo.notna()
        rho, p = stats.spearmanr(codigo[ok], d.loc[ok, "puntaje"])
        filas.append(
            {
                "Factor": ETIQUETA_FACTOR[f],
                "Escala": "ordinal",
                "Prueba": "Spearman",
                "n": int(ok.sum()),
                "Estadístico": float(rho),
                "p": float(p),
            }
        )
    for f in NOMINALES:
        grupos = [
            g["puntaje"].to_numpy() for v, g in d.groupby(f) if str(v).strip() and len(g) >= 2
        ]
        h, p = stats.kruskal(*grupos) if len(grupos) >= 2 else (float("nan"), float("nan"))
        filas.append(
            {
                "Factor": ETIQUETA_FACTOR[f],
                "Escala": "nominal",
                "Prueba": "Kruskal-Wallis (H)",
                "n": int(sum(len(g) for g in grupos)),
                "Estadístico": float(h),
                "p": float(p),
            }
        )
    for f, (si, no) in BINARIOS.items():
        x, y = d.loc[d[f] == si, "puntaje"], d.loc[d[f] == no, "puntaje"]
        u, p = stats.mannwhitneyu(x, y, alternative="two-sided")
        # correlación biserial de rangos: (2U/(n1·n2)) − 1, entre −1 y 1
        filas.append(
            {
                "Factor": ETIQUETA_FACTOR[f],
                "Escala": "binaria",
                "Prueba": "Mann-Whitney (r rangos)",
                "n": int(len(x) + len(y)),
                "Estadístico": float(2 * u / (len(x) * len(y)) - 1),
                "p": float(p),
            }
        )
    t = pd.DataFrame(filas)
    t["p ajustado (BH)"] = _bh(t["p"].tolist())
    return t


def resumen_por_factor(d: pd.DataFrame, factor: str) -> pd.DataFrame:
    niveles = ORDINALES.get(factor) or sorted(v for v in d[factor].astype(str).unique() if v)
    g = d[d[factor].astype(str).str.strip() != ""].groupby(d[factor].astype(str))["puntaje"]
    t = g.agg(["count", "mean", "median"]).reindex([n for n in niveles if n in g.groups])
    return t.rename(columns={"count": "n", "mean": "Media", "median": "Mediana"})


def loteria(d: pd.DataFrame) -> pd.DataFrame:
    """Pregunta 5: valor esperado y riesgo de cada opción, y cuántos la escogieron."""
    opciones = {
        "a": (2.0, 0.0, "$2 M seguros"),
        "b": (2.5, 2.5, "$5 M con prob. 50 %"),
        "c": (3.0, 6.0, "$15 M con prob. 20 %"),
    }
    v = d["q5"].astype(str)
    return pd.DataFrame(
        [
            {
                "Opción": k,
                "Premio": txt,
                "Valor esperado (M COP)": e,
                "Desv. estándar (M COP)": s,
                "Personas": int((v == k).sum()),
                "%": float((v == k).mean()),
            }
            for k, (e, s, txt) in opciones.items()
        ]
    )


def portafolios(d: pd.DataFrame) -> pd.DataFrame:
    """Portafolios guardados: origen (propio/asignado), activos y y* por perfil."""
    t = d[d["origen_portafolio"].astype(str) != ""].copy()
    t["y"] = pd.to_numeric(t["y_guardado"], errors="coerce")
    return t


@dataclass(frozen=True)
class ResultadosEDA:
    datos: pd.DataFrame
    calidad: pd.DataFrame
    puntaje: dict
    perfiles: pd.DataFrame
    edad_perfil: pd.DataFrame
    items: pd.DataFrame
    alfa: float
    item_resto: pd.DataFrame
    horizonte: dict
    asociaciones: pd.DataFrame
    loteria: pd.DataFrame
    portafolios: pd.DataFrame
    figuras: dict[str, Path]


# ------------------------------------------------------------------ figuras


def _guardar(fig, ruta: Path) -> Path:
    fig.tight_layout()
    fig.savefig(ruta, dpi=160)
    plt.close(fig)
    return ruta


def fig_edad_perfil(d: pd.DataFrame, ruta: Path) -> Path:
    t = pd.crosstab(d["rango_edad"], d["perfil"], dropna=False).reindex(
        index=RANGOS_EDAD, columns=ORDEN_PERFIL, fill_value=0
    )
    colores = ["#1f4e79", "#4f81bd", "#b7b7b7", "#f2a65a", "#c0504d"]
    fig, ax = plt.subplots(figsize=(7.0, 3.6))
    base = np.zeros(len(t))
    for perfil, color in zip(ORDEN_PERFIL, colores, strict=True):
        ax.bar(t.index, t[perfil], bottom=base, color=color, label=perfil)
        base += t[perfil].to_numpy()
    for i, total in enumerate(base):
        ax.text(i, total + 0.15, int(total), ha="center", fontsize=8)
    ax.set_ylabel("Personas")
    ax.set_xlabel("Rango de edad")
    ax.legend(fontsize=7, ncol=3, loc="upper right")
    ax.set_ylim(0, base.max() + 2)
    return _guardar(fig, ruta)


def fig_puntaje(d: pd.DataFrame, ruta: Path) -> Path:
    fig, ax = plt.subplots(figsize=(7.0, 3.4))
    bandas = [(9, 12.5), (12.5, 16.5), (16.5, 20.5), (20.5, 24.5), (24.5, 27.5)]
    for (x0, x1), color, (_a, _b, _k, e, A) in zip(
        bandas, ["#dbe5f1", "#eef3f8", "#f5f5f5", "#fbeee2", "#f6dcdb"], PERFILES, strict=True
    ):
        ax.axvspan(x0, x1, color=color, zorder=0)
        ax.text((x0 + x1) / 2, 0.97, f"{e}\nA = {A}", ha="center", va="top", fontsize=6.5,
                transform=ax.get_xaxis_transform())  # fmt: skip
    cuentas = d["puntaje"].value_counts().reindex(range(9, 28), fill_value=0)
    ax.bar(cuentas.index, cuentas.to_numpy(), color=AZUL, width=0.8, zorder=2)
    ax.axvline(d["puntaje"].mean(), color=NARANJA, lw=1.5, ls="--", label="Media", zorder=3)
    ax.set_xticks(range(9, 28))
    ax.set_xlabel("Puntaje del cuestionario (9 = más averso, 27 = menos averso)")
    ax.set_ylabel("Personas")
    ax.set_ylim(0, cuentas.max() + 2.5)
    ax.legend(fontsize=7, loc="center left")
    return _guardar(fig, ruta)


def fig_items(d: pd.DataFrame, ruta: Path) -> Path:
    t = tabla_items(d).iloc[::-1]
    fig, ax = plt.subplots(figsize=(7.0, 3.8))
    izq = np.zeros(len(t))
    for letra, nombre in (("a", "a (más averso)"), ("b", "b"), ("c", "c (menos averso)")):
        ax.barh(t["Pregunta"], t[letra], left=izq, color=COLORES_ABC[letra], label=nombre)
        for i, (x0, v) in enumerate(zip(izq, t[letra], strict=True)):
            if v >= 0.08:
                ax.text(x0 + v / 2, i, f"{v:.0%}", ha="center", va="center", fontsize=7,
                        color="white" if letra != "b" else "black")  # fmt: skip
        izq += t[letra].to_numpy()
    ax.set_xlim(0, 1)
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.tick_params(axis="y", labelsize=7.5)
    ax.legend(fontsize=7, ncol=3, loc="upper center", bbox_to_anchor=(0.4, 1.12))
    return _guardar(fig, ruta)


def fig_factores(d: pd.DataFrame, ruta: Path) -> Path:
    """Puntaje por nivel de cuatro factores (puntos = personas, rombo = media)."""
    factores = [
        "rango_edad",
        "rango_ingresos",
        "experiencia_invirtiendo_anios",
        "horizonte_principal_inversion",
    ]
    fig, ejes = plt.subplots(2, 2, figsize=(7.4, 5.6), sharey=True)
    rng = np.random.default_rng(0)
    for ax, f in zip(ejes.flat, factores, strict=True):
        niveles = [n for n in ORDINALES[f] if (d[f].astype(str) == n).any()]
        for i, n in enumerate(niveles):
            y = d.loc[d[f].astype(str) == n, "puntaje"].to_numpy()
            ax.scatter(i + rng.uniform(-0.12, 0.12, len(y)), y, s=14, color=AZUL, alpha=0.6)
            ax.scatter([i], [y.mean()], marker="D", s=40, color=NARANJA, zorder=3)
        ax.set_xticks(range(len(niveles)))
        etiquetas = [
            n.replace("$", "").replace(".000.000", "M").replace(" años", "a") for n in niveles
        ]
        ax.set_xticklabels(etiquetas, rotation=35, ha="right", fontsize=6.5)
        ax.set_title(ETIQUETA_FACTOR[f], fontsize=9)
        ax.grid(axis="y", alpha=0.25)
    ejes[0, 0].set_ylabel("Puntaje")
    ejes[1, 0].set_ylabel("Puntaje")
    return _guardar(fig, ruta)


def fig_correlaciones(d: pd.DataFrame, ruta: Path) -> Path:
    """Matriz de Spearman entre las 9 preguntas, el puntaje y los factores ordinales."""
    x = d[IDS_PREGUNTAS].apply(lambda s: s.map({"a": 1, "b": 2, "c": 3})).astype(float)
    x.columns = [q.upper().replace("Q", "P") for q in IDS_PREGUNTAS]
    x["Puntaje"] = d["puntaje"]
    for f, niveles in ORDINALES.items():
        x[ETIQUETA_FACTOR[f]] = d[f].astype(str).map({v: i for i, v in enumerate(niveles, 1)})
    c = x.corr(method="spearman")
    fig, ax = plt.subplots(figsize=(7.2, 6.0))
    im = ax.imshow(c, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(len(c)))
    ax.set_yticks(range(len(c)))
    ax.set_xticklabels(c.columns, rotation=60, ha="right", fontsize=7)
    ax.set_yticklabels(c.columns, fontsize=7)
    for i in range(len(c)):
        for j in range(len(c)):
            v = c.iat[i, j]
            if np.isfinite(v):
                ax.text(j, i, f"{v:.1f}".replace(".", ","), ha="center", va="center", fontsize=5.5,
                        color="white" if abs(v) > 0.6 else "black")  # fmt: skip
    fig.colorbar(im, ax=ax, shrink=0.75, label="ρ de Spearman")
    return _guardar(fig, ruta)


def fig_ystar(
    d: pd.DataFrame, y_por_a: dict[int, float], y_sin_tope: dict[int, float], ruta: Path
) -> Path:
    """Cuántas personas hay en cada A y qué y* les corresponde (con y sin tope de 100 %)."""
    a_vals = [8, 6, 4, 3, 1]
    n = [int((d["a"] == a).sum()) for a in a_vals]
    fig, ax = plt.subplots(figsize=(7.0, 3.4))
    x = np.arange(len(a_vals))
    ax.bar(
        x - 0.2,
        [y_por_a[a] for a in a_vals],
        width=0.4,
        color=AZUL,
        label="y* aplicado (tope 100 %)",
    )
    ax.bar(x + 0.2, [y_sin_tope[a] for a in a_vals], width=0.4, color=NARANJA, alpha=0.7,
           label="y* de la fórmula (sin tope)")  # fmt: skip
    ax.axhline(1, color=GRIS, ls="--", lw=1)
    for i, (a, k) in enumerate(zip(a_vals, n, strict=True)):
        ax.text(i + 0.2, y_sin_tope[a] + 0.05, f"{y_sin_tope[a]:.0%}", ha="center", fontsize=7)
        ax.text(i, -0.42, f"{k} pers.", ha="center", fontsize=7.5, color=GRIS)
    ax.set_xticks(x)
    ax.set_xticklabels([f"A = {a}" for a in a_vals])
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.set_ylim(-0.5, max(y_sin_tope.values()) + 0.4)
    ax.set_ylabel("Fracción en el portafolio de riesgo")
    ax.legend(fontsize=7, loc="upper left")
    return _guardar(fig, ruta)


def analizar(
    voluntarios: pd.DataFrame,
    carpeta_figuras: Path,
    y_por_a: dict[int, float],
    y_sin_tope: dict[int, float],
) -> ResultadosEDA:
    d = preparar(voluntarios)
    carpeta_figuras.mkdir(parents=True, exist_ok=True)
    alfa, item_resto = cronbach(d)
    figuras = {
        "eda_edad_perfil": fig_edad_perfil(d, carpeta_figuras / "eda_edad_perfil.png"),
        "eda_puntaje": fig_puntaje(d, carpeta_figuras / "eda_puntaje.png"),
        "eda_items": fig_items(d, carpeta_figuras / "eda_items.png"),
        "eda_factores": fig_factores(d, carpeta_figuras / "eda_factores.png"),
        "eda_correlaciones": fig_correlaciones(d, carpeta_figuras / "eda_correlaciones.png"),
        "eda_ystar": fig_ystar(d, y_por_a, y_sin_tope, carpeta_figuras / "eda_ystar.png"),
    }
    return ResultadosEDA(
        datos=d,
        calidad=calidad(d),
        puntaje=resumen_puntaje(d),
        perfiles=tabla_perfiles(d),
        edad_perfil=tabla_edad_perfil(d),
        items=tabla_items(d),
        alfa=alfa,
        item_resto=item_resto,
        horizonte=coherencia_horizonte(d),
        asociaciones=asociaciones(d),
        loteria=loteria(d),
        portafolios=portafolios(d),
        figuras=figuras,
    )
