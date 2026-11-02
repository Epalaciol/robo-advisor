-- 0002_rangos_edad.sql — amplía los rangos de edad permitidos en perfiles:
-- agrega '18-24' y '75+'. Se conserva 'otro' por compatibilidad con filas previas.
-- (Los menores de 18 no se registran: la app lo bloquea, no hay consentimiento válido.)

alter table public.perfiles drop constraint perfiles_edad_rango_check;
alter table public.perfiles add constraint perfiles_edad_rango_check
  check (edad_rango in ('18-24', '25-34', '35-44', '45-54', '55-64', '65-74', '75+', 'otro'));
