# Código del Taller 2 · guía de lectura

Esta carpeta calcula la curva cero cupón de los TES. Está dividida en **cuatro partes**, de la más
conceptual a la más operativa. No hace falta saber programar para seguir la idea: cada archivo empieza
con un texto que explica qué hace.

```
  datos/      ─►  core/        ─►  pipeline/       ─►  reportes/
  (leer el        (las cuentas:      (hacerlo cada       (Excel, PDF
   informe)        curva, TIR…)       día y guardarlo)    y gráficos)
```

## 1. `core/` — las cuentas (el corazón del taller)
Código "puro": recibe números y devuelve números, sin internet ni base de datos; por eso se puede probar sola.

| Archivo | Qué hace, en una frase |
|---|---|
| [`flujos.py`](core/flujos.py) | Arma el calendario de pagos de cada bono (cupones anuales y los 100 finales) y el tiempo de cada pago |
| [`nelson_siegel.py`](core/nelson_siegel.py) | La curva: dada la fecha futura *t*, devuelve la tasa cero cupón y el factor de descuento |
| [`calibracion.py`](core/calibracion.py) | Encuentra los betas que hacen que los precios de la curva se parezcan lo más posible a los del mercado (el "Solver" del Excel) |
| [`rendimientos.py`](core/rendimientos.py) | TIR, duración, convexidad y DV01 |
| [`senales.py`](core/senales.py) | Decide **comprar / vender / mantener** comparando TIR observada y estimada |
| [`analisis.py`](core/analisis.py) | Une todo lo anterior para un día: devuelve la tabla completa por papel |

### Tres fragmentos clave

**La curva** ([`nelson_siegel.py`](core/nelson_siegel.py)): la tasa a plazo *t* depende de tres números (β0 nivel, β1 pendiente, β2 curvatura) y de τ.
```python
carga = (1 - exp(-t / tau)) / (t / tau)
tasa = b0 + b1 * carga + b2 * (carga - exp(-t / tau))
```

**El ajuste** ([`calibracion.py`](core/calibracion.py)): se buscan los betas que minimizan el error entre el precio de mercado y el de la curva, papel por papel.
```python
residuo = precio_sucio_observado - precio_con_la_curva(papel, betas)
```

**La decisión** ([`senales.py`](core/senales.py)): si la TIR observada supera a la estimada por más de un umbral, el papel rinde de más (barato); si queda por debajo, rinde de menos (caro).
```python
if spread_pb > umbral:
    return "Comprar"
if spread_pb < -umbral:
    return "Vender"
return "Mantener"
```

## 2. `datos/` — traer y revisar la información
| Archivo | Qué hace |
|---|---|
| [`irc.py`](datos/irc.py) | Descarga el informe diario de www.irc.gov.co |
| [`informe.py`](datos/informe.py) | Lee la tabla del PDF y la **valida** (¿cuadra el total? ¿coinciden fechas y nemotécnicos? ¿es coherente el cupón corrido?) |
| [`repositorio.py`](datos/repositorio.py) | Guarda y lee los resultados en la base de datos (Supabase) |

## 3. `pipeline/` — hacerlo todos los días
| Archivo | Qué hace |
|---|---|
| [`procesar.py`](pipeline/procesar.py) | Para cada día: leer → validar → calibrar (partiendo de los betas del día anterior) |
| [`update_tes.py`](pipeline/update_tes.py) | El comando que ejecuta el proceso automático diario y carga a la base de datos |
| [`validacion.py`](pipeline/validacion.py) | Las pruebas de la entrega: compara contra el Excel del profesor y el del grupo (resultados en [`docs/taller-2/09-validacion.md`](../../../docs/taller-2/09-validacion.md)) |

## 4. `reportes/` — lo que se entrega
| Archivo | Qué hace |
|---|---|
| [`excel.py`](reportes/excel.py) | Genera el Excel del 2-oct con fórmulas vivas |
| [`informe.py`](reportes/informe.py) | Genera el informe PDF |
| [`graficas.py`](reportes/graficas.py) | Gráficos interactivos de la página web |

La página web que muestra todo esto es [`app/pages/4_T2_Curva_TES.py`](../../../app/pages/4_T2_Curva_TES.py).
Las pruebas que garantizan los cálculos están en [`tests/taller2/`](../../../tests/taller2/).
