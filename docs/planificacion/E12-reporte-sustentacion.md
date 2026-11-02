# E12 · Reporte (PDF/Excel), voluntarios y sustentación

**Depende de:** E10 (idealmente E11) · **Rama:** `e12-reporte` · **Commit:** `feat(reportes): E12 generador de reporte, Excel y guion de sustentación`

## Objetivo
Producir los **entregables formales** del taller: PDF autoexplicativo (el que más pesa), Excel de soporte y código; más el análisis de los 5 voluntarios.

## Alcance
1. **Voluntarios (R3):** 5 personas, una por rango de edad (25-34, 35-44, 45-54, 55-64, 65-74), cada una usando la app real. Recolectar factores personales (ya en `perfiles.factores`) con su consentimiento. Pedir portafolios con **al menos un voluntario por perfil distinto** si es posible.
2. **`scripts/exportar_resultados.py`** (con `service_role` y solo local): genera `exports/voluntarios.csv` (alias, rango de edad, factores, puntaje, perfil, A, tickers, `y*`, retorno/σ/Sharpe del completo) y `exports/pesos_voluntarios.csv`. Sin correos. `exports/` está en `.gitignore`.
3. **`reportes/generar_excel.py`:** libro `Taller1.xlsx` con hojas: *Resumen*, *Encuestas*, *Perfil y A*, *Universo*, *Retornos*, *Covarianzas*, *Portafolio de riesgo*, *Frontera y CAL*, *Portafolio completo*, *Betas y duration*, *Múltiplos*. Valores calculados por el motor; fórmulas vivas en lo esencial (y*, utilidad, Sharpe) para que el profesor pueda revisarlas.
4. **`reportes/generar_pdf.py`** (o Quarto/Jupyter→PDF): PDF "paso a paso" con:
   1. Objetivo y alcance. 2. Metodología del cuestionario y tabla puntaje→A. 3. Los 5 voluntarios (tabla de factores y resultados) y análisis de qué factores explican la aversión (edad, ingresos, dependientes, experiencia, horizonte; con cautela por n=5). 4. Universo de activos y fuente de datos. 5. Estimación (retornos, Σ, shrinkage, supuestos). 6. Markowitz: frontera, CAL, tangente con gráficos. 7. Portafolio completo `y*` por perfil (tabla A=8…1 con el mismo portafolio de riesgo). 8. Betas y duration. 9. Múltiplos y tilts. 10. Arquitectura del proto robo-advisor (capturas de la app). 11. Limitaciones (datos históricos, μ inestable, sin apalancamiento, USD) y mejoras futuras (Taller 2, IA). 12. Anexos: fórmulas y enlaces al repositorio.
5. **`docs/guion-sustentacion.md`:** guion de 8–10 minutos (demo en vivo del registro→encuesta→portafolio→reingreso + 5 puntos clave) y preguntas probables con respuesta (por qué Ledoit-Wolf, por qué w_max, qué pasa con A=1, limitaciones de μ histórico).
6. **Lista de preguntas al profesor** (de `docs/00` §5): enviarlas antes y registrar la respuesta.

## Fuera de alcance
Taller 2; cambios funcionales en la app salvo correcciones.

## Verificación
- [ ] Cada cifra del PDF se puede rastrear al Excel o al código (mismos números).
- [ ] El PDF se entiende sin abrir el código: cada gráfico tiene explicación y cada fórmula su significado.
- [ ] Los datos personales están anonimizados (alias V1–V5) y no se suben al repo.
- [ ] Se ensayó la demo completa en local y en producción.

## Criterios de aceptación
- [ ] PDF, Excel y código listos y consistentes entre sí.
- [ ] Respaldo de datos exportado.
- [ ] Guion ensayado una vez cronometrado.
