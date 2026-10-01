-- Phase 3: pin pgvector HNSW recall for every invocation, including PostgREST.
-- Supabase's postgres role cannot ALTER FUNCTION ... SET this extension GUC,
-- so set it in the function body with transaction-local scope.
create or replace function public.match_persona_docs(
  persona text,
  query_embedding extensions.vector(3072),
  match_count integer default 3,
  max_distance double precision default 0.85
)
returns table (
  id uuid,
  content text,
  "character" text,
  metadata jsonb,
  distance double precision
)
language plpgsql
stable
security invoker
set search_path = pg_catalog, extensions
as $$
declare
  query_half extensions.halfvec(3072);
begin
  if persona not in ('barbie', 'homer', 'jesus') or persona is null then
    raise exception 'Unsupported persona' using errcode = '22023';
  end if;
  if query_embedding is null or match_count is null or match_count < 1 or match_count > 100
     or max_distance is null or max_distance <= 0 or max_distance > 2 then
    raise exception 'Invalid match_persona_docs arguments' using errcode = '22023';
  end if;

  perform pg_catalog.set_config('hnsw.ef_search', '200', true);
  query_half := query_embedding::extensions.halfvec(3072);

  if persona = 'barbie' then
    return query
    with ranked as materialized (
      select d.id, d.content, d."character", d.metadata,
             (d.embedding <=> query_half) as distance
      from public.rag_barbie as d
      order by d.embedding <=> query_half
      limit match_count
    )
    select ranked.id, ranked.content, ranked."character", ranked.metadata, ranked.distance
    from ranked
    where ranked.distance < max_distance
    order by ranked.distance;
  elsif persona = 'homer' then
    return query
    with ranked as materialized (
      select d.id, d.content, d."character", d.metadata,
             (d.embedding <=> query_half) as distance
      from public.rag_homer as d
      order by d.embedding <=> query_half
      limit match_count
    )
    select ranked.id, ranked.content, ranked."character", ranked.metadata, ranked.distance
    from ranked
    where ranked.distance < max_distance
    order by ranked.distance;
  else
    return query
    with ranked as materialized (
      select d.id, d.content, d."character", d.metadata,
             (d.embedding <=> query_half) as distance
      from public.rag_jesus as d
      order by d.embedding <=> query_half
      limit match_count
    )
    select ranked.id, ranked.content, ranked."character", ranked.metadata, ranked.distance
    from ranked
    where ranked.distance < max_distance
    order by ranked.distance;
  end if;
end;
$$;

revoke all on function public.match_persona_docs(text, extensions.vector, integer, double precision)
  from public, anon, authenticated;
grant execute on function public.match_persona_docs(text, extensions.vector, integer, double precision)
  to service_role;
