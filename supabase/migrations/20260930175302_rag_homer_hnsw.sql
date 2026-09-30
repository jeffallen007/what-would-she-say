-- Phase 2. Apply only after rag_homer has passed the load verification.
-- Run this file in its own database session after explicit approval.
-- Small compute: keep the HNSW build serial and below /dev/shm capacity.
set maintenance_work_mem = '256MB';
set max_parallel_maintenance_workers = 0;
set statement_timeout = '30min';
create index if not exists rag_homer_embedding_hnsw_idx
  on public.rag_homer using hnsw (embedding extensions.halfvec_cosine_ops);
reset maintenance_work_mem;
reset max_parallel_maintenance_workers;
reset statement_timeout;
