#!/usr/bin/env python3
"""Compare the pgvector RPC with exact snapshot retrieval and live Weaviate.

Only IDs, distances, and timings are read. Weaviate calls are read-only.
The ignored report contains aggregate metrics only, never prompts or vectors.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from statistics import fmean

import numpy as np
import pyarrow.parquet as pq
import psycopg
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "scripts" / "vector-investigation" / "data"
PERSONAS = ("barbie", "homer", "jesus")
SNAPSHOT_COUNTS = {"barbie": 274, "homer": 25066, "jesus": 31001}
CHARACTERS = {"barbie": "Barbie Margot", "homer": "Homer Simpson", "jesus": None}
DISTANCE_CUTOFF = 0.85


def load_environment() -> None:
    load_dotenv(ROOT / ".env.local", override=False)
    load_dotenv(ROOT / "scripts" / "vectorstore-generation" / ".env", override=False)


def openai_embeddings(texts: list[str]) -> np.ndarray:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is required")
    request = urllib.request.Request(
        "https://api.openai.com/v1/embeddings",
        data=json.dumps({"model": "text-embedding-3-large", "input": texts, "encoding_format": "float"}).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            body = json.loads(response.read())
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"OpenAI embeddings HTTP {error.code}") from None
    data = sorted(body["data"], key=lambda item: item["index"])
    if len(data) != len(texts) or [item["index"] for item in data] != list(range(len(texts))):
        raise RuntimeError("OpenAI embedding response count/order mismatch")
    vectors = np.asarray([item["embedding"] for item in data], dtype=np.float32)
    if vectors.shape != (len(texts), 3072) or not np.all(np.isfinite(vectors)):
        raise RuntimeError("OpenAI query embeddings have invalid dimensions or values")
    return vectors


def normalized(vectors: np.ndarray) -> np.ndarray:
    return vectors / np.maximum(np.linalg.norm(vectors, axis=1, keepdims=True), 1e-12)


def database_ids(conn: psycopg.Connection, persona: str) -> set[str]:
    with conn.cursor() as cursor:
        cursor.execute(f"select id from public.rag_{persona}")
        return {str(row[0]) for row in cursor.fetchall()}


def snapshot_matrix(persona: str, retained_ids: set[str]) -> tuple[list[str], np.ndarray]:
    file = pq.ParquetFile(DATA / f"{persona}.parquet")
    id_groups: list[str] = []
    vector_groups: list[np.ndarray] = []
    for batch in file.iter_batches(batch_size=2048, columns=["uuid", "vector"]):
        ids = batch.column(0).to_pylist()
        mask = np.fromiter((value in retained_ids for value in ids), dtype=bool, count=len(ids))
        if not mask.any():
            continue
        vectors = batch.column(1).values.to_numpy(zero_copy_only=False).reshape(len(ids), 3072)
        id_groups.extend(value for value, keep in zip(ids, mask) if keep)
        vector_groups.append(np.asarray(vectors[mask], dtype=np.float32))
    if len(id_groups) != SNAPSHOT_COUNTS[persona] or len(set(id_groups)) != len(id_groups):
        raise RuntimeError(f"{persona} retained snapshot IDs do not match the loaded corpus")
    matrix = normalized(np.concatenate(vector_groups))
    return id_groups, matrix


def exact_baseline(ids: list[str], matrix: np.ndarray, query_vectors: np.ndarray) -> list[list[str]]:
    scores = matrix @ normalized(query_vectors).T
    results: list[list[str]] = []
    for column in range(scores.shape[1]):
        values = scores[:, column]
        top = np.argpartition(values, -3)[-3:]
        top = top[np.argsort(values[top])[::-1]]
        results.append([ids[int(i)] for i in top if values[i] > 1 - DISTANCE_CUTOFF])
    return results


def vector_literal(vector: np.ndarray) -> str:
    return "[" + ",".join(format(float(value), ".9g") for value in vector) + "]"


def rpc_http(persona: str, vector: np.ndarray) -> tuple[list[str], float]:
    ref_file = ROOT / "supabase" / ".temp" / "project-ref"
    ref = ref_file.read_text().strip() if ref_file.exists() else ""
    url = os.getenv("SUPABASE_URL") or (f"https://{ref}.supabase.co" if ref else "")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL/project-ref and SUPABASE_SERVICE_ROLE_KEY are required")
    request = urllib.request.Request(
        url.rstrip("/") + "/rest/v1/rpc/match_persona_docs",
        data=json.dumps({
            "persona": persona,
            "query_embedding": vector_literal(vector),
            "match_count": 3,
            "max_distance": DISTANCE_CUTOFF,
        }).encode(),
        headers={"Authorization": f"Bearer {key}", "apikey": key, "Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            rows = json.loads(response.read())
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"Supabase RPC HTTP {error.code}") from None
    elapsed_ms = (time.perf_counter() - started) * 1000
    return checked_rpc_rows(rows), elapsed_ms


def rpc_database(conn: psycopg.Connection, persona: str, vector: np.ndarray) -> tuple[list[str], float]:
    started = time.perf_counter()
    with conn.cursor() as cursor:
        cursor.execute(
            "select id, distance from public.match_persona_docs(%s, %s::extensions.vector(3072), 3, %s)",
            (persona, vector_literal(vector), DISTANCE_CUTOFF),
        )
        rows = cursor.fetchall()
    elapsed_ms = (time.perf_counter() - started) * 1000
    return checked_rpc_rows([{"id": str(row[0]), "distance": float(row[1])} for row in rows]), elapsed_ms


def checked_rpc_rows(rows: list[dict]) -> list[str]:
    if len(rows) > 3 or any(row["distance"] >= DISTANCE_CUTOFF for row in rows):
        raise RuntimeError("RPC returned too many or above-cutoff matches")
    distances = [row["distance"] for row in rows]
    if distances != sorted(distances):
        raise RuntimeError("RPC did not return distance order")
    return [str(row["id"]) for row in rows]


def weaviate_live(persona: str, query: str) -> list[str]:
    url = os.getenv("WEAVIATE_URL")
    key = os.getenv("WEAVIATE_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    if not url or not key or not openai_key:
        raise RuntimeError("WEAVIATE_URL, WEAVIATE_API_KEY, and OPENAI_API_KEY are required")
    collection = persona.capitalize()
    clause = "nearText: { concepts: [" + json.dumps(query) + "] }"
    character = CHARACTERS[persona]
    filter_clause = (
        "where: { path: [\"character\"], operator: Equal, valueText: " + json.dumps(character) + " }"
        if character else ""
    )
    graphql = "{ Get { " + collection + "(" + clause + " " + filter_clause + " limit: 3) { _additional { id distance } } } }"
    request = urllib.request.Request(
        url.rstrip("/") + "/v1/graphql",
        data=json.dumps({"query": graphql}).encode(),
        headers={
            "Authorization": f"Bearer {key}", "X-OpenAI-Api-Key": openai_key,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            body = json.loads(response.read())
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"Weaviate HTTP {error.code}") from None
    if body.get("errors"):
        raise RuntimeError("Weaviate GraphQL returned errors")
    rows = body["data"]["Get"][collection]
    return [str(row["_additional"]["id"]) for row in rows if float(row["_additional"]["distance"]) < DISTANCE_CUTOFF]


def mean_overlap(reference: list[list[str]], candidate: list[list[str]]) -> float:
    # Two empty result sets are a matching fallback, not zero overlap.
    return fmean(
        1.0 if not left and not right else len(set(left) & set(right)) / max(1, len(left))
        for left, right in zip(reference, candidate)
    )


def report_metrics(
    baseline: list[list[str]], rpc: list[list[str]], live: list[list[str]], latencies: list[float],
) -> dict:
    return {
        "baseline_vs_rpc_mean_top3_overlap": round(mean_overlap(baseline, rpc), 4),
        "live_vs_rpc_mean_top3_overlap": round(mean_overlap(live, rpc), 4),
        "fallback_count_baseline": sum(not rows for rows in baseline),
        "fallback_count_rpc": sum(not rows for rows in rpc),
        "fallback_count_live": sum(not rows for rows in live),
        "fallback_rate_baseline_percent": round(100 * fmean(not rows for rows in baseline), 2),
        "fallback_rate_rpc_percent": round(100 * fmean(not rows for rows in rpc), 2),
        "fallback_rate_live_percent": round(100 * fmean(not rows for rows in live), 2),
        "rpc_latency_p50_ms": round(float(np.percentile(latencies, 50)), 1),
        "rpc_latency_p95_ms": round(float(np.percentile(latencies, 95)), 1),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-only", action="store_true", help="Compute the exact local baseline; do not call RPC or Weaviate")
    parser.add_argument("--transport", choices=("http", "db"), default="http", help="RPC transport (default: HTTP PostgREST)")
    args = parser.parse_args()
    load_environment()
    dsn = os.getenv("SUPABASE_DB_URL")
    if not dsn:
        raise RuntimeError("SUPABASE_DB_URL is required")
    queries = json.loads((DATA / "queries.json").read_text(encoding="utf-8"))
    if any(len(queries[name]) != 40 for name in PERSONAS):
        raise RuntimeError("Expected 40 queries for each persona")
    if any(queries[name] != queries["barbie"] for name in PERSONAS):
        raise RuntimeError("Query groups differ; update batching before testing")
    query_vectors = openai_embeddings(queries["barbie"])
    report: dict = {
        "query_model": "text-embedding-3-large", "query_input": "raw text, case preserved, no prefix",
        "threshold": DISTANCE_CUTOFF, "transport": args.transport, "personas": {},
    }
    with psycopg.connect(dsn, connect_timeout=20, autocommit=True) as conn:
        for persona in PERSONAS:
            retained = database_ids(conn, persona)
            ids, matrix = snapshot_matrix(persona, retained)
            baseline = exact_baseline(ids, matrix, query_vectors)
            print({"persona": persona, "snapshot_baseline_rows": len(ids), "baseline_fallbacks": sum(not x for x in baseline)}, flush=True)
            del ids, matrix
            if args.baseline_only:
                continue
            rpc_results: list[list[str]] = []
            live_results: list[list[str]] = []
            latencies: list[float] = []
            for query, vector in zip(queries[persona], query_vectors):
                if args.transport == "http":
                    matches, latency = rpc_http(persona, vector)
                else:
                    matches, latency = rpc_database(conn, persona, vector)
                rpc_results.append(matches)
                latencies.append(latency)
                live_results.append(weaviate_live(persona, query))
            metrics = report_metrics(baseline, rpc_results, live_results, latencies)
            report["personas"][persona] = metrics
            print({"persona": persona, **metrics}, flush=True)
    if args.baseline_only:
        return
    report["parity_pass"] = all(
        row["baseline_vs_rpc_mean_top3_overlap"] >= 0.95
        and abs(row["fallback_count_rpc"] - row["fallback_count_baseline"]) <= 1
        for row in report["personas"].values()
    )
    (DATA / "phase3_pgvector_parity.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print({"parity_pass": report["parity_pass"], "report_file": "phase3_pgvector_parity.json"}, flush=True)
    if not report["parity_pass"]:
        raise RuntimeError("Phase 3 parity threshold not met")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        if isinstance(error, RuntimeError):
            print(f"ERROR: {error}", file=sys.stderr)
        else:
            print(f"ERROR: {type(error).__name__}", file=sys.stderr)
        raise SystemExit(1)
