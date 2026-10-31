# 00 · Contexto, requisitos y supuestos

## 1. Origen
Taller 1 de Inversiones (EAFIT, Semestre II 2026, prof. Juan Carlos Botero). Grupos de 4. **Entrega: 12 de noviembre de 2026.**
Entregable formal: **PDF** autoexplicativo (el que más pesa) + Excel + código Python. El Excel solo se revisa si hay dudas.

## 2. Qué pide el taller y cómo lo cubre la app

| # | Requisito del taller | Dónde se cubre | Entregable |
|---|---|---|---|
| R1 | Cuestionario de 9 ítems, puntaje 9–27 → perfil y A (8, 6, 4, 3, 1) | `core/cuestionario.py`, página Encuesta | E03, E08 |
| R2 | Utilidad `U = E(r) − ½·A·σ²` | `core/utilidad.py` | E03 |
| R3 | Encuestar 5 voluntarios (uno por rango de edad 25-34 … 65-74) y recoger datos personales que expliquen la aversión | `perfiles.factores`, tabla de resultados, export | E08, E12 |
| R4 | Universo de activos amplio: acciones Colombia/Latam, EE.UU., EAFE, TES, renta fija IG/HY/resto del mundo, REITs, cripto | catálogo `activos` (≈22) | E01, E02 |
| R5 | Portafolio óptimo de riesgo (Markowitz) y portafolio completo según el perfil (`y*`) | `core/markowitz.py`, `core/portafolio_completo.py` | E04 |
| R6 | Mostrar composición, σ, retorno histórico, Sharpe | página Constructor | E09 |
| R7 | Frontera eficiente y CAL óptima | `core/markowitz.py` + gráfico | E04, E09 |
| R8 | Beta de las acciones y Duration de los bonos | `core/riesgo.py` | E05 |
| R9 | Análisis de múltiplos (tipo investing.com) para sobre/subponderar acciones frente al neutral | `core/multiplos.py` | E06 |
| R10 | "Proto robo-advisor" que el usuario pueda usar (registro, perfil, portafolio) | app Streamlit + Supabase | E07–E10 |
| R11 | Documentar paso a paso en PDF | generador de reporte + guion | E12 |

Nota: la introducción del taller menciona obtener la función de utilidad cuadrática mediante **loterías**, pero el cuerpo no las desarrolla. Se deja como pregunta al profesor (ver §4) y no se implementa.

## 3. Alcance de esta fase (lo que pidió el equipo)
Registro → encuesta → guardar usuario y resultado → escoger activos y armar el portafolio (**una sola vez**) → guardar portafolio ligado a la persona y su aversión → al reingresar, mostrar el portafolio y su comportamiento con datos nuevos → recomendaciones con **valores/reglas fijas** → pipeline diario de datos (no tiempo real).

**Fuera de alcance ahora:** Taller 2 (Nelson-Siegel, TES, DV01), IA/LLM, websockets, ejecución real de órdenes, rebalanceo automático, múltiples portafolios por usuario.

## 4. Supuestos por defecto (cambiarlos = actualizar `config.py` y este doc)

