-- Phase 2. Apply only after rag_barbie has passed the load verification.
-- Run this file in its own database session after explicit approval.
set maintenance_work_mem = '1GB';
set statement_timeout = '30min';
create index if not exists rag_barbie_embedding_hnsw_idx
  on public.rag_barbie using hnsw (embedding extensions.halfvec_cosine_ops);
reset maintenance_work_mem;
reset statement_timeout;
