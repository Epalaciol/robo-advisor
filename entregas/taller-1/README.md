# Taller 1 · Aversión al riesgo y portafolio óptimo (Markowitz)

**Inversiones — Maestría en Finanzas, Universidad EAFIT · Semestre II de 2026**  
Profesor: Juan Carlos Botero Ramírez  
Entrega: **19 de noviembre de 2026**

Este taller pide tres cosas: (1) medir el **grado de aversión al riesgo (A)** de cinco voluntarios con un
cuestionario; (2) calcular el **portafolio de riesgo óptimo** con Markowitz y el **portafolio completo**
de cada persona (cuánto en activos de riesgo y cuánto en el activo libre de riesgo); y (3) construir un
**proto robo-advisor** que lo haga automáticamente.

## ¿Qué hay en esta carpeta?

| Archivo | Qué es | Para quién |
|---|---|---|
| [**Taller1_Informe.pdf**](Taller1_Informe.pdf) | El informe: explica el procedimiento paso a paso y los resultados | **Empiece por aquí** |
| [Taller1.xlsx](Taller1.xlsx) | El soporte en Excel: datos, retornos, matriz de covarianzas, frontera, CAL y portafolio completo (con fórmulas vivas) | Para revisar un cálculo en detalle |
| [datos/voluntarios_plantilla.csv](datos/voluntarios_plantilla.csv) | Formato en que se cargan las respuestas de los voluntarios | Solo quien regenere el informe |
| [figuras/](figuras/) | Los gráficos del informe en imagen | Opcional |

## Cómo leer el informe (10 minutos)

1. **Sección 1 – Resumen:** la respuesta en un párrafo.
2. **Sección 2 – Aversión al riesgo:** cómo el cuestionario (9 preguntas, puntaje 9–27) se convierte en el
   coeficiente A (8, 6, 4, 3 o 1) y qué resultó con los cinco voluntarios.
3. **Sección 3 – Markowitz, en 7 pasos:** universo de 11 ETF → retornos y riesgos → frontera eficiente y CAL →
   portafolio óptimo → portafolio completo por perfil → beta y duration → múltiplos.
4. **Secciones 4 y 5:** la aplicación y las limitaciones.

## Pruebe la aplicación (el "proto robo-advisor")

**🔗 <https://mft-investements.streamlit.app/>** — cree su cuenta (solo correo, alias y rango de edad),
responda el cuestionario, escoja entre 3 y 11 activos y vea su portafolio completo, la frontera eficiente y
la CAL. En cada nuevo ingreso muestra cómo le ha ido con los precios del día y da recomendaciones con
**reglas fijas** (sin inteligencia artificial). Para un recorrido rápido: `a3@local.test` / `Prueba1234!`.

## ¿Dónde está el código?

[**`src/roboadvisor/taller1/`**](../../src/roboadvisor/taller1/README.md) — con una guía que explica cada
archivo en lenguaje sencillo. La aplicación está en [`app/`](../../app/). Las pruebas automáticas que
verifican los cálculos están en [`tests/taller1/`](../../tests/taller1/).

## Glosario de tres líneas

- **A (aversión al riesgo):** cuánto le molesta a la persona perder; mayor A, más conservadora.
- **Portafolio de riesgo óptimo:** la mezcla de activos con la mejor relación retorno/riesgo (mayor ratio de Sharpe).
- **y\*:** la fracción del dinero que, según su A, se pone en ese portafolio; el resto va al activo libre de riesgo.

## Regenerar el informe y el Excel

```
pip install -e ".[reportes]"
python -m roboadvisor.taller1.reportes
```
(usa los precios guardados en `data_local/taller1/`, así que no necesita internet).

> Ejercicio académico; no es asesoría de inversión. Los retornos pasados no garantizan resultados futuros.