| Tema | Supuesto | Por qué |
|---|---|---|
| Moneda | Todo en **USD** (ETF/ADR/cripto cotizan en USD) | Evita convertir COP y mezclar efecto cambiario en el primer corte |
| Selección | El usuario elige **de 3 a 11 activos**; la app optimiza los pesos | El taller habla de "11 activos"; el equipo pidió que el usuario escoja |
| Posiciones | Solo largas, sin apalancamiento: `0 ≤ y* ≤ 1` | A=1 podría dar y*>100% |
| Tope por activo | `w_max = 40%` (config) | Markowitz con medias históricas concentra en 1–2 activos |
| Retornos | Mensuales simples sobre `adj_close`, ventana **60 meses**, mínimo 36 | Estabilidad y comparabilidad |
| μ | Media histórica anualizada (×12) | Es lo que pide el taller; se documenta su fragilidad |
| Σ | Covarianza anualizada (×12) con **Ledoit-Wolf** | Reduce ruido de estimación |
| Tasa libre de riesgo | Letra del Tesoro 3 meses (`^IRX`) | Sin llave de API; coherente con activos en USD |
| Benchmark de beta | `ACWI` (acciones globales) | Mismo benchmark para Colombia/Latam/EE.UU./EAFE |
| Seguimiento | Compra y mantiene desde `fecha_base` (pesos derivan); parte libre de riesgo rinde a la tasa de ese día | Simple y explicable; el rebalanceo es una *recomendación* |
| Datos | Cierre diario vía pipeline 5:00 pm Bogotá, no tiempo real | Portafolio de largo plazo |
| Recomendaciones | Reglas fijas con umbrales en `config.py` + aviso "ejercicio académico" | Sin IA en esta fase |
| TES / renta fija Colombia | Fila `TES_COP` en catálogo **inactiva**; se habilita con el Taller 2 | No hay ETF fiable en Yahoo |

## 5. Preguntas para el profesor (enviar antes de la entrega)
1. ¿Cuántos activos exactamente? ("11 activos" vs. "universo lo más completo posible").
2. ¿La parte de loterías/utilidad cuadrática se evalúa en este taller?
3. ¿Se permite apalancamiento cuando A=1 (y*>100%)?
4. ¿Moneda de referencia: USD o COP?
5. ¿Es válido usar fuentes distintas a investing.com para los múltiplos (Yahoo Finance)?
6. ¿La tasa libre de riesgo debe ser de corto plazo (T-bill 3 meses, `^IRX`, la convención de
   libro de texto para Markowitz/CAL) o de largo plazo (T-note 10 años, `^TNX`), dado que el
   horizonte real del portafolio es de años? Usamos `^IRX` por defecto (sin riesgo de tasa,
   coherente con "libre de riesgo"); `^TNX` sí tiene riesgo de precio y ya está representado
   por activos como `TLT`/`IEF` en el catálogo.
7. ¿`μ` debe estimarse como promedio histórico simple (lo que hacemos, §3 de
   `03-motor-financiero.md`) o con un modelo tipo CAPM (`rf + β·(E(Rm)−rf)`)? Son métodos
   legítimos distintos: el histórico refleja lo que el activo *realmente* rindió en la ventana
   (puede estar inflado por una racha reciente, ej. oro 2021–2026); CAPM refleja lo que
   *debería* rendir según su riesgo sistemático, independiente de su historia. Usamos el
   histórico por ser el estándar del enfoque Markowitz clásico del taller.
8. ¿Por qué retornos mensuales y no diarios para estimar `μ`/`Σ`? Decisión deliberada
   (ver tabla §3 "Estabilidad y comparabilidad"): con datos diarios, `μ` es mucho más ruidoso
   (el error estándar de la media baja lento frente a la volatilidad de alta frecuencia) y `Σ`
   se distorsiona por efectos de no-sincronía/autocorrelación de corto plazo entre activos con
   distintos calendarios de cotización (cripto 7 días vs. acciones 5, distintas zonas horarias).
   Como el portafolio es de asignación estratégica de largo plazo (no trading), el ruido diario
   no aporta señal útil a Markowitz y sí perjudica la estabilidad de la estimación.

## 6. Riesgos conocidos
- `yfinance` no es API oficial: puede fallar o limitar peticiones → por eso existe el pipeline y la app nunca llama a Yahoo.
- Cripto cotiza 7 días; acciones 5 → se alinea al calendario de acciones (cierre mensual).
- Múltiplos de ETF en Yahoo son incompletos → la regla de múltiplos aplica solo donde hay dato (ver E06).
- Datos personales de voluntarios: consentimiento explícito, RLS y alias; nada en el repo.
