# E03 · Motor: cuestionario, puntaje y utilidad

**Depende de:** E00 · **Rama:** `e03-cuestionario` · **Commit:** `feat(core): E03 cuestionario, perfiles y utilidad`

## Objetivo
Implementar el cuestionario del taller, su puntaje y la función de utilidad, como código puro y probado.

## Alcance
- `core/cuestionario.py`
  - `PREGUNTAS: list[Pregunta]` con 9 ítems **transcritos del PDF del Taller 1** (`id` ∈ q1, q2a, q2b, q2c, q3, q4, q5, q6, q7; `texto`; `opciones: {a,b,c}`). Los montos de la P5 se dejan tal cual ($2.000.000; $5.000.000 al 50 %; $15.000.000 al 20 %).
  - `puntuar(respuestas: dict[str, str]) -> ResultadoEncuesta(puntaje, perfil, a, conteo)` con `puntaje = 1·#a + 2·#b + 3·#c`.
  - `PERFILES`: tabla de rangos → `(clave_perfil, etiqueta, A)` según `docs/02` (claves: `conservador`, `conservador_moderado`, `moderado`, `moderado_agresivo`, `agresivo`).
  - `ValueError` si faltan preguntas, sobran ids o hay valores distintos de a/b/c.
  - `FACTORES_SUGERIDOS`: lista de campos de contexto personal opcionales para el formulario (ocupación, rango de ingresos, dependientes económicos, nivel educativo, experiencia invirtiendo en años, horizonte principal de inversión, colchón de emergencia sí/no). Es solo metadatos para la UI y el análisis del PDF.
- `core/utilidad.py`: `utilidad(er, sigma, a) -> float` = `er − 0.5·a·sigma²`; valida `sigma ≥ 0` y `a > 0`.

## Fuera de alcance
UI, base de datos, loterías/utilidad cuadrática por juegos.

## Pruebas (`tests/core/test_cuestionario.py`, `test_utilidad.py`)
- Todas "a" → 9 → Conservador A=8; todas "c" → 27 → Agresivo A=1.
- Bordes: 12→13, 16→17, 20→21, 24→25 cambian de perfil (probar los 8 puntajes).
- Una combinación mixta calculada a mano (p. ej. 3 a, 4 b, 2 c = 3+8+6 = 17 → Moderado A=4).
- Errores: falta q7; id extra; valor "d".
- Utilidad: `utilidad(0.10, 0.20, 4) = 0.10 − 0.5·4·0.04 = 0.02`; con A creciente la utilidad decrece.

## Verificación local
```bash
pytest tests/core -q && ruff check .
python -c "from roboadvisor.core.cuestionario import puntuar; print(puntuar({k:'b' for k in ['q1','q2a','q2b','q2c','q3','q4','q5','q6','q7']}))"
```
Esperado: puntaje 18, perfil moderado, A=4.

## Criterios de aceptación
- [x] 9 preguntas con sus opciones fieles al PDF.
- [x] Mapeo puntaje→perfil correcto en todo el rango 9–27.
- [x] Sin imports de red, DB ni Streamlit en `core/`.
