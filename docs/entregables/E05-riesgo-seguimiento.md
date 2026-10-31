# E05 · Motor: betas, duration, métricas y seguimiento

**Depende de:** E04 · **Rama:** `e05-riesgo-seguimiento` · **Commit:** `feat(core): E05 betas, duration, métricas y seguimiento`

## Objetivo
Cubrir el requisito de beta (acciones) y duration (bonos), las métricas del portafolio y el cálculo de cómo se ha comportado un portafolio guardado con precios nuevos. Ver `docs/03` §6–7.

## Alcance
- `core/riesgo.py`
  - `betas(retornos_activos, retornos_benchmark) -> Series` (β = Cov/Var, misma ventana). Solo para activos de renta variable; la app decide a cuáles aplicarlo según el catálogo.
  - `beta_portafolio(betas, pesos_riesgo) -> float` (ponderado solo sobre la parte de renta variable, normalizada, y también contribución al total).
  - `duration_portafolio(durations, pesos_riesgo) -> dict(duration_rf_normalizada, contribucion_total)`.
  - `metricas(port, est) -> dict` (retorno, σ, Sharpe) y `contribucion_riesgo(w, sigma) -> Series` (`w_i·(Σw)_i / σ_p²`, suma 1).
- `core/seguimiento.py`
  - `valorar(pesos_completo, fecha_base, rf_base, precios, rf_serie, v0=100) -> Seguimiento` con: serie `valor`, `retorno_acum`, `retorno_anualizado` (None si < 1 año), `vol_realizada` (anual, √252), `max_drawdown`, `sharpe_realizado` (None si < 60 observaciones), `pesos_actuales` (deriva), `contribucion` por activo (aporte al retorno en puntos).
  - La clave `RF` (peso libre de riesgo) crece a `(1+rf_base)^(1/252)` diario.
  - Mismo cálculo reutilizable para un benchmark de un solo activo (`valorar_benchmark(precios_acwi, ...)`).
  - Si hay menos de 2 observaciones tras `fecha_base`, devuelve un `Seguimiento` con `suficiente=False` (la UI mostrará "aún no hay datos nuevos").

## Fuera de alcance
Recomendaciones (E06), UI, gráficos.

## Pruebas
- Beta de un activo = 1 contra sí mismo; beta de `2·benchmark` = 2 (series sintéticas); beta de activo no correlacionado ≈ 0.
- Duration: pesos 50/50 con duration 4 y 8 → 6 normalizada; contribución al total escala con el peso de renta fija.
- `contribucion_riesgo` suma 1.
- Seguimiento: precios constantes y rf=0 → valor constante; un solo activo con 100 % → replica su retorno; 50 % rf al 5 % → crecimiento de la parte rf coincide con `(1.05)^(t/252)`; `suficiente=False` con 1 observación.
- Max drawdown con serie conocida (100,120,90,110 → −25 %).

## Verificación local
```bash
pytest tests/core -q && ruff check .
```

## Criterios de aceptación
- [ ] Todas las pruebas pasan; funciones puras.
- [ ] Series cortas no revientan: devuelven `None`/`suficiente=False` y no `NaN` silenciosos.
- [ ] Documentado en docstrings el supuesto compra-y-mantiene.
