# Taller 1 · Aversión al riesgo y portafolio óptimo (Markowitz)

**Inversiones — Maestría en Finanzas, Universidad EAFIT · Semestre II de 2026**  
Profesor: Juan Carlos Botero Ramírez  
Integrantes: Sebastian Duarte Uran, Paulina Jaramillo, Juan David Londoño, Juan Luis Orrego Henao y Esteban Palacio Londoño  
Entrega: **19 de noviembre de 2026**

Este taller pide tres cosas: (1) medir el **grado de aversión al riesgo (A)** de cinco voluntarios con un
cuestionario (se recogieron 37 encuestas: los cinco voluntarios, uno por rango de edad, y un análisis
exploratorio de todas); (2) calcular el **portafolio de riesgo óptimo** con Markowitz y el **portafolio completo**
de cada persona (cuánto en activos de riesgo y cuánto en el activo libre de riesgo); y (3) construir un
**proto robo-advisor** que lo haga automáticamente.

## ¿Qué hay en esta carpeta?

| Archivo | Qué es | Para quién |
|---|---|---|
| [**Taller1_Informe.pdf**](Taller1_Informe.pdf) | El informe: explica el procedimiento paso a paso y los resultados | **Empiece por aquí** |
| [Taller1.xlsx](Taller1.xlsx) | El soporte en Excel: retornos, covarianzas, frontera, CAL, portafolio completo con y sin tope, composición por perfil, múltiplos, las 37 encuestas (puntaje, perfil, A e y* con fórmulas vivas) y las tablas del EDA | Para revisar un cálculo en detalle |
| [figuras/](figuras/) | Los gráficos del informe en imagen | Opcional |

## Cómo leer el informe

- **Resumen ejecutivo:** la respuesta en una página.
- **1 – Metodología:** el flujo completo, las herramientas y los supuestos.
- **2 – Parte 1, aversión al riesgo:** la función de utilidad, el cuestionario (puntaje 9–27 → A) y el cálculo
  paso a paso de los **cinco voluntarios** (uno por rango de edad), con su función de utilidad y su
  portafolio completo.
- **3 – Parte 2, Markowitz:** universo y datos → retorno promedio histórico, riesgo y correlaciones → el
  problema de optimización → frontera eficiente, CAL y portafolio óptimo → portafolio completo por perfil →
  **perfiles con A baja: el tope de 100 % y el valor real de y\*** → beta y duration → múltiplos.
- **4 – El aplicativo.**
- **5 – EDA de las 37 encuestas:** calidad de datos, perfil de la muestra, distribución del puntaje,
  respuestas por pregunta, confiabilidad del cuestionario (alfa de Cronbach), factores asociados y qué implica
  para el portafolio.
- **Conclusiones, limitaciones y anexos** (cuestionario completo y respuestas anonimizadas).

## Pruebe la aplicación (el "proto robo-advisor")

**🔗 <https://mft-investements.streamlit.app/>** — cree su cuenta (solo correo, alias y rango de edad),
responda el cuestionario, escoja entre 3 y 11 activos y vea su portafolio completo, la frontera eficiente y
la CAL. En cada nuevo ingreso muestra cómo le ha ido con los precios del día y da recomendaciones con
**reglas fijas** (sin inteligencia artificial). Para un recorrido rápido: `a3@local.test` / `Prueba1234!`.

**Acceso de administrador para el profesor.** Con la cuenta `admin@mft-investments.app` (la clave se envía
en el correo de entrega; no está en el repositorio) aparece la página **Administración**: lista a todos los
encuestados (alias y rango de edad, sin correos) y, para cada uno, sus respuestas y el cálculo de A, su
portafolio de riesgo y completo con el cálculo de y\* paso a paso, y el seguimiento con los precios de
hoy. Es de solo lectura.

## Cómo se ve `y*` en cada perfil

En el paso de construcción, el botón **"Cargar portafolio de referencia (11 ETF)"** carga los mismos 11 ETF
para todos los perfiles. El portafolio de riesgo óptimo es el mismo; lo que cambia con A es cuánto se invierte
en él (**y\***): con los datos del informe, 50 % (A = 8), 66 % (A = 6), 99,6 % (A = 4) y 100 % para A = 3 y 1.
En estos dos la fórmula da 133 % y 399 % (querrían endeudarse); como el modelo no admite apalancamiento se
limita a 100 %, y el informe explica el valor real y cómo se interpreta (sección 3.7).

Los 11 ETF (QQQ, SMH, COLO, ILF, EWZ, EFA, AGG, HYG, BNDX, VNQ y GLD) salen de una búsqueda sobre el catálogo:
sin SPY ni apalancados, cubriendo las clases del enunciado, la combinación de 11 con mayor Sharpe (0,67) con
pesos entre 5 % y 40 %. Sin el piso de 5 % el óptimo quedaba en solo 3 activos (40-40-20); con él entran los 11.

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
(usa los precios guardados en `data_local/taller1/`, así que no necesita internet; esa instantánea se
actualiza desde la base de datos con `python scripts/taller1/exportar_instantanea.py`).

> Ejercicio académico; no es asesoría de inversión. Los retornos pasados no garantizan resultados futuros.
