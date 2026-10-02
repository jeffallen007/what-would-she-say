#!/usr/bin/env python3
"""Load the approved, reachable persona snapshot into Supabase.

Weaviate is never contacted. The local investigation selection functions are
imported so this loader does not introduce a second dedup implementation.
Run `--preflight` before `--load`; neither mode prints source rows or vectors.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from urllib.parse import urlparse

import faiss
import numpy as np
import pyarrow.parquet as pq
import psycopg
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[2]
INVESTIGATION = ROOT / "scripts" / "vector-investigation"
sys.path.insert(0, str(INVESTIGATION))
from phase2_reduction_candidates import (  # noqa: E402
    COLLECTION_RULES,
    DATA_DIR,
    exact_duplicate_stats,
    load_collection,
    near_duplicate_stats,
)


PERSONAS = ("Barbie", "Homer", "Jesus")
BACKFILL_COUNTS = {"Barbie": 0, "Homer": 37, "Jesus": 100}
# The Homer target is amended from the approximate four-thread finding after
# a repeatable single-thread selection. No load runs unless counts match.
SNAPSHOT_COUNTS = {"Barbie": 274, "Homer": 25066, "Jesus": 31001}
NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "whatwouldshesay.com")


def select(name: str) -> tuple[list[dict], np.ndarray, list[int], list[str]]:
    properties, vectors = load_collection(name)
    uuids = pq.read_table(DATA_DIR / f"{name.lower()}.parquet", columns=["uuid"]).column("uuid").to_pylist()
    target = COLLECTION_RULES[name]
    reachable = list(range(len(properties))) if target is None else [
        i for i, row in enumerate(properties) if row.get("character") == target
    ]
    exact, _ = exact_duplicate_stats(properties, reachable)
    near, _, _ = near_duplicate_stats(properties, vectors, reachable)
    selected = [i for i in reachable if i not in exact and i not in near]
    if len(selected) != SNAPSHOT_COUNTS[name]:
        raise RuntimeError(f"{name} selection count changed: {len(selected)}")
    if len({uuids[i] for i in selected}) != len(selected):
        raise RuntimeError(f"{name} selected UUIDs are not unique")
    print(f"{name}: reachable={len(reachable)}, exact={len(exact)}, near={len(near)}, selected={len(selected)}", flush=True)
    return properties, vectors, selected, uuids


def vector_literal(vector: np.ndarray) -> str:
    if vector.shape != (3072,) or not np.all(np.isfinite(vector)):
        raise RuntimeError("Invalid embedding shape or value")
    half = np.asarray(vector, dtype=np.float16)
    if not np.all(np.isfinite(half)):
        raise RuntimeError("Embedding cannot be stored as halfvec")
    # Five significant decimal digits round-trip every finite IEEE half value.
    return "[" + ",".join(format(float(value), ".5g") for value in half) + "]"


def backfill_rows() -> dict[str, list[dict]]:
    payload = json.loads((DATA_DIR / "phase2_migration_backfill.json").read_text(encoding="utf-8"))
    rows = {"Barbie": [], "Homer": payload["homer"], "Jesus": payload["jesus"]}
    for name in PERSONAS:
        if len(rows[name]) != BACKFILL_COUNTS[name]:
            raise RuntimeError(f"{name} backfill payload count changed")
    return rows


def embed_rows(rows: dict[str, list[dict]]) -> dict[str, np.ndarray]:
    load_dotenv(ROOT / "scripts" / "vectorstore-generation" / ".env", override=False)
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is required")
    result: dict[str, np.ndarray] = {}
    for name in PERSONAS:
        inputs = [row["embedding_input"] for row in rows[name]]
        batches: list[np.ndarray] = []
        for start in range(0, len(inputs), 50):
            chunk = inputs[start:start + 50]
            request = urllib.request.Request(
                "https://api.openai.com/v1/embeddings",
                data=json.dumps({"model": "text-embedding-3-large", "input": chunk, "encoding_format": "float"}).encode(),
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=120) as response:
                    body = json.loads(response.read())
            except urllib.error.HTTPError as error:
                raise RuntimeError(f"Embedding API returned HTTP {error.code}") from None
            data = sorted(body["data"], key=lambda item: item["index"])
            if len(data) != len(chunk) or [item["index"] for item in data] != list(range(len(chunk))):
                raise RuntimeError("Embedding API response count/order mismatch")
            batch = np.asarray([item["embedding"] for item in data], dtype=np.float32)
            if batch.shape != (len(chunk), 3072) or not np.all(np.isfinite(batch)):
                raise RuntimeError("Embedding API returned invalid vectors")
            batches.append(batch)
        result[name] = np.concatenate(batches) if batches else np.empty((0, 3072), dtype=np.float32)
        print(f"{name}: embedded {len(result[name])} backfill rows", flush=True)
    return result


def chapter_and_book(verse: str) -> tuple[str, str]:
    match = re.match(r"^(.*?)\s+(\d+):(\d+)$", verse.strip())
    if not match:
        return "", ""
    book = match.group(1)
    return f"{book} {match.group(2)}", book


def check_backfill_neighbors(
    name: str, properties: list[dict], vectors: np.ndarray, selected: list[int],
    backfill: list[dict], backfill_vectors: np.ndarray,
) -> None:
    if not backfill:
        return
    source = np.ascontiguousarray(vectors[selected], dtype=np.float32)
    source /= np.maximum(np.linalg.norm(source, axis=1, keepdims=True), 1e-12)
    queries = np.array(backfill_vectors, dtype=np.float32, copy=True, order="C")
    queries /= np.maximum(np.linalg.norm(queries, axis=1, keepdims=True), 1e-12)
    index = faiss.IndexFlatIP(3072)
    index.add(source)
    similarities, nearest = index.search(queries, 1)
    if name == "Homer":
        plausible = sum(properties[selected[int(i)]].get("character") == "Homer Simpson" for i in nearest[:, 0])
        print(f"Homer backfill nearest-neighbor persona check: {plausible}/{len(backfill)}", flush=True)
        if plausible != len(backfill):
            raise RuntimeError("Homer backfill nearest-neighbor sanity check failed")
    else:
        same_chapter = 0
        same_book = 0
        for row, i in zip(backfill, nearest[:, 0]):
            expected_chapter, expected_book = chapter_and_book(row["metadata"]["verse"])
            found_chapter, found_book = chapter_and_book(str(properties[selected[int(i)]].get("verse", "")))
            same_chapter += bool(expected_chapter and expected_chapter == found_chapter)
            same_book += bool(expected_book and expected_book == found_book)
        print(
            f"Jesus backfill nearest-neighbor check: same_chapter={same_chapter}/{len(backfill)}, "
            f"same_book={same_book}/{len(backfill)}, min_cosine={float(similarities.min()):.4f}",
            flush=True,
        )
    if not np.all(np.isfinite(similarities)):
        raise RuntimeError(f"{name} backfill nearest-neighbor similarity invalid")


def load_table(
    conn: psycopg.Connection, name: str, properties: list[dict], vectors: np.ndarray,
    selected: list[int], uuids: list[str], backfill: list[dict], backfill_vectors: np.ndarray,
) -> None:
    table = f"public.rag_{name.lower()}"
    existing_ids = {uuids[i] for i in selected}
    new_ids = [str(uuid.uuid5(NAMESPACE, f"rag/{name.lower()}/{row['metadata']['doc_id']}")) for row in backfill]
    if len(set(new_ids)) != len(new_ids) or any(value in existing_ids for value in new_ids):
        raise RuntimeError(f"{name} backfill UUID collision")
    started = time.monotonic()
    with conn.transaction():
        with conn.cursor() as cursor:
            cursor.execute(f"truncate table {table}")
            with cursor.copy(f"copy {table} (id, content, embedding, character, source, metadata) from stdin") as copy:
                for i in selected:
                    props = properties[i]
                    metadata = {key: value for key, value in props.items() if key not in {"content", "character", "source"}}
                    copy.write_row((
                        uuids[i], props["content"], vector_literal(vectors[i]),
                        props.get("character"), props.get("source"), json.dumps(metadata, ensure_ascii=False),
                    ))
                for new_id, row, vector in zip(new_ids, backfill, backfill_vectors):
                    meta = row["metadata"]
                    metadata = {key: value for key, value in meta.items() if key not in {"character", "source"}}
                    copy.write_row((
                        new_id, row["content"], vector_literal(vector),
                        meta.get("character"), meta.get("source"), json.dumps(metadata, ensure_ascii=False),
                    ))
            cursor.execute(f"select count(*), count(*) filter (where embedding is null or vector_dims(embedding) != 3072) from {table}")
            count, invalid = cursor.fetchone()
            if count != SNAPSHOT_COUNTS[name] + BACKFILL_COUNTS[name] or invalid:
                raise RuntimeError(f"{name} database count/dimension verification failed")
            sample = random.Random(20260930).sample(selected, 20)
            similarities = []
            for i in sample:
                cursor.execute(f"select embedding::text from {table} where id = %s", (uuids[i],))
                value = cursor.fetchone()
                if value is None:
                    raise RuntimeError(f"{name} sampled UUID missing")
                stored = np.fromstring(value[0].strip("[]"), sep=",", dtype=np.float32)
                original = vectors[i]
                if stored.shape != (3072,):
                    raise RuntimeError(f"{name} stored embedding dimension invalid")
                similarity = float(np.dot(stored, original) / (np.linalg.norm(stored) * np.linalg.norm(original)))
                similarities.append(similarity)
            if min(similarities) < 0.999:
                raise RuntimeError(f"{name} halfvec precision verification failed")
    print(
        f"{name}: loaded={count}, invalid_embeddings={invalid}, "
        f"sampled=20, min_cosine={min(similarities):.6f}, seconds={time.monotonic()-started:.1f}",
        flush=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", action="store_true", help="Run local selection only; do not connect or write")
    parser.add_argument("--load", action="store_true", help="Embed and load the three tables")
    args = parser.parse_args()
    if args.preflight == args.load:
        parser.error("choose exactly one of --preflight or --load")
    faiss.omp_set_num_threads(1)
    rows = backfill_rows()
    if args.preflight:
        for name in PERSONAS:
            select(name)
        return
    load_dotenv(ROOT / ".env.local", override=False)
    dsn = os.getenv("SUPABASE_DB_URL")
    if not dsn:
        raise RuntimeError("SUPABASE_DB_URL is required")
    embeddings = embed_rows(rows)
    if urlparse(dsn).port != 5432:
        raise RuntimeError("SUPABASE_DB_URL must use port 5432")
    with psycopg.connect(dsn, connect_timeout=20, autocommit=True) as conn:
        with conn.cursor() as cursor:
            cursor.execute("set search_path to public, extensions")
            cursor.execute("set statement_timeout to '30min'")
        for name in PERSONAS:
            properties, vectors, selected, uuids = select(name)
            check_backfill_neighbors(name, properties, vectors, selected, rows[name], embeddings[name])
            load_table(conn, name, properties, vectors, selected, uuids, rows[name], embeddings[name])
            del properties, vectors, selected, uuids


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # Driver/API exceptions can include request details or connection URLs.
        # Report only the type; known validation errors above are safe summaries.
        if isinstance(error, RuntimeError):
            print(f"ERROR: {error}", file=sys.stderr)
        else:
            print(f"ERROR: {type(error).__name__}", file=sys.stderr)
        raise SystemExit(1)
