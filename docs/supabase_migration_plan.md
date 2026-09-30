# Weaviate → Supabase pgvector Migration Plan: What Would (S)he Say

## Goal
Move persona retrieval from Weaviate to Supabase pgvector with no user-visible change, then cancel Weaviate.
Inputs: `docs/vector_reduction_findings.md`, the Phase 0–4 artifacts in `scripts/vector-investigation/`,
and the local Parquet snapshot.

## Locked Decisions
- **Scope:** 56,478 rows: Barbie 274, Homer 25,066 + 37 backfill, Jesus 31,001 + 100 backfill.
- **Storage:** `halfvec(3072)`, `text-embedding-3-large`, cosine distance, HNSW index.
- **Layout:** one table per persona; no character filter at query time (unreachable rows are excluded at load).
- **Retrieval behavior:** top-3, cosine distance < 0.85. These are unchanged from live.
- **Frontend:** untouched. The `weaviate-chat` request/response contract `{prompt, persona}` → `{response}` is preserved.
- **Cutover control:** the `VECTOR_BACKEND` Edge Function secret (`weaviate` | `supabase`), default `weaviate`.
- **Branch:** `feat/supabase-pgvector`. Merge to `main` only with `VECTOR_BACKEND=weaviate`.
- **Compute:** Supabase Small (2 GB RAM).
- **Additional Edge Functions:** Preserve `chat` and `generate-vectorstore` as-is; neither is part of the Weaviate retrieval swap.
- **Logging amendment:** Preserve existing prompt, response, and context logging in `weaviate-chat` for before/after comparison. The metadata-only rule applies only to new Supabase-path logging.

## Guardrails
- Read-only on Weaviate throughout.
- Codex writes SQL migration files. Jeff applies them, or approves CLI apply per migration.
- Secrets come from env only. Never print vectors, full rows, or keys to the console.
- Stop at every GATE and report inline.

## Phase 0: Pre-flight
1. **[Jeff]** Confirm the Supabase project that hosts the app's Edge Functions. Retrieval must live in that project.
2. **[Jeff]** Upgrade that project to Small compute (brief restart).
3. **[Jeff]** Copy the Parquet snapshot and `phase2_migration_backfill.json` off-laptop (e.g., Google Drive).
   After Weaviate is canceled, this is the only full copy.
4. **[Codex]** Verify:
   - pgvector ≥ 0.7.0 (required for `halfvec`)
   - which schema the extension lives in
   - free disk space ≥ 3 GB
5. **[Codex]** Identify how Edge Functions deploy: Lovable-on-merge, Supabase CLI, or both. Report this, because
   it determines how Phase 4 ships.
6. **[Codex]** Read `weaviate-chat` and `weaviate-warmup`. Document:
   - the persona string values
   - the prompt assembly
   - how context is joined
   - model params
   - error handling
**GATE 0:** Report findings.

## Phase 1: Schema
Migration file: `supabase/migrations/<ts>_rag_persona_tables.sql`
- `create extension if not exists vector` (in the correct schema).
- Tables `rag_barbie`, `rag_homer`, `rag_jesus`:
  - `id uuid primary key` (Weaviate UUID; deterministic uuid5 for backfill rows)
  - `content text not null`
  - `embedding halfvec(3072) not null`
  - `character text`, `source text`
  - `metadata jsonb not null default '{}'` (all other Weaviate properties)
- Enable RLS on all three tables with no policies, so only the service role can read.
- **No HNSW index yet.** It is built after the load (Phase 2).

**GATE 1:** Jeff applies the migration.

## Phase 2: Load + Index
1. **Loader** `scripts/supabase-migration/load_vectors.py`:
   - Source: the Parquet snapshot.
   - Apply the exact Phase 2 reachable + dedup rules. Reuse the investigation code; don't reimplement.
   - Bulk insert via psycopg `COPY` over the direct/session connection, not the transaction pooler.
   - Idempotent: truncate-then-load per table.
   - **Phase 2 amendment (Jeff approved):** the earlier Homer 25,068 count came from an approximate, parallel HNSW dedup scan. Running the same investigation selection functions with one FAISS thread yielded 25,066 retained Homer snapshot rows. The loader pins FAISS to one thread and rejects any different count before loading that table.
2. **Backfill:**
   - Embed the 137 `embedding_input` strings with `text-embedding-3-large` (3072 dims, cost under $0.01).
   - Sanity check: each backfill vector's nearest neighbor is plausible (same book/chapter, or Homer).
   - Insert with deterministic UUIDs.
3. **Verify:**
   - Row counts match Locked Decisions exactly.
   - No null or wrong-dimension embeddings.
   - 20 random IDs per table: cosine similarity to the snapshot vector ≥ 0.999 (halfvec precision check).
