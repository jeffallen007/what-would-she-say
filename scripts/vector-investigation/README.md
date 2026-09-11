# Vector Reduction Investigation

This directory contains reproducible, read-only investigation tooling for the
Weaviate-to-Supabase migration assessment.

## Phase 0: Export the live snapshot

Run from the repository root:

```sh
.venv/bin/python scripts/vector-investigation/export_weaviate_snapshot.py
```

The script loads credentials only from already-set environment variables or the
existing ignored `scripts/vectorstore-generation/.env` file. It does not print
credentials or alter Weaviate. It writes one Parquet file per collection plus a
schema/count manifest to `scripts/vector-investigation/data/`, which is ignored
by Git because it includes source content and embeddings.

Required Python packages in `.venv`: `weaviate-client`, `python-dotenv`,
`pyarrow`, `pypdf`, `numpy`, and `faiss-cpu`.

To export only one collection:

```sh
.venv/bin/python scripts/vector-investigation/export_weaviate_snapshot.py --collection Homer
```

## Phase 1: Inventory the snapshot

```sh
.venv/bin/python scripts/vector-investigation/phase1_inventory.py
```

This command is fully local: it reads the Phase 0 Parquet snapshot and checked-in
source files. It writes inventory JSON/CSV reports to the ignored `data/`
directory, including the full Homer character comparison and the exact Bible
verses not represented in the Jesus collection.

## Phase 2: Reduction candidates

```sh
.venv/bin/python scripts/vector-investigation/phase2_reduction_candidates.py
```

This command also runs locally. It identifies unreachable objects, normalized
exact duplicates, and cosine-similarity near duplicates in the reachable target
corpus. It writes a migration-backfill payload for the live omissions found in
Phase 1; it does not send data to Weaviate, Supabase, or OpenAI.

## Phase 3: Dimension evaluation

```sh
.venv/bin/python scripts/vector-investigation/phase3_dimension_evaluation.py
```

Phase 3 embeds only the fixed query set and a bounded answer-evaluation sample;
it never embeds the corpus. It evaluates 3072-dimensional live and deduplicated
baselines locally and uses `gpt-4o-mini` for the blind answer-level comparison.
It prints no vectors or corpus exports.

## Serialization validation follow-up

```sh
.venv/bin/python scripts/vector-investigation/validate_weaviate_serialization.py
```

This reads the live schema and 20 deterministic snapshot objects per collection,
then makes only 60 fresh embedding requests. It records hashes and cosine metrics
locally; it does not print vector values or complete input strings.

## Phase 4: accepted halfvec sizing

```sh
.venv/bin/python scripts/vector-investigation/phase4_halfvec_sizing.py
```

This local calculation uses only the accepted 56,343 reachable records plus 137
non-empty backfill rows. It makes no database or API calls.
