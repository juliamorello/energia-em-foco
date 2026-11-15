-- Execute em um NOVO projeto Supabase. NÃO use o SQL da versão anterior.
-- Tabelas sem políticas de acesso público: somente o servidor Streamlit com a chave secreta pode consultar.
create table if not exists public.contas (
 id uuid primary key,
 usuario text not null unique,
 senha_hash text not null,
 criado_em timestamptz not null default now()
);
create table if not exists public.consumos (
 user_id uuid not null references public.contas(id) on delete cascade,
 mes date not null,
 consumo_kwh numeric(12,2) not null check(consumo_kwh>=0),
 tarifa numeric(12,4) not null check(tarifa>=0),
 primary key (user_id,mes)
);
alter table public.contas enable row level security;
alter table public.consumos enable row level security;
-- Sem políticas públicas: acesso apenas com service_role mantida no servidor.
