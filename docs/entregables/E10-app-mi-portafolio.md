# E10 · App: Mi portafolio, comportamiento y recomendaciones

**Depende de:** E06, E09 · **Rama:** `e10-app-mi-portafolio` · **Commit:** `feat(app): E10 seguimiento del portafolio y recomendaciones`

## Objetivo
Cuando el usuario reingresa y ya tiene encuesta y portafolio, ve su portafolio, cómo se ha comportado con los datos nuevos del pipeline y recomendaciones por reglas fijas.

## Alcance
- `pages/3_Mi_portafolio.py` (requiere sesión, encuesta y portafolio; si falta algo, redirige a la etapa correspondiente)
  - **Encabezado:** perfil, A, fecha de creación, `fecha_base`, fecha del último dato y días transcurridos. Si `Seguimiento.suficiente = False`: mensaje "Aún no hay datos nuevos desde la creación" y solo se muestra la composición.
  - **Composición:** pesos iniciales vs pesos actuales (deriva), con tabla y barras.
  - **Comportamiento:** curva de valor (base 100) del portafolio frente a `ACWI`; retorno acumulado, anualizado (si aplica), volatilidad realizada, max drawdown, Sharpe realizado (si aplica); contribución por activo (en puntos).
  - **Esperado vs realizado:** retorno y σ esperados al crear vs. los realizados (explicando que en periodos cortos no son comparables).
  - **Recomendaciones:** tarjetas por severidad (`acción`, `aviso`, `info`), cada una con su explicación y los números en un expander. Incluye aviso académico. Sección de múltiplos con tabla de P/E, mediana de peers, z y señal.
  - **Referencia hoy:** el portafolio tangente recalculado con los mismos activos y datos actuales (pesos óptimos de hoy vs. pesos guardados) para alimentar R1.
  - Botón "Actualizar vista" que limpia la caché; **no** llama a Yahoo.
- `data/servicio_portafolio.py`: orquesta repositorios + `core` para producir un `ResumenPortafolio` (única función que combina datos y motor; testable con repositorios falsos).
- Cache con `st.cache_data` por (`user_id`, `ultima_fecha_precios`).

## Fuera de alcance
Cambiar el portafolio, ejecutar órdenes, notificaciones por correo, IA.

## Pruebas
- Pytest con repositorios falsos: `servicio_portafolio` produce `ResumenPortafolio` coherente para (a) portafolio recién creado, (b) 30 días después con precios sintéticos, (c) datos viejos (activa R5), (d) un activo con retorno 12m < rf (activa R2).
- Manual: checklist.

## Verificación local (manual)
Para ver comportamiento sin esperar semanas, usar el script `scripts/simular_envejecimiento.py` (lo crea este entregable) que, **solo en local y con `service_role`**, mueve `fecha_base` de un portafolio de prueba 60 días atrás (o crea uno de prueba con esa fecha). Documentar en el script que nunca debe apuntar al proyecto de producción con usuarios reales.
- [x] Portafolio con `fecha_base` movida atrás (verificado en local con el expander
      "🧪 Solo en modo mock" de la propia página, 31 días) muestra curva, retorno y
      vol coherentes con precios reales.
- [x] El peso actual del activo más rentable es mayor que el inicial (deriva) — verificado
      en browser (SPY/EFA subieron de peso, GLD —el más rezagado— bajó) y en pytest
      (`test_30_dias_despues_el_mas_rentable_pesa_mas`).
- [x] Se activan las reglas esperadas en los casos de prueba (pytest: R2 y R5); con
      datos sanos sale R0 (verificado antes de envejecer el portafolio).
- [x] Simular datos viejos → aparece R5 (cubierto en pytest con repositorios falsos,
      `test_datos_viejos_activa_r5`; no reproducido en browser por ser difícil de forzar
      con el dataset estático de 10 años de `data_local/precios.csv`).
- [x] Un usuario no puede ver el portafolio de otro (heredado del filtrado por
      `user_id` de `RepositorioUsuario`/`ClienteMock`, ya cubierto desde E07–E09).

## Criterios de aceptación
- [x] Checklist completo; las cifras coinciden con `core` en pruebas.
- [x] Ningún texto de recomendación suena a orden de compra/venta real; todas llevan el aviso académico.
- [x] La página carga en < 5 s con datos en caché (verificado en browser, modo mock).
