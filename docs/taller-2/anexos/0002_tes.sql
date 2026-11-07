-- Renombrar al siguiente número libre de supabase/migrations/ (0002_tes.sql o 0003_tes.sql).
-- 0002 · Taller 2: TES (informe diario, curva Nelson-Siegel, señales)
-- Lectura pública (anon) SOLO de las tablas tes_* y curvas_ns. Escritura solo service_role.

-- 1. pipeline_runs acepta tipo 'tes'
alter table public.pipeline_runs drop constraint pipeline_runs_tipo_check;
alter table public.pipeline_runs
  add constraint pipeline_runs_tipo_check check (tipo in ('precios', 'fundamentales', 'tes'));

-- 2. Tablas
create table public.tes_emisiones (
  nemotecnico  text primary key,
  tipo         text not null,                -- TCO, TFIT, TFVT...
  vencimiento  date not null,
  cupon        numeric(8,4) not null check (cupon >= 0)   -- % del facial
);

create table public.tes_informes (
  fecha          date primary key,
  total_nominal_mm bigint not null,
  via            text not null check (via in ('texto', 'ocr', 'csv')),
  url            text,                                   -- PDF de origen en irc.gov.co (null si es CSV)
  fuente         text not null default 'irc.gov.co',     -- p. ej. 'Enunciado Taller 2'
  validado       boolean not null default false,
  sha256         text,
  cargado_at     timestamptz not null default now()
);

create table public.tes_cotizaciones (
  fecha            date not null references public.tes_informes(fecha) on delete cascade,
  nemotecnico      text not null references public.tes_emisiones(nemotecnico),
  valor_nominal_mm bigint not null check (valor_nominal_mm >= 0),  -- millones COP, saldo en circulación
  precio_limpio    numeric(12,6) not null check (precio_limpio > 0),
  precio_sucio     numeric(12,6) not null check (precio_sucio >= precio_limpio),
  duracion         numeric(10,4),
  tasa_pub         numeric(10,6),
  origen_tasa      text check (origen_tasa in ('VAL', 'SEN')),
  tasa_prev        numeric(10,6),
  origen_prev      text check (origen_prev in ('VAL', 'SEN')),
  var_pb           numeric(10,2),
  primary key (fecha, nemotecnico)
);

create table public.curvas_ns (
  fecha        date primary key references public.tes_informes(fecha) on delete cascade,
  beta0        double precision not null,
  beta1        double precision not null,
  beta2        double precision not null,
  tau          double precision not null,
  sse          double precision,
  rmse         double precision,
  n_papeles    integer,
  usar_origen  text not null default 'todos' check (usar_origen in ('todos', 'SEN')),
  estado       text not null check (estado in ('ok', 'no_convergio')),
  calculado_at timestamptz not null default now()
);

create table public.tes_senales (
  fecha           date not null references public.tes_informes(fecha) on delete cascade,
  nemotecnico     text not null references public.tes_emisiones(nemotecnico),
  precio_estimado numeric(12,6) not null,
  tir_obs         double precision not null,
  tir_teo         double precision not null,
  spread_pb       double precision not null,
  senal           text not null check (senal in ('COMPRAR', 'VENDER', 'MANTENER')),
  umbral_pb       double precision not null,
  dur_macaulay    double precision,
  dur_modificada  double precision,
  convexidad      double precision,
  dv01_cop        double precision,   -- COP por 1 pb, por $1.000.000.000 (1.000 millones) de nominal
  primary key (fecha, nemotecnico)
);
comment on column public.tes_senales.dv01_cop is
  'COP por -1 pb, por 1.000 millones de COP (10^9) de valor nominal. NO 10^12.';

-- 3. RLS: lectura pública de datos de mercado de TES; escritura solo service_role
alter table public.tes_emisiones    enable row level security;
alter table public.tes_informes     enable row level security;
alter table public.tes_cotizaciones enable row level security;
alter table public.curvas_ns        enable row level security;
alter table public.tes_senales      enable row level security;

create policy tes_emisiones_lectura    on public.tes_emisiones    for select to anon, authenticated using (true);
create policy tes_informes_lectura     on public.tes_informes     for select to anon, authenticated using (true);
create policy tes_cotizaciones_lectura on public.tes_cotizaciones for select to anon, authenticated using (true);
create policy curvas_ns_lectura        on public.curvas_ns        for select to anon, authenticated using (true);
create policy tes_senales_lectura      on public.tes_senales      for select to anon, authenticated using (true);

-- 4. Privilegios: anon solo SELECT sobre tes_*; nada nuevo se concede por defecto
revoke all on public.tes_emisiones, public.tes_informes, public.tes_cotizaciones,
              public.curvas_ns, public.tes_senales from anon, authenticated;
grant select on public.tes_emisiones, public.tes_informes, public.tes_cotizaciones,
                public.curvas_ns, public.tes_senales to anon, authenticated;

alter default privileges in schema public revoke all on tables from anon;
