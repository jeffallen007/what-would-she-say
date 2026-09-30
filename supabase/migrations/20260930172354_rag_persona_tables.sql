-- Phase 1: store the reachable, deduplicated persona corpus in pgvector.
-- The extension is available at version 0.8.0 in this project and is not yet installed.
create schema if not exists extensions;
create extension if not exists vector with schema extensions;

-- Preserve Weaviate UUIDs for existing objects. Backfill rows will use UUIDv5.
create table public.rag_barbie (
  id uuid primary key,
  content text not null,
  embedding extensions.halfvec(3072) not null,
  character text,
  source text,
  metadata jsonb not null default '{}'::jsonb
);

create table public.rag_homer (
  id uuid primary key,
  content text not null,
  embedding extensions.halfvec(3072) not null,
  character text,
  source text,
  metadata jsonb not null default '{}'::jsonb
);

create table public.rag_jesus (
  id uuid primary key,
  content text not null,
  embedding extensions.halfvec(3072) not null,
  character text,
  source text,
  metadata jsonb not null default '{}'::jsonb
);

-- No policies: only privileged database roles and service_role may read rows.
alter table public.rag_barbie enable row level security;
alter table public.rag_homer enable row level security;
alter table public.rag_jesus enable row level security;

-- Supabase projects may grant new public tables to API roles by default.
-- Remove those grants as well as relying on RLS's default-deny behavior.
revoke all on table public.rag_barbie, public.rag_homer, public.rag_jesus
  from public, anon, authenticated;
grant select on table public.rag_barbie, public.rag_homer, public.rag_jesus
  to service_role;

-- Build HNSW indexes only after the Phase 2 load.
