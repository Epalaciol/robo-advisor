# E04 · Motor: estimación, Markowitz, frontera, CAL y portafolio completo

**Depende de:** E00 · **Rama:** `e04-markowitz` · **Commit:** `feat(core): E04 estimación, Markowitz, frontera, CAL y y*`

## Objetivo
El corazón del taller: dado un panel de precios y una tasa libre de riesgo, obtener μ, Σ, portafolio de riesgo óptimo, frontera eficiente, CAL y el portafolio completo para un A. Fórmulas en `docs/03` §3–5.

## Alcance
- `core/retornos.py`
  - `retornos_mensuales(precios: DataFrame[fecha × ticker]) -> DataFrame` (cierre de mes, retornos simples, `dropna`).
  - `estimar(precios, rf, ventana_meses, min_meses) -> Estimacion` (`tickers, mu, sigma, rf, n_meses, fecha_fin`). μ = 12·media; Σ = 12·LedoitWolf. Error claro si algún ticker tiene historia insuficiente (nombrarlo).
- `core/markowitz.py`
  - `min_varianza(est, w_max) -> Portafolio`
  - `tangente(est, w_max) -> Portafolio` (con `advertencia` si Sharpe ≤ 0 → devuelve mínima varianza)
  - `frontera(est, w_max, n_puntos=40) -> DataFrame[retorno, sigma, pesos]`
  - `cal(port_tangente, rf) -> (pendiente, intercepto)`
  - `Portafolio(w: Series, retorno, sigma, sharpe, advertencia)`.
  - `w_max` efectivo = `max(w_max, 1/n)`; si hubo ajuste, queda anotado.
- `core/portafolio_completo.py`
  - `y_star(er_p, sigma_p, rf, a) -> (y_sin_recorte, y)` con recorte a [0, 1].
  - `componer(port_riesgo, rf, a) -> PortafolioCompleto(y, peso_rf, pesos_riesgo, pesos_completo, retorno, sigma, utilidad, apalancamiento_requerido)`.
- Fixtures sintéticos en `tests/conftest.py`: panel de 5 activos con retornos simulados con semilla fija (60+ meses) y una Σ conocida para pruebas analíticas.

## Fuera de alcance
Betas, duration, seguimiento (E05); acceso a datos; gráficos (E09).

## Pruebas (`tests/core/test_markowitz.py`, `test_portafolio_completo.py`)
- Dos activos no correlacionados: pesos de mínima varianza = fórmula cerrada `σ₂²/(σ₁²+σ₂²)`.
- `sum(w)=1`, `0 ≤ w ≤ w_max` en tangente, mínima varianza y todos los puntos de la frontera.
- Tangente: Sharpe ≥ el máximo Sharpe de 5.000 portafolios aleatorios factibles (con tolerancia).
- Frontera: σ no decreciente en la rama eficiente; el punto de menor σ es la mínima varianza.
- CAL: pasa por (0, rf) y por el tangente.
- `y*`: para A = 8, 6, 4, 3, 1 es no decreciente al bajar A; con retorno esperado < rf → y=0; caso con y_sin_recorte > 1 marca `apalancamiento_requerido`.
- Estimación: ticker con 20 meses → `ValueError` que nombra el ticker.
- Determinismo: dos corridas dan exactamente los mismos pesos.

## Verificación local
```bash
pytest tests/core -q && ruff check .
python scripts/demo_motor.py   # usa el panel sintético, imprime pesos, Sharpe y y* para A=8,6,4,3,1
```
(`scripts/demo_motor.py` lo crea este entregable.)

## Criterios de aceptación
- [x] Todas las pruebas de arriba pasan.
- [x] Se documentan en el docstring las fórmulas y supuestos (anualización, shrinkage).
- [x] `core/` no importa red, DB ni Streamlit.
- [x] Con tolerancia numérica documentada (p. ej. 1e-6) y sin `warnings` de SciPy no controlados.
