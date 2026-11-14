-- 0002: tasa libre de riesgo = T-note a 10 años (^TNX) y portafolio guardado solo con
-- los activos que quedaron con peso > 0 (puede haber menos de 3 si w_max es alto).
-- Aplicar en el SQL Editor de Supabase (no se aplica sola desde la app).

alter table public.tasa_libre_riesgo alter column fuente set default 'yahoo:^TNX';

alter table public.portafolios drop constraint if exists portafolios_tickers_check;
alter table public.portafolios
  add constraint portafolios_tickers_check check (cardinality(tickers) between 1 and 11);
