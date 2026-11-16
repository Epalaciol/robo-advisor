-- 0003 · TALLER 2 · Curva cero cupón de TES (Nelson-Siegel), TIR, decisiones y DV01.
-- Tablas propias del Taller 2 con prefijo t2_ (no se toca ninguna tabla del Taller 1).
-- Lectura pública (anon y authenticated, para la página sin login); escritura solo service_role.

create table public.t2_informes (
  fecha            date primary key,                 -- fecha del Informe Diario de TES
  total_nominal_mm bigint,                           -- "Total Tasa Fija en Pesos" (millones COP)
  promedio_var_pb  numeric(8,2),
  n_papeles        integer not null,
  via              text not null check (via in ('pdf', 'excel', 'csv')),
  fuente           text not null,                    -- nombre del archivo
  url              text,                             -- URL de descarga en irc.gov.co (si aplica)
  sha256           text,
  validado         boolean not null,                 -- true si no hubo errores de validación
  hallazgos        jsonb not null default '[]',      -- advertencias/errores V1–V6
  cargado_at       timestamptz not null default now()
);

create table public.t2_cotizaciones (
  fecha            date not null references public.t2_informes(fecha) on delete cascade,
  nemotecnico      text not null,
  tipo             text not null,                    -- TCO, TFIT, TFVT
  vencimiento      date not null,
  cupon            numeric(8,4) not null check (cupon >= 0),
  valor_nominal_mm bigint not null,                  -- saldo en circulación, millones COP
  precio_limpio    numeric(12,6) not null,
  precio_sucio     numeric(12,6) not null,
  duracion         numeric(10,4),                    -- Macaulay del informe
  tasa_pub         numeric(10,6),                    -- decimal
  origen_tasa      text check (origen_tasa in ('VAL', 'SEN')),
  tasa_prev        numeric(10,6),
  origen_prev      text check (origen_prev in ('VAL', 'SEN')),
  var_pb           numeric(10,2),
  primary key (fecha, nemotecnico)
);

create table public.t2_curvas (
  fecha        date primary key references public.t2_informes(fecha) on delete cascade,
  b0           double precision not null,
  b1           double precision not null,
  b2           double precision not null,
  tau          double precision not null,
  sse          double precision not null,
  rmse         double precision not null,
  n_papeles    integer not null,
  usar_origen  text not null,
  ponderacion  text not null,
  regla_umbral text not null,                        -- 'sigma', 'sigma_robusta' o pb fijos
  umbral_pb    double precision not null,
  convergio    boolean not null,
  calculado_at timestamptz not null default now()
);

create table public.t2_resultados (
  fecha               date not null references public.t2_curvas(fecha) on delete cascade,
  nemotecnico         text not null,
  plazo_anos          double precision not null,
  precio_estimado     double precision not null,
  tir_observada       double precision not null,
  tir_estimada        double precision not null,
  spread_pb           double precision not null,
  senal               text not null check (senal in ('Comprar', 'Vender', 'Mantener')),
  duracion_macaulay   double precision not null,
  duracion_modificada double precision not null,
  convexidad          double precision not null,
  dv01_cop            double precision not null,     -- COP por 1 pb, por $1.000.000.000 nominal
  dv01_curva_cop      double precision not null,
  primary key (fecha, nemotecnico)
);
comment on column public.t2_resultados.dv01_cop is
  'COP que cambia el valor de $1.000 millones (10^9 COP) de nominal ante 1 pb de TIR. NO 10^12.';

create table public.t2_corridas (
  id           bigint generated always as identity primary key,
  iniciado_at  timestamptz not null default now(),
  terminado_at timestamptz,
  estado       text not null check (estado in ('ok', 'parcial', 'error')),
  modo         text not null,                        -- 'diario', 'fase1', 'fase2', 'manual'
  detalle      jsonb not null default '{}'
);

-- RLS: lectura pública de los datos de mercado del Taller 2; escritura solo service_role.
alter table public.t2_informes     enable row level security;
alter table public.t2_cotizaciones enable row level security;
alter table public.t2_curvas       enable row level security;
alter table public.t2_resultados   enable row level security;
alter table public.t2_corridas     enable row level security;

create policy t2_informes_lectura     on public.t2_informes     for select to anon, authenticated using (true);
create policy t2_cotizaciones_lectura on public.t2_cotizaciones for select to anon, authenticated using (true);
create policy t2_curvas_lectura       on public.t2_curvas       for select to anon, authenticated using (true);
create policy t2_resultados_lectura   on public.t2_resultados   for select to anon, authenticated using (true);
create policy t2_corridas_lectura     on public.t2_corridas     for select to anon, authenticated using (true);

revoke all on public.t2_informes, public.t2_cotizaciones, public.t2_curvas, public.t2_resultados,
              public.t2_corridas from anon, authenticated;
grant select on public.t2_informes, public.t2_cotizaciones, public.t2_curvas, public.t2_resultados,
                public.t2_corridas to anon, authenticated;
