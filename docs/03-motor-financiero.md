# 03 · Motor financiero (`src/roboadvisor/core/`)

Todo puro y determinista. Cada función indica su fórmula porque el PDF del taller debe explicarla.

## Estructura
```
core/
  cuestionario.py        PREGUNTAS, puntuar(respuestas) -> ResultadoEncuesta
  utilidad.py            utilidad(er, sigma, a)
  retornos.py            retornos_diarios(precios), estimar(retornos, ...) -> Estimacion
  markowitz.py           min_varianza, tangente, frontera, cal
  portafolio_completo.py y_star, componer
  riesgo.py              betas, duration_portafolio, metricas_portafolio, contribucion_riesgo
  seguimiento.py         valorar(...) -> Seguimiento
  multiplos.py           señales_multiplos(fundamentales, ...)
  recomendaciones.py     generar(contexto) -> list[Recomendacion]
```

## 1. Cuestionario
- 9 ítems (Q1, Q2A, Q2B, Q2C, Q3, Q4, Q5, Q6, Q7), respuestas `a|b|c`.
- `puntaje = 1·#a + 2·#b + 3·#c` (9–27) → perfil y A según la tabla de `02-modelo-datos.md`.
- Valida: falta de respuestas o valores fuera de `a|b|c` lanza `ValueError`.
- Los textos de las preguntas están en el PDF del Taller 1; se transcriben tal cual en `PREGUNTAS` (con las opciones).

## 2. Utilidad
`U = E(r) − ½·A·σ²`  (r y σ en términos anuales decimales).

## 3. Estimación (`retornos.py`)
1. Precios diarios `adj_close` de los tickers elegidos (todos ETF, mismo calendario); alinear por fecha común, `dropna`.
2. Retornos diarios simples `r_t = P_t / P_{t−1} − 1`; ventana = últimos `ventana_dias` (1260); exigir ≥ `min_dias` (504) o error claro indicando el ticker con historia corta.
3. `μ = 252 · media(r)` (anualizada, aritmética).
4. `Σ = 252 · LedoitWolf().fit(r).covariance_`.
5. `rf` = tasa anual de `tasa_libre_riesgo` en la última fecha disponible (decimal).
Devuelve `Estimacion(tickers, mu, sigma, rf, n_obs, fecha_fin)`.

## 4. Markowitz (`markowitz.py`)
Restricciones: `Σw = 1`, `0 ≤ w_i ≤ w_max` (con `w_max ≥ 1/n`; si no, se ajusta y se avisa). Solver: `scipy.optimize.minimize(method="SLSQP")`.
- **Mínima varianza global:** `min wᵀΣw`.
- **Portafolio tangente (óptimo de riesgo):** `max (wᵀμ − rf) / √(wᵀΣw)`. Si ningún activo supera a `rf` (Sharpe ≤ 0), se devuelve el de mínima varianza y se marca `advertencia`.
- **Frontera eficiente:** para una malla de retornos objetivo entre el retorno del mínima varianza y el máximo alcanzable con las restricciones, `min wᵀΣw` s.t. `wᵀμ = target`. ≥ 40 puntos. Debe ser monótona creciente en σ para la rama eficiente.
- **CAL óptima:** recta `E(r) = rf + S*·σ` con `S*` = Sharpe del tangente.
Salidas son dataclasses con `w` como `pd.Series` indexada por ticker.

## 5. Portafolio completo (`portafolio_completo.py`)
`y* = (E(R_p) − r_f) / (A · σ_p²)`, recortado a `[0, 1]` (sin apalancamiento).
Peso en riesgo del activo i: `y*·w_i`; peso libre de riesgo: `1 − y*`.
`E(R_c) = rf + y*(E(R_p) − rf)`, `σ_c = y*·σ_p`, `U_c = E(R_c) − ½A σ_c²`.
Se informa si el recorte a 1 fue activo (`apalancamiento_requerido = y*_sin_recorte > 1`).

