# MFT Investments · Robo-advisor

**Talleres 1 y 2 de Inversiones — Maestría en Finanzas, EAFIT (2026-II)**
*Quantitative Research & Asset Management*

Una plataforma que ayuda a una persona a armar su portafolio de inversión según cuánto riesgo está dispuesta a asumir, usando el modelo media-varianza de Markowitz. **Es un ejercicio académico: no constituye asesoría de inversión.**

---

## Dónde probarla

**🔗 Aplicación: <https://mft-investements.streamlit.app/>**

Si la página dice que la app "se fue a dormir", pulse el botón para despertarla; tarda unos segundos.

### Usuarios de demostración
| Para qué | Correo | Clave |
|---|---|---|
| Recorrer **todo el flujo desde cero** (responder la encuesta) | `prueba@local.test` | `Prueba1234!` |
| Saltar directo a **construir el portafolio** (perfil ya definido, A = 3) | `a3@local.test` | `Prueba1234!` |

También puede **crear su propia cuenta** en la pestaña "Crear cuenta" (solo pide correo, un alias y un rango de edad; no se recolectan cédula, teléfono ni nombre completo).

---

## Cómo interactuar (recorrido de 5 minutos)

1. **Ingrese o cree una cuenta.** Arriba aparece quién tiene la sesión abierta.
2. **Perfil de riesgo.** Nueve preguntas sobre cómo reacciona ante ganancias y pérdidas. Con el puntaje (9–27) la plataforma define su perfil y su coeficiente de aversión al riesgo **A** (8, 6, 4, 3 o 1). El perfil se mide una sola vez.
3. **Construcción del portafolio.** Elija de 3 a 11 activos del catálogo (ETF de renta variable y renta fija, REIT, oro, bitcoin y ether) y, si quiere, un peso máximo por activo. La plataforma calcula:
   - el **portafolio óptimo de riesgo** (frontera eficiente y portafolio tangente),
   - el **portafolio completo**: cuánto va a riesgo (**y\***) y cuánto al activo libre de riesgo, según su A (línea CAL, sin apalancamiento),
   - gráficos de la frontera, la CAL y su curva de indiferencia, además de betas y duration.
   El portafolio se guarda **una sola vez**.
4. **Seguimiento.** En cada ingreso se muestra cómo ha rendido el portafolio con los precios nuevos frente al benchmark (ACWI), el cambio de peso de cada activo y **recomendaciones con reglas fijas** (sin inteligencia artificial): desvío del óptimo, volatilidad fuera de perfil, activos rezagados, señales de múltiplos y datos desactualizados.

> Para ver el seguimiento con movimiento recomendamos dejar pasar algunos días de precios; el pipeline diario trae los datos nuevos cada tarde.

---

## Qué debe saber

- **Datos:** precios diarios de Yahoo Finance, actualizados de lunes a viernes a las 5:00 pm (hora de Bogotá). Base de datos y autenticación en Supabase.
- **Moneda base:** USD. **Solo posiciones largas**, sin apalancamiento.
- **Los tickers del catálogo** están pendientes de validación con el profesor.
- **Privacidad:** cada usuario solo ve sus propios datos (seguridad a nivel de fila en la base de datos).
- Las recomendaciones son **reglas fijas y explicables**; no hay IA en esta fase.

---

## Taller 2 · Curva cero cupón de TES (sección pública)

En la misma aplicación, la página **"Taller 2 · Curva TES"** se abre **sin iniciar sesión** (enlace en la pantalla de inicio). Muestra, para cada Informe Diario de Deuda Pública de [www.irc.gov.co](https://www.irc.gov.co/440):

- los **betas de Nelson-Siegel** del día (τ = 3,7) y la **curva cero cupón** de 1 a 30 años,
- la **TIR observada** de cada TES tasa fija en pesos frente a la **TIR estimada con la curva**, y la decisión **comprar / vender / mantener** (umbral: 1 desviación estándar de las diferencias),
- **duración, convexidad y DV01 por cada $1.000 millones** (10⁹ COP) de valor nominal,
- la historia de la curva desde el 2-oct-2026 (día de prueba del enunciado).

Un pipeline diario descarga los informes, los valida y calcula la curva. Para el día del enunciado:
`python -m roboadvisor.taller2.pipeline.update_tes --fecha 2026-10-02 --sin-supabase`.
Metodología y validación: [`docs/taller-2/`](docs/taller-2/README.md).

## Dónde está el código de cada taller

| | Taller 1 · Robo-advisor | Taller 2 · Curva TES | Común |
|---|---|---|---|
| Motor (puro, sin red) | `src/roboadvisor/taller1/core/` | `src/roboadvisor/taller2/core/` | — |
| Datos y pipeline | `src/roboadvisor/taller1/data/`, `taller1/pipeline/` | `src/roboadvisor/taller2/datos/`, `taller2/pipeline/` | `src/roboadvisor/comun/` (Supabase, mock, config) |
| App (Streamlit) | `app/pages/1_T1_…`, `2_T1_…`, `3_T1_…`, `app/ui/taller1/` | `app/pages/4_T2_Curva_TES.py`, `app/ui/taller2/` | `app/Inicio.py`, `app/ui/comun/` |
| Base de datos (mismo proyecto Supabase) | `supabase/migrations/0001`, `0002_*` | `supabase/migrations/0003_taller2_tes.sql` (tablas `t2_*`) | — |
| Pruebas | `tests/taller1/` | `tests/taller2/` | `tests/comun/` |
| Documentos | `docs/taller-1/` | `docs/taller-2/` | — |
| Automatización | `.github/workflows/pipeline.yml`, `pipeline-fundamentales.yml` | `.github/workflows/pipeline-taller2.yml` | `ci.yml` |

## Para ver cómo está hecho
La explicación técnica (tecnologías, carpetas, cómo levantar la aplicación en local, pruebas y despliegue) está en [**README_TECNICO.md**](README_TECNICO.md). Las especificaciones y fórmulas están en [`docs/taller-1/`](docs/taller-1/) y [`docs/taller-2/`](docs/taller-2/).

**Fechas:** Taller 1 — 12 de noviembre de 2026 · Taller 2 — 19 de noviembre de 2026.
