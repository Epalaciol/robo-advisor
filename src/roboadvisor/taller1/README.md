# Código del Taller 1 · guía de lectura

Esta carpeta contiene todo lo que calcula el robo-advisor: desde las respuestas del cuestionario hasta el
portafolio completo de cada persona. Cada archivo empieza con un texto que explica qué hace.

```
  cuestionario ─► A ─► Markowitz ─► portafolio de riesgo ─► portafolio completo (y*) ─► seguimiento
```

## `core/` — las cuentas (sin internet ni base de datos)
| Archivo | Qué hace, en una frase |
|---|---|
| [`cuestionario.py`](core/cuestionario.py) | Las 9 preguntas del enunciado; suma el puntaje (9–27) y lo convierte en perfil y A (8, 6, 4, 3, 1) |
| [`utilidad.py`](core/utilidad.py) | La utilidad U = E(r) − ½·A·σ² |
| [`retornos.py`](core/retornos.py) | De los precios diarios, calcula el retorno esperado y la matriz de riesgos (covarianzas) de cada activo |
| [`markowitz.py`](core/markowitz.py) | Portafolio de mínima varianza, portafolio óptimo de riesgo (tangente), frontera eficiente y CAL |
| [`portafolio_completo.py`](core/portafolio_completo.py) | y\* = (E(Rp) − rf)/(A·σp²): cuánto va a riesgo y cuánto al activo libre de riesgo |
| [`riesgo.py`](core/riesgo.py) | Betas de las acciones y duration de los bonos |
| [`multiplos.py`](core/multiplos.py) | Compara el P/E de hoy de cada acción con su propio histórico y sugiere subir o bajar su peso |
| [`seguimiento.py`](core/seguimiento.py) | Cómo ha rendido el portafolio desde que se armó, frente al índice mundial (ACWI) |
| [`recomendaciones.py`](core/recomendaciones.py) | Recomendaciones con reglas fijas (sin IA), siempre con el aviso "ejercicio académico" |

**Un fragmento clave** ([`portafolio_completo.py`](core/portafolio_completo.py)): la fracción que va al portafolio de riesgo.
```python
y_sin_recorte = (er_p - rf) / (a * sigma_p**2)
y = min(max(y_sin_recorte, 0.0), 1.0)  # sin apalancamiento: entre 0 % y 100 %
```

## `data/` y `pipeline/` — traer los datos
| Archivo | Qué hace |
|---|---|
| [`pipeline/update_prices.py`](pipeline/update_prices.py) | Cada día hábil descarga los precios de Yahoo Finance y los guarda |
| [`pipeline/update_fundamentals.py`](pipeline/update_fundamentals.py) | Una vez por semana guarda los múltiplos (P/E) |
| [`pipeline/validators.py`](pipeline/validators.py) | Revisa que los datos descargados sean razonables |
| [`data/`](data/) | Guarda y lee de la base de datos: usuarios, encuestas, portafolios, precios |

## `reportes/` — lo que se entrega
| Archivo | Qué hace |
|---|---|
| [`caso.py`](reportes/caso.py) | El caso de referencia (11 ETF): estima y optimiza con el mismo motor de la app |
| [`excel.py`](reportes/excel.py) | Genera `Taller1.xlsx` |
| [`informe.py`](reportes/informe.py) | Genera el informe PDF |

La aplicación web está en [`app/`](../../../app/) (páginas `1_T1_Encuesta`, `2_T1_Constructor`, `3_T1_Mi_portafolio`).
Las pruebas que garantizan los cálculos están en [`tests/taller1/`](../../../tests/taller1/).
