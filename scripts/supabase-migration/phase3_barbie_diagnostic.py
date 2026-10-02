#!/usr/bin/env python3
"""Compare Barbie exact halfvec retrieval with the float32 snapshot baseline."""

from __future__ import annotations

import json
import os

import numpy as np
import psycopg

from parity_test import (
    DATA, database_ids, exact_baseline, load_environment,
    mean_overlap, normalized, openai_embeddings, rpc_database, rpc_http,
    snapshot_matrix,
)


def main() -> None:
    load_environment()
    queries = json.loads((DATA / "queries.json").read_text(encoding="utf-8"))["barbie"]
    vectors = openai_embeddings(queries)
    with psycopg.connect(os.environ["SUPABASE_DB_URL"], connect_timeout=20, autocommit=True) as conn:
        with conn.cursor() as cursor:
            cursor.execute("select to_regclass('public.rag_barbie_embedding_hnsw_idx') is null")
            if not cursor.fetchone()[0]:
                raise RuntimeError("Barbie HNSW index still exists")
        ids, matrix = snapshot_matrix("barbie", database_ids(conn, "barbie"))
        baseline = exact_baseline(ids, matrix, vectors)
        id_to_row = {ident: row for row, ident in enumerate(ids)}
        direct: list[list[str]] = []
        http: list[list[str]] = []
        db_ms: list[float] = []
        http_ms: list[float] = []
        differences: list[dict] = []
        unit_queries = normalized(vectors)
        for i, vector in enumerate(vectors):
            db_ids, db_elapsed = rpc_database(conn, "barbie", vector)
            http_ids, http_elapsed = rpc_http("barbie", vector)
            if db_ids != http_ids:
                raise RuntimeError(f"PostgREST and database RPC differ for query {i + 1}")
            direct.append(db_ids)
            http.append(http_ids)
            db_ms.append(db_elapsed)
            http_ms.append(http_elapsed)
            missing = sorted(set(baseline[i]) - set(db_ids))
            extra = sorted(set(db_ids) - set(baseline[i]))
            if not missing and not extra:
                continue
            if len(missing) != len(extra):
                raise RuntimeError(f"Unequal swap counts for query {i + 1}")
            unit_query = unit_queries[i]
            missing_dist = sorted(float(1 - np.dot(matrix[id_to_row[ident]], unit_query)) for ident in missing)
            extra_dist = sorted(float(1 - np.dot(matrix[id_to_row[ident]], unit_query)) for ident in extra)
            gaps = [abs(left - right) for left, right in zip(missing_dist, extra_dist)]
            differences.append({"query_number": i + 1, "swapped_pairs": len(gaps),
                                "float32_distance_gaps": [round(gap, 8) for gap in gaps]})
        gaps = [gap for row in differences for gap in row["float32_distance_gaps"]]
        report = {
            "index_absent": True,
            "queries": len(queries),
            "overlap": round(mean_overlap(baseline, http), 4),
            "baseline_fallbacks": sum(not value for value in baseline),
            "rpc_fallbacks": sum(not value for value in http),
            "db_latency_p50_ms": round(float(np.percentile(db_ms, 50)), 1),
            "db_latency_p95_ms": round(float(np.percentile(db_ms, 95)), 1),
            "http_latency_p50_ms": round(float(np.percentile(http_ms, 50)), 1),
            "http_latency_p95_ms": round(float(np.percentile(http_ms, 95)), 1),
            "queries_with_swaps": len(differences),
            "swapped_pairs": len(gaps),
            "distance_gap_max": round(max(gaps, default=0), 8),
            "distance_gaps_below_0_01": all(gap < 0.01 for gap in gaps),
            "differences": differences,
        }
        output = DATA / "phase3_barbie_diagnostic.json"
        output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print({key: value for key, value in report.items() if key != "differences"}, flush=True)
        print({"report_file": output.name}, flush=True)


if __name__ == "__main__":
    main()