4. **Index** (one session per table):
   - On Small compute, use `set maintenance_work_mem = '256MB';` and `set max_parallel_maintenance_workers = 0;` for a serial HNSW build. The earlier 1 GB guidance is unsafe here: the parallel Jesus build tried to resize a `/dev/shm` segment to 1,070,625,280 bytes and failed with SQLSTATE 53100, despite ample data-volume space. Barbie and Homer happened to build with 1 GB, but that setting should not be reused for Small instances.
   - `create index ... using hnsw (embedding halfvec_cosine_ops);` with defaults m=16, ef_construction=64.
   - Report build time and index size. Check swap only if the project's Supabase plan exposes advanced
     Database Memory usage telemetry (Team, Enterprise, or Platform); an absent Swap series alone is
     inconclusive because Supabase shows it only while swapping. On plans without that telemetry, record
     swap as unverified rather than treating it as a failed gate. If sustained swap is observed, Jeff bumps
     compute to Medium, rebuilds, then drops back to Small.

**GATE 2:** Report counts, verification results, and index sizes.

## Phase 3: Retrieval RPC + Parity Test
Migration file: `supabase/migrations/<ts>_match_persona_docs.sql`
- `match_persona_docs(persona text, query_embedding vector(3072), match_count int default 3, max_distance float default 0.85)`
  - Returns `id, content, character, metadata, distance`.
  - Takes the query as a `vector(3072)`, which is simpler to pass from the Edge Function, and converts it to
    `halfvec(3072)` inside the function.
  - Uses a fixed query per persona table. Rank and take the top N first, then drop anything at or above
    `max_distance`, so the HNSW index is still used.
  - Pin the extension schema so the function can always find the vector type.
  - Only the service role can run it; anonymous and logged-in users are blocked.
- **Query-embedding parity:** confirm how Weaviate `nearText` embedded query text (raw text vs. any prefix).
  Match it exactly in the new path.
- **Parity test** `scripts/supabase-migration/parity_test.py`, using the 120 queries in `data/queries.json`:
  - Supabase RPC vs. the Phase 3 exact 3072 deduped baseline: mean top-3 overlap **≥ 0.95** per persona.
  - Supabase RPC vs. live Weaviate: report only; expect small diffs from dedup, backfill, and quantization.
  - Fallback rate (no context) per persona matches baseline within ±1 query.
  - RPC latency p50/p95.

**GATE 3:** Jeff applies the migration. Codex reports parity results.

## Phase 4: Edge Function Swap
- In `weaviate-chat`, add a retrieval adapter:
  - `VECTOR_BACKEND=weaviate` → existing code path, unchanged.
  - `VECTOR_BACKEND=supabase` → embed the query (OpenAI, 3-large, 3072), call `match_persona_docs` with the
    service-role client, return the same context shape.
- Everything downstream of retrieval is byte-for-byte unchanged: prompt build, fallback prompt, `gpt-4o-mini`
  params, response shape.
- `weaviate-warmup`: under `supabase`, return 200 immediately (no-op). The frontend call stays for now.
- Add Supabase-path retrieval logs for backend, persona, result count, top distance, and retrieval ms. Do not add content or vectors to these new log statements. Keep all existing `weaviate-chat` prompt, response, and context logging unchanged.
- Deploy via the path found in Phase 0 with `VECTOR_BACKEND=weaviate`, and confirm prod behavior is unchanged.
- Smoke test with `supabase` in a non-prod invocation, or by flipping briefly, depending on the deploy path.

**GATE 4:** PR review, merge, deploy with `weaviate` active.

## Phase 5: Cutover + Soak
1. **[Jeff]** Set `VECTOR_BACKEND=supabase`.
2. **[Codex]** Run 5 live prompts per persona through the production site's Edge Function. Check that responses
   look persona-appropriate and the logs show `supabase`.
3. **Soak:** 2–3 days. Watch Edge Function errors, retrieval latency, and Supabase CPU/RAM (no swap).
4. **Rollback:** set `VECTOR_BACKEND=weaviate`, which is instant with no redeploy while Weaviate still exists.

**GATE 5:** Jeff approves decommissioning.

## Phase 6: Decommission + Cleanup
1. **[Jeff]** Confirm the off-laptop snapshot is present, then cancel Weaviate.
   Post-cancel rollback = reload Supabase from the snapshot.
2. **[Codex]** Cleanup PR:
   - Remove the Weaviate adapter, the `VECTOR_BACKEND` flag, and Weaviate secrets.
   - Make `weaviate-warmup` a permanent no-op, or remove it together with the frontend call (optional UI change).
   - Optionally rename `weaviate-chat`. This requires a frontend change, so it's a separate PR.
   - Replace the Weaviate generation scripts with a Supabase loader for new personas:
     - uses the validated serialization function
     - fails loudly on batch errors
     - checks final counts (fixes the silent 50-row drops)
   - Update both READMEs: architecture, persona generation workflow, the corrected GPT-4o-mini label.

## Acceptance Criteria (overall)
- Frontend untouched; contract preserved.
- Parity ≥ 0.95 top-3 overlap vs. exact baseline for every persona.
- Edge Function p95 latency ≤ the current Weaviate path.
- Zero Weaviate dependencies after Phase 6.
- Supabase compute stays on Small without swap under normal load.

## Known Follow-ups (out of scope)
- Barbie gets no context for 17.5% of queries at the 0.85 cutoff; evaluate lowering the cutoff or adding narration context.
- UI label says GPT-4o; the model is `gpt-4o-mini`.
