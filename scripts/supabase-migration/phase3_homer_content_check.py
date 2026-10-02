#!/usr/bin/env python3
"""Compare post-dedup Homer baseline and deployed RPC by normalized content."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from collections import Counter
from statistics import fmean

import numpy as np
import psycopg

from parity_test import (
    DATA, DISTANCE_CUTOFF, ROOT, database_ids, exact_baseline,
    load_environment, openai_embeddings, snapshot_matrix,
    vector_literal,
)

sys.path.insert(0, str(ROOT / "scripts" / "vector-investigation"))
from phase2_reduction_candidates import normalized_content  # noqa: E402


def rpc_http_rows(vector: np.ndarray) -> list[dict]:
    ref_file = ROOT / "supabase" / ".temp" / "project-ref"
    ref = ref_file.read_text().strip() if ref_file.exists() else ""
    url = os.getenv("SUPABASE_URL") or (f"https://{ref}.supabase.co" if ref else "")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError("Supabase URL and service role key are required")
    request = urllib.request.Request(
        url.rstrip("/") + "/rest/v1/rpc/match_persona_docs?select=id,content,distance&order=distance.asc",
        data=json.dumps({"persona": "homer", "query_embedding": vector_literal(vector),
                         "match_count": 3, "max_distance": DISTANCE_CUTOFF}).encode(),
        headers={"Authorization": f"Bearer {key}", "apikey": key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            rows = json.loads(response.read())
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"Supabase RPC HTTP {error.code}") from None
    if len(rows) > 3 or any(row["distance"] >= DISTANCE_CUTOFF for row in rows):
        raise RuntimeError("RPC result violated top-3 distance cutoff")
    return rows


def overlap(left: list[str], right: list[str]) -> float:
    if not left and not right:
        return 1.0
    return sum((Counter(left) & Counter(right)).values()) / max(1, len(left))


def unmatched_ids(ids: list[str], texts: list[str], surplus: Counter[str]) -> list[str]:
    result: list[str] = []
    for ident, text in zip(ids, texts):
        if surplus[text] > 0:
            result.append(ident)
            surplus[text] -= 1
    return result


def exact_half_distances(conn: psycopg.Connection, vector: np.ndarray, ids: list[str]) -> dict[str, float]:
    if not ids:
        return {}
    with conn.cursor() as cursor:
        cursor.execute(
            "select id, embedding <=> %s::extensions.halfvec(3072) "
            "from public.rag_homer where id = any(%s::uuid[])",
            (vector_literal(vector), ids),
        )
        return {str(ident): float(distance) for ident, distance in cursor.fetchall()}


def main() -> None:
    load_environment()
    queries = json.loads((DATA / "queries.json").read_text(encoding="utf-8"))["homer"]
    vectors = openai_embeddings(queries)
    report: dict = {"queries": len(queries), "baseline": "retained post-dedup snapshot UUIDs", "mismatches": []}
    with psycopg.connect(os.environ["SUPABASE_DB_URL"], connect_timeout=20, autocommit=True) as conn:
        ids, matrix = snapshot_matrix("homer", database_ids(conn, "homer"))
        baseline = exact_baseline(ids, matrix, vectors)
        retained = set(ids)
        rpc_rows = [rpc_http_rows(vector) for vector in vectors]
        rpc_ids = [[str(row["id"]) for row in rows] for rows in rpc_rows]
        needed = list({ident for rows in baseline + rpc_ids for ident in rows})
        with conn.cursor() as cursor:
            cursor.execute("select id, content from public.rag_homer where id = any(%s::uuid[])", (needed,))
            content = {str(ident): value for ident, value in cursor.fetchall()}
        if len(content) != len(needed):
            raise RuntimeError("Top-3 ID missing from loaded table")
        id_scores: list[float] = []
        content_scores: list[float] = []
        for i, (left_ids, right_ids, vector) in enumerate(zip(baseline, rpc_ids, vectors)):
            left = [normalized_content(content[ident]) for ident in left_ids]
            right = [normalized_content(content[ident]) for ident in right_ids]
            id_score = overlap(left_ids, right_ids)
            content_score = overlap(left, right)
            id_scores.append(id_score)
            content_scores.append(content_score)
            if content_score == 1:
                continue
            left_excess = Counter(left) - Counter(right)
            right_excess = Counter(right) - Counter(left)
            missing = unmatched_ids(left_ids, left, left_excess)
            extra = unmatched_ids(right_ids, right, right_excess)
            if len(missing) != len(extra):
                raise RuntimeError(f"Unequal unmatched content counts at query {i + 1}")
            distances = exact_half_distances(conn, vector, missing + extra)
            missing.sort(key=lambda ident: distances[ident])
            extra.sort(key=lambda ident: distances[ident])
            pairs = []
            for baseline_id, rpc_id in zip(missing, extra):
                pairs.append({
                    "baseline_content": content[baseline_id],
                    "rpc_content": content[rpc_id],
                    "baseline_halfvec_distance": round(distances[baseline_id], 6),
                    "rpc_halfvec_distance": round(distances[rpc_id], 6),
                    "rpc_minus_baseline_distance": round(distances[rpc_id] - distances[baseline_id], 6),
                    "rpc_is_backfill": rpc_id not in retained,
                })
            report["mismatches"].append({"query_number": i + 1, "query": queries[i],
                                         "id_overlap": round(id_score, 4),
                                         "content_overlap": round(content_score, 4), "pairs": pairs})
        report.update({
            "id_overlap": round(fmean(id_scores), 4),
            "content_overlap": round(fmean(content_scores), 4),
            "matching_fallbacks": sum(not left and not right for left, right in zip(baseline, rpc_ids)),
            "queries_with_true_content_misses": len(report["mismatches"]),
            "rpc_backfill_swap_pairs": sum(pair["rpc_is_backfill"] for row in report["mismatches"] for pair in row["pairs"]),
        })
    output = DATA / "phase3_homer_content_check.json"
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print({key: value for key, value in report.items() if key != "mismatches"}, flush=True)
    print({"report_file": output.name}, flush=True)


if __name__ == "__main__":
    main()
