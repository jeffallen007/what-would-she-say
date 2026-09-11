# Vector Reduction Investigation — What Would (S)he Say

## Goal
Find the smallest embedding footprint (dimensions × vector count) that keeps retrieval
effectively unchanged for users, before migrating from Weaviate to Supabase pgvector.
Read `weaviate_to_supabase_assessment.md` first for context.

## Hard Constraints
- **Read-only on Weaviate.** No deletes, updates, schema changes, or re-uploads.
- **No changes** to app code, Edge Functions, or Supabase.
- **Secrets from env vars only.** Never commit keys or exported data.
- **Spend guardrail:** OpenAI spend is limited to query embeddings (tiny). Get Jeff's approval
  before any full-corpus re-embedding; sample runs of ≤5k chunks are OK.
- **Put new work in** `scripts/vector-investigation/`. Gitignore `data/`.

## Phase 0 — Export Snapshot (reused by all later phases)
1. Pull the live schema for `Barbie`, `Homer`, and `Jesus`. Record the actual vectorizer model,
   dimensions, and distance metric. Confirm or refute the checked-in `text-embedding-3-large` / 3072 config.
2. Use a cursor to iterate every object in each collection, saving the UUID, all properties, and the vector.
3. Save to local Parquet in `data/`. This file also serves as the migration rollback snapshot.
4. Verify that exported counts match Weaviate's aggregate counts.

## Phase 1 — Inventory
- **Counts:** total per collection; per `character` value for Barbie and Homer.
- **Source comparison:** compare these to the row/chunk counts that `generate_document_objects.py`
  produces from each source file.
- **Explain the gap:** give the most likely cause of 570k vs. expected. Candidates include repeated
  upload runs appending duplicates, chunk overlap, or all characters being uploaded.
- **Length distribution:** tokens/words per chunk, per collection.

## Phase 2 — Reduction Candidates (vector count)
Report each category as a count and a % of its collection. Where one object falls into several
categories, count it once in a combined "removable" total.
- **Unreachable:** Barbie rows where `character != "Barbie Margot"` and Homer rows where
  `character != "Homer Simpson"`. The live Edge Function filters these out, so they are never retrieved.
- **Exact duplicates:** the same normalized content (lowercase, collapsed whitespace, stripped
  punctuation) plus the same character. Note whether duplicates come in whole-upload multiples,
  which is the signature of repeated runs.
- **Near-duplicates:** cosine similarity ≥ 0.98 within a persona. Report the count and sample pairs.
- **Low-value short chunks:** fewer than 4 words (e.g., "D'oh!"). Flag only. Measure how often
  they appear in the baseline top-3 (Phase 3) before recommending removal.

## Phase 3 — Dimension Evaluation
**Method:** `text-embedding-3-large` supports Matryoshka shortening. Truncating stored vectors to the
first N dims and L2-renormalizing approximates the API `dimensions` parameter, so no corpus
re-embedding is needed. Verify this on about 50 texts by comparing truncated vectors with fresh
API vectors at a given N.

**Setup:**
1. Use the deduplicated, reachable corpus from Phase 2.
2. Build a fixed query set of 40 realistic user questions per persona. Mix on-topic, off-topic,
   and emotional/advice prompts. Save it as `queries.json` so it can be reused for the migration
   A/B test.
3. Embed the queries once with `text-embedding-3-large` at 3072, then truncate them the same way
   as the corpus.
4. **Baseline:** exact (brute-force) cosine search at 3072, using live behavior: the persona
   filter, top-3, and distance < 0.85.
5. **Candidates:** 256, 512, 768, 1024, 1536, and 2000 (the max for indexed pgvector `vector`).
6. **Optional:** `text-embedding-3-small` at 1536 on a ≤5k-chunk sample, only if the large-model
   results are borderline.

**Metrics per persona × dimension:**
- Mean top-3 set overlap with the baseline, plus % of queries with an identical top-3
- Mean rank correlation of the top-3
- Fallback rate (no results under the threshold) vs. baseline
- Distance distribution shift. Recommend a recalibrated threshold if 0.85 no longer behaves the same.
  Also note whether 0.85 filters anything at all today.

**Answer-level check (two leading candidates only):** for 15 queries per persona, generate
responses with the live prompt setup (`gpt-4o-mini`, temp 0.7, 325 tokens, persona system prompts
from `my_prompts.py`). Use both baseline context and candidate context, then run a blind pairwise
LLM-judge comparison. Report the win/tie/loss rate.

**Proposed decision rule** (flag if you'd adjust it):
the smallest N where every persona has mean top-3 overlap ≥ 0.85, no increase in fallback rate,
and an answer-level tie-or-better rate ≥ 90%.

## Phase 4 — Footprint & Cost
For current state vs. each viable scenario (reduced count × N dims), estimate:
- Raw vector storage as `vector` (float32) vs. `halfvec` (float16)
- Rough HNSW index size plus text/metadata
- Which Supabase compute tier the HNSW index likely needs to fit in RAM

## Deliverables
1. `scripts/vector-investigation/`: reproducible scripts plus a README with run commands.
2. `data/queries.json`: the fixed query set, committed (no secrets).
3. `vector_reduction_findings.md`, containing:
   - A 3–5 bullet summary with the recommended **N**, the recommended **vector count**, and the storage type
   - Inventory and gap-explanation tables
   - Reduction-candidate table
   - Dimension-evaluation table (persona × N × metrics)
   - Footprint/cost table
   - Risks, open questions, and the recommended next step for the migration
