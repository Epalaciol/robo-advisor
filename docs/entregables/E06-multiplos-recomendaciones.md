# E06 · Motor: múltiplos y recomendaciones (reglas fijas)

**Depende de:** E05 · **Rama:** `e06-recomendaciones` · **Commit:** `feat(core): E06 múltiplos y recomendaciones por reglas`

## Objetivo
Implementar el análisis de múltiplos que pide el taller y el sistema de recomendaciones con reglas fijas y explicables (sin IA). Ver `docs/03` §8–9.

## Alcance
- `core/multiplos.py`
  - `senales_multiplos(fundamentales: DataFrame[ticker, pe, pb, fecha], elegibles: list[str], params) -> list[SenalMultiplo]` (`ticker, pe, mediana_peers, z, señal ∈ {cara, barata, neutral, sin_dato}, tilt_sugerido`).
  - `z` robusto: `(x − mediana) / (1.4826·MAD)`; si MAD = 0 → neutral. Mínimo 4 peers con dato; si no → `sin_dato` con motivo.
  - Descarta datos con más de 10 días de antigüedad o `pe ≤ 0` (utilidad negativa → `sin_dato`, motivo "P/E no significativo").
  - `peso_ajustado(pesos_actuales, senales, tilt) -> Series` (sugerencia, sin salirse de [0,1], renormalizada a la parte de riesgo).
- `core/recomendaciones.py`
  - `ContextoRecomendacion` (dataclass): portafolio guardado (pesos_riesgo, pesos_completo, y*, σ_objetivo), tangente de hoy, seguimiento, retornos 12m por activo, rf 12m, señales de múltiplos, antigüedad de datos por ticker, parámetros.
  - `generar(ctx) -> list[Recomendacion]` con las reglas R0–R5 de `docs/03` §9, ordenadas por severidad.
  - Cada `Recomendacion` incluye `datos` (los números que la sustentan) y el aviso fijo "Ejercicio académico; no constituye asesoría financiera."
- Todos los umbrales vienen de `ParametrosFinancieros` (E00).

## Fuera de alcance
Obtener datos (E10), UI, LLM, rebalanceo automático.

## Pruebas (`tests/core/test_multiplos.py`, `test_recomendaciones.py`)
- Múltiplos: peers conocidos → z esperado; MAD=0 → neutral; < 4 peers → `sin_dato`; P/E negativo → `sin_dato`; dato viejo → descartado.
- `peso_ajustado` suma lo mismo que antes y respeta [0,1].
- Una prueba **por regla** con un caso que la activa y otro que no (R1 con 4,9 pp vs 5,1 pp; R2; R3 con vol 24 % vs 26 % sobre el objetivo; R4; R5 con 5 vs 6 días hábiles).
- Sin reglas activas → solo R0.
- Orden: `accion` antes que `aviso` antes que `info`.

## Verificación local
```bash
pytest tests/core -q && ruff check .
```

## Criterios de aceptación
- [ ] Cada regla es independiente y su prueba documenta el umbral.
- [ ] Ningún texto sugiere una compra/venta concreta de dinero real; usan "considerar", "revisar".
- [ ] El aviso académico está presente en todas las recomendaciones.
