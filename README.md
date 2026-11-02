# MFT Investments · Robo-advisor

**Taller 1 de Inversiones — Maestría en Finanzas, EAFIT (2026-II)**
*Quantitative Research & Asset Management*

Una plataforma que ayuda a una persona a armar su portafolio de inversión según cuánto riesgo está dispuesta a asumir, usando el modelo media-varianza de Markowitz. **Es un ejercicio académico: no constituye asesoría de inversión.**

---

## Dónde probarla

**🔗 Aplicación: `https://TU-APP.streamlit.app`** <!-- TODO: reemplazar por la URL real de Streamlit Cloud -->

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
4. **Seguimiento.** En cada ingreso se muestra cómo ha rendido el portafolio con los precios nuevos frente al benchmark (ACWI), la deriva de pesos y **recomendaciones con reglas fijas** (sin inteligencia artificial): desvío del óptimo, volatilidad fuera de perfil, activos rezagados, señales de múltiplos y datos desactualizados.

> Para ver el seguimiento con movimiento recomendamos dejar pasar algunos días de precios; el pipeline diario trae los datos nuevos cada tarde.

---

## Qué debe saber

- **Datos:** precios diarios de Yahoo Finance, actualizados de lunes a viernes a las 5:00 pm (hora de Bogotá). Base de datos y autenticación en Supabase.
- **Moneda base:** USD. **Solo posiciones largas**, sin apalancamiento.
- **Los tickers del catálogo** están pendientes de validación con el profesor.
- **Privacidad:** cada usuario solo ve sus propios datos (seguridad a nivel de fila en la base de datos).
- Las recomendaciones son **reglas fijas y explicables**; no hay IA en esta fase.

## Para ver cómo está hecho
La explicación técnica (tecnologías, carpetas, cómo levantar la aplicación en local, pruebas y despliegue) está en [**README_TECNICO.md**](README_TECNICO.md). Las especificaciones y fórmulas están en la carpeta [`docs/`](docs/).

**Fechas:** Taller 1 — 12 de noviembre de 2026 · Taller 2 — 19 de noviembre de 2026.
