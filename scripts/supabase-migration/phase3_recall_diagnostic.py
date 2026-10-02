#!/usr/bin/env python3
"""Measure RPC recall under HNSW settings; emit aggregate data only.

With --inside-function, temporarily replace the RPC body within a transaction
to set ef_search on invocation, then roll back. The deployed RPC is unchanged.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import numpy as np
import psycopg

from parity_test import (
    DATA, DISTANCE_CUTOFF, PERSONAS, database_ids, exact_baseline,
    load_environment, mean_overlap, openai_embeddings, snapshot_matrix,
    vector_literal,
)


SETTINGS = (100, 200, 400)
ROOT = Path(__file__).resolve().parents[2]
FUNCTION_SQL = ROOT / "supabase" / "migrations" / "20260930202447_match_persona_docs.sql"
FUNCTION_SIGNATURE = "public.match_persona_docs(text, extensions.vector, integer, double precision)"


def function_definition(conn: psycopg.Connection) -> str:
    with conn.cursor() as cursor:
        cursor.execute("select pg_get_functiondef(%s::regprocedure)", (FUNCTION_SIGNATURE,))
        return cursor.fetchone()[0]


def replacement_sql(ef: int) -> str:
    sql = FUNCTION_SQL.read_text(encoding="utf-8").split("-- Functions otherwise grant", 1)[0]
    marker = "  query_half := query_embedding::extensions.halfvec(3072);"
    if sql.count(marker) != 1:
        raise RuntimeError("RPC body marker changed")
    return sql.replace(marker, f"  perform pg_catalog.set_config('hnsw.ef_search', '{ef}', true);\n" + marker)


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
    parser.add_argument("--inside-function", action="store_true", help="Test a transaction-only RPC body setting")
    args = parser.parse_args()
    if any(value < 1 or value > 1000 for value in args.ef):
        parser.error("hnsw.ef_search must be between 1 and 1000")
    load_environment()
    dsn = os.getenv("SUPABASE_DB_URL")
    if not dsn:
        raise RuntimeError("SUPABASE_DB_URL is required")
    queries = json.loads((DATA / "queries.json").read_text(encoding="utf-8"))
    vectors = openai_embeddings(queries["barbie"])
    report: dict = {"transport": "direct database RPC", "setting_location": "transaction-only function body" if args.inside_function else "session", "queries_per_persona": 40, "ef_search_values": args.ef, "personas": {}}
    with psycopg.connect(dsn, connect_timeout=20, autocommit=True) as conn:
        original_function = function_definition(conn) if args.inside_function else None
        for persona in args.persona:
            ids, matrix = snapshot_matrix(persona, database_ids(conn, persona))
            baseline = exact_baseline(ids, matrix, vectors)
            persona_report: dict = {}
            for ef in args.ef:
                if args.inside_function:
                    with conn.cursor() as cursor:
                        cursor.execute("begin")
                try:
                    with conn.cursor() as cursor:
                        if args.inside_function:
                            cursor.execute(replacement_sql(ef))
                        else:
                            cursor.execute("select set_config('hnsw.ef_search', %s, false)", (str(ef),))
                    results: list[list[str]] = []
                    latencies: list[float] = []
                    for vector in vectors:
                        rows, elapsed = rpc_rows(conn, persona, vector)
                        results.append([ident for ident, _ in rows])
                        latencies.append(elapsed)
                finally:
                    if args.inside_function:
                        with conn.cursor() as cursor:
                            cursor.execute("rollback")
                        if function_definition(conn) != original_function:
                            raise RuntimeError("RPC definition was not restored after rollback")
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
    suffix += "_inside_function" if args.inside_function else ""
    output = DATA / f"phase3_recall_diagnostic{suffix}.json"
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print({"report_file": output.name}, flush=True)


if __name__ == "__main__":
    main()
