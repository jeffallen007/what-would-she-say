# Phase 2 persona load

This loader reads only the local Phase 0 Parquet snapshot and the existing
`phase2_migration_backfill.json`. It does not contact Weaviate. It imports the
Phase 2 investigation functions for reachability and duplicate selection and
pins FAISS to one thread so the Homer selection is reproducible.

From the repository root, install `scripts/supabase-migration/requirements.txt`
into the Python environment, then run:

```sh
python scripts/supabase-migration/load_vectors.py --preflight
python scripts/supabase-migration/load_vectors.py --load
```

`--preflight` needs no credentials and makes no database or API calls. `--load`
reads `SUPABASE_DB_URL` from the ignored root `.env.local` and `OPENAI_API_KEY`
from the existing ignored `scripts/vectorstore-generation/.env`. The database
URL must use a direct or session-pooler port 5432 connection. The loader embeds
the 137 backfill inputs with `text-embedding-3-large`, then truncates, copies,
checks, and commits each persona table in its own transaction. A failed table
rolls back while previously committed tables remain intact. Re-running the
loader replaces each table's contents.

Expected committed counts: Barbie 274; Homer 25,103 (including 37 backfills);
Jesus 31,101 (including 100 backfills). Every embedding must have 3,072
dimensions. The loader compares 20 stored vectors per table against their
original snapshot vectors and requires cosine similarity at least 0.999.

After all three loads pass, the three `rag_*_hnsw.sql` migration files can be
applied separately, one session per table, **only with approval**. On Small
compute they use 256 MB of maintenance memory, disable parallel maintenance
workers, and set a 30-minute statement timeout for the index build. They reset
all three settings afterward. The loader does not apply migrations.

## Phase 3 parity

Jeff applies `supabase/migrations/20260930202447_match_persona_docs.sql` after
review. Before that, the exact baseline can be checked without the RPC:

```sh
python scripts/supabase-migration/parity_test.py --baseline-only
```

After the migration is applied, add `SUPABASE_SERVICE_ROLE_KEY` to the ignored
root `.env.local` and run:

```sh
python scripts/supabase-migration/parity_test.py
```

The test uses the raw, case-preserved prompts from the fixed 120-query set. It
compares the PostgREST RPC with exact cosine retrieval on the retained 3,072-
dimensional snapshot vectors and read-only live Weaviate `nearText` queries.
The report in ignored `scripts/vector-investigation/data/phase3_pgvector_parity.json`
contains aggregate metrics only. Latency measures the HTTP RPC call, including
network and PostgREST overhead. `--transport db` is available for a direct
database diagnostic if the service-role HTTP key is unavailable.

The overlap scorer treats matching no-result fallbacks as agreement. For the
Phase 3 recall follow-up, `phase3_recall_diagnostic.py` tests 100/200/400 using
session-local `hnsw.ef_search` without changing the deployed function. Its
latency is direct database RPC time, not PostgREST time. The index-free Barbie
check is `phase3_barbie_diagnostic.py`; it reports only aggregate metrics and
query numbers for any swapped IDs. Both write ignored JSON reports under the
vector-investigation data directory.