## 6. Riesgo (`riesgo.py`)
- **Beta** de cada acción/ETF de renta variable vs. `ACWI`: `β = Cov(r_i, r_m) / Var(r_m)` (retornos diarios, misma ventana). Betas del portafolio = suma ponderada.
- **Duration** de renta fija: valor fijo del catálogo; `Duration_portafolio = Σ w_i · D_i` sobre la parte de renta fija (y duration contribuida al total).
- **Métricas:** σ, retorno esperado, Sharpe, `VaR` paramétrico opcional (no requerido), contribución al riesgo `w_i (Σw)_i / σ_p²`.
- **Max drawdown** y **vol realizada** a partir de series diarias (en `seguimiento`).

## 7. Seguimiento (`seguimiento.py`)
Entrada: `pesos_completo`, `fecha_base`, `rf_base`, precios diarios desde `fecha_base`, serie de rf.
Compra-y-mantiene: cantidades iniciales `q_i = V0·w_i / P_i(base)` con `V0 = 100`; la parte libre de riesgo crece a `rf_base` diaria (`(1+rf)^(1/252)`). Salidas: serie de valor, retorno acumulado, retorno anualizado (solo si ≥ 1 año; si no, `None`), volatilidad realizada anualizada (√252), max drawdown, Sharpe realizado (solo si ≥ 60 observaciones), contribución por activo, pesos actuales (deriva). También el mismo cálculo para `ACWI` como referencia.

## 8. Múltiplos (`multiplos.py`)
Aplica solo a activos de renta variable con `pe` disponible (último dato ≤ 10 días de antigüedad).
`z = (PE_i − mediana(PE_peers)) / MAD_escalada(PE_peers)` con peers = acciones del catálogo con dato. `z > +1` → "cara" (sugerir subponderar `tilt_multiplos` = 2,5 pp); `z < −1` → "barata" (sobreponderar); si hay < 4 peers con dato, no hay señal y se informa. P/B se muestra como apoyo. Las señales **ajustan una sugerencia**, no recalculan Markowitz.

## 9. Recomendaciones (`recomendaciones.py`) — reglas fijas
Entrada: portafolio guardado, `Estimacion` recalculada hoy, tangente de hoy, seguimiento, señales de múltiplos, antigüedad de datos. Salida: lista de `Recomendacion(id, severidad, ticker|None, titulo, detalle, datos)`. Orden: `accion` > `aviso` > `info`.

| id | Regla | Parámetro (config) | Severidad |
|---|---|---|---|
| R1 `deriva_pesos` | `|peso_actual_i − peso_óptimo_hoy_i| > umbral` para algún activo | `umbral_desvio = 5 pp` | aviso (acción si > 10 pp) |
| R2 `activo_rezagado` | retorno 12m del activo < rf 12m y su peso actual > mínimo | `min_peso_alerta = 5 %` | aviso |
| R3 `fuera_de_perfil` | vol realizada del portafolio completo > `σ_objetivo · (1 + tol)`, con `σ_objetivo = y*·σ_p` de la creación | `tol_vol = 25 %` | acción |
| R4 `multiplos` | señal de múltiplos "cara"/"barata" para una acción del portafolio | `z = 1`, `tilt = 2,5 pp` | info |
| R5 `datos_viejos` | último precio de algún activo con > N días hábiles | `dias_stale = 5` | aviso |
| R0 `todo_ok` | no se activó ninguna regla anterior | — | info |

Todas las recomendaciones incluyen el texto fijo: *"Ejercicio académico; no constituye asesoría financiera."* y los números que las sustentan (campo `datos`) para poder explicarlas en el PDF.

## 10. Pruebas obligatorias del motor
- Puntaje→perfil en todos los bordes (12/13, 16/17, 20/21, 24/25).
- Con 2 activos de Σ conocida, la mínima varianza coincide con la fórmula cerrada.
- Pesos suman 1, respetan `[0, w_max]`; tangente tiene Sharpe ≥ cualquier punto de la malla aleatoria.
- Frontera: σ no decreciente a lo largo de la rama eficiente; el tangente queda sobre/cerca de la frontera.
- `y*` con A=1…8 es monótona decreciente en A; recorte a [0,1] verificado.
- Seguimiento: con precios constantes y rf=0 el valor no cambia; con un solo activo replica su retorno.
- Cada regla de recomendación con un caso que la activa y uno que no.
