#!/usr/bin/env python3
"""Measure RPC recall under session-local HNSW settings; emit aggregate data only.

Session-local settings have the same value at the query as a function SET clause,
while leaving the deployed function unchanged during exploration.
"""

from __future__ import annotations

import argparse
import json
import os
import time

import numpy as np
import psycopg

from parity_test import (
    DATA, DISTANCE_CUTOFF, PERSONAS, database_ids, exact_baseline,
    load_environment, mean_overlap, openai_embeddings, snapshot_matrix,
    vector_literal,
)


SETTINGS = (100, 200, 400)


def rpc_rows(conn: psycopg.Connection, persona: str, vector: np.ndarray) -> tuple[list[tuple[str, float]], float]:
    started = time.perf_counter()
    with conn.cursor() as cursor:
        cursor.execute(
            "select id, distance from public.match_persona_docs(%s, %s::extensions.vector(3072), 3, %s)",
            (persona, vector_literal(vector), DISTANCE_CUTOFF),
        )
        rows = [(str(row[0]), float(row[1])) for row in cursor.fetchall()]
    return rows, (time.perf_counter() - started) * 1000


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--persona", choices=PERSONAS, nargs="+", default=PERSONAS)
    parser.add_argument("--ef", type=int, nargs="+", default=SETTINGS)
    args = parser.parse_args()
    if any(value < 1 or value > 1000 for value in args.ef):
        parser.error("hnsw.ef_search must be between 1 and 1000")
    load_environment()
    dsn = os.getenv("SUPABASE_DB_URL")
    if not dsn:
        raise RuntimeError("SUPABASE_DB_URL is required")
    queries = json.loads((DATA / "queries.json").read_text(encoding="utf-8"))
    vectors = openai_embeddings(queries["barbie"])
    report: dict = {"transport": "direct database RPC", "queries_per_persona": 40, "ef_search_values": args.ef, "personas": {}}
    with psycopg.connect(dsn, connect_timeout=20, autocommit=True) as conn:
        for persona in args.persona:
            ids, matrix = snapshot_matrix(persona, database_ids(conn, persona))
            baseline = exact_baseline(ids, matrix, vectors)
            persona_report: dict = {}
            for ef in args.ef:
                with conn.cursor() as cursor:
                    cursor.execute("select set_config('hnsw.ef_search', %s, false)", (str(ef),))
                results: list[list[str]] = []
                latencies: list[float] = []
                for vector in vectors:
                    rows, elapsed = rpc_rows(conn, persona, vector)
                    results.append([ident for ident, _ in rows])
                    latencies.append(elapsed)
                row = {
                    "overlap": round(mean_overlap(baseline, results), 4),
                    "fallback_baseline": sum(not value for value in baseline),
                    "fallback_rpc": sum(not value for value in results),
                    "latency_p50_ms": round(float(np.percentile(latencies, 50)), 1),
                    "latency_p95_ms": round(float(np.percentile(latencies, 95)), 1),
                }
                persona_report[str(ef)] = row
                print({"persona": persona, "ef_search": ef, **row}, flush=True)
            report["personas"][persona] = persona_report
            del matrix
    suffix = "_" + "_".join(args.persona) if tuple(args.persona) != PERSONAS else ""
    output = DATA / f"phase3_recall_diagnostic{suffix}.json"
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print({"report_file": output.name}, flush=True)


if __name__ == "__main__":
    main()
