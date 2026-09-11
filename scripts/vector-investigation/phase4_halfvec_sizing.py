#!/usr/bin/env python3
"""Phase 4 capacity estimate for the accepted halfvec(3072) migration shape.

This has no database/network side effects. It intentionally uses the approved
56,343 reachable records plus 137 non-empty backfill records, rather than
recomputing the non-deterministic near-duplicate candidate set.
"""

from __future__ import annotations

import json
import math
from pathlib import Path


DATA = Path(__file__).resolve().parent / "data"
REACHABLE_ROWS = 56_343
BACKFILL_ROWS = 137
DIMENSIONS = 3_072
HALFVEC_BYTES_PER_VALUE = 8 + (2 * DIMENSIONS)  # pgvector varlena header + dim/unused + float16 values
PAGE_BYTES = 8_192
USABLE_PAGE_BYTES = 8_168  # PostgreSQL BLCKSZ less page header


def mib(value: int | float) -> float:
    return round(value / 1024**2, 2)


def gib(value: int | float) -> float:
    return round(value / 1024**3, 3)


def main() -> None:
    total_rows = REACHABLE_ROWS + BACKFILL_ROWS
    vector_payload = total_rows * HALFVEC_BYTES_PER_VALUE

    # A 3072-d halfvec is large enough that its HNSW vector tuple occupies one
    # 8 KiB index page. Add a 16-neighbor graph allowance and 5–15% page/free
    # space overhead. This is a planning estimate; pg_relation_size after a
    # pilot load is the acceptance measurement.
    pages_per_vector = math.ceil((HALFVEC_BYTES_PER_VALUE + 64) / USABLE_PAGE_BYTES)
    vector_pages = total_rows * pages_per_vector * PAGE_BYTES
    graph_bytes = total_rows * 256  # default HNSW m=16, base-layer links + upper layers/tuple metadata
    hnsw_low = int((vector_pages + graph_bytes) * 1.05)
    hnsw_high = int((vector_pages + graph_bytes) * 1.15)
    report = {
        "scope": "accepted reachable corpus plus approved non-empty migration backfill only",
        "rows": {"reachable": REACHABLE_ROWS, "backfill": BACKFILL_ROWS, "total": total_rows},
        "storage": {
            "type": "halfvec(3072)",
            "bytes_per_vector_value": HALFVEC_BYTES_PER_VALUE,
            "vector_value_payload_bytes": vector_payload,
            "vector_value_payload_mib": mib(vector_payload),
            "hnsw_assumptions": "pgvector HNSW default m=16; one 8 KiB vector-tuple page per 3072-d halfvec; 5–15% index overhead",
            "hnsw_index_estimate_bytes": {"low": hnsw_low, "high": hnsw_high},
            "hnsw_index_estimate_mib": {"low": mib(hnsw_low), "high": mib(hnsw_high)},
            "vector_values_plus_hnsw_mib": {"low": mib(vector_payload + hnsw_low), "high": mib(vector_payload + hnsw_high)},
        },
        "compute": {
            "minimum_recommended_supabase_tier": "Small (2 GB RAM)",
            "not_micro_reason": "Micro has 1 GB RAM and substantial platform base memory; it leaves too little headroom for an approximately 0.46–0.50 GiB HNSW index, Postgres work memory, and normal traffic.",
            "build_note": "Create/load in batches, then build the HNSW index; monitor swap. Temporarily use Medium (4 GB) if the Small build shows swapping, then scale down after measuring pg_relation_size.",
        },
        "measurement_sql": "SELECT pg_size_pretty(pg_relation_size('documents')), pg_size_pretty(pg_relation_size('documents_embedding_hnsw_idx'));",
    }
    DATA.mkdir(exist_ok=True)
    (DATA / "phase4_halfvec_sizing.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Rows: {total_rows:,}; halfvec payload: {mib(vector_payload):.2f} MiB")
    print(f"HNSW estimate: {mib(hnsw_low):.2f}–{mib(hnsw_high):.2f} MiB; minimum tier: Small (2 GB)")


if __name__ == "__main__":
    main()
