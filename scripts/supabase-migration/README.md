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
