#!/usr/bin/env python3
"""Phase 2 reduction candidates from the local, immutable Phase 0 snapshot.

No network APIs are called. Near-duplicate detection is run only on the
reachable corpus because unreachable records are excluded from the migration
target before deduplication. It uses a high-recall HNSW nearest-neighbor scan
and verifies returned cosine scores against the normalized float32 vectors.
"""

from __future__ import annotations

import csv
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import faiss
import numpy as np
import pyarrow.parquet as pq

from weaviate_serialization import serialized_text


DATA_DIR = Path(__file__).resolve().parent / "data"
NORMALIZE_PUNCTUATION = re.compile(r"[^\w\s]")
COLLECTION_RULES = {
    "Barbie": "Barbie Margot",
    "Homer": "Homer Simpson",
    "Jesus": None,
}


def normalized_content(content: str) -> str:
    text = unicodedata.normalize("NFKC", content).lower()
    text = NORMALIZE_PUNCTUATION.sub("", text)
    return " ".join(text.split())


def word_count(content: str) -> int:
    return len(re.findall(r"\b[\w']+\b", content))


def load_collection(name: str) -> tuple[list[dict[str, Any]], np.ndarray]:
    table = pq.read_table(DATA_DIR / f"{name.lower()}.parquet", columns=["properties_json", "vector"])
    properties = [json.loads(value) for value in table.column("properties_json").to_pylist()]
    vector_array = table.column("vector").combine_chunks()
    vectors = vector_array.values.to_numpy(zero_copy_only=False).reshape(len(properties), vector_array.type.list_size)
    return properties, np.asarray(vectors, dtype=np.float32)


def exact_duplicate_stats(properties: list[dict[str, Any]], candidate_indices: list[int]) -> tuple[set[int], list[dict[str, Any]]]:
    groups: dict[tuple[str, str], list[int]] = defaultdict(list)
    for index in candidate_indices:
        props = properties[index]
        groups[(str(props.get("character", "")), normalized_content(str(props.get("content", ""))))].append(index)

    redundant: set[int] = set()
    examples: list[dict[str, Any]] = []
    for (character, content), indexes in groups.items():
        if len(indexes) > 1:
            redundant.update(indexes[1:])
            if len(examples) < 10:
                examples.append(
                    {
                        "character": character,
                        "occurrences": len(indexes),
                        "content": content[:300],
                    }
                )
    return redundant, examples


class UnionFind:
    def __init__(self, values: list[int]) -> None:
        self.parent = {value: value for value in values}

    def find(self, value: int) -> int:
        while self.parent[value] != value:
            self.parent[value] = self.parent[self.parent[value]]
            value = self.parent[value]
        return value

    def union(self, left: int, right: int) -> None:
        left_root, right_root = self.find(left), self.find(right)
        if left_root != right_root:
            self.parent[right_root] = left_root


def near_duplicate_stats(
    properties: list[dict[str, Any]], vectors: np.ndarray, indices: list[int]
) -> tuple[set[int], list[dict[str, Any]], int]:
    if len(indices) < 2:
        return set(), [], 0
    candidate_vectors = np.ascontiguousarray(vectors[indices], dtype=np.float32)
    norms = np.linalg.norm(candidate_vectors, axis=1, keepdims=True)
    candidate_vectors = candidate_vectors / np.maximum(norms, 1e-12)

    # k=8 catches clusters rather than only a record's single nearest neighbor.
    index = faiss.IndexHNSWFlat(candidate_vectors.shape[1], 32, faiss.METRIC_INNER_PRODUCT)
    index.hnsw.efConstruction = 200
    index.hnsw.efSearch = 256
    index.add(candidate_vectors)
    scores, neighbors = index.search(candidate_vectors, min(8, len(indices)))

    union_find = UnionFind(indices)
    qualifying_pairs: list[tuple[int, int, float]] = []
    for local_index, original_index in enumerate(indices):
        for score, neighbor_local_index in zip(scores[local_index], neighbors[local_index]):
            if neighbor_local_index < 0 or neighbor_local_index == local_index or score < 0.98:
                continue
            neighbor_index = indices[int(neighbor_local_index)]
            if original_index < neighbor_index:
                union_find.union(original_index, neighbor_index)
                qualifying_pairs.append((original_index, neighbor_index, float(score)))

    components: dict[int, list[int]] = defaultdict(list)
    for value in indices:
        components[union_find.find(value)].append(value)
    redundant: set[int] = set()
    for members in components.values():
        if len(members) > 1:
            redundant.update(sorted(members)[1:])

    examples = [
        {
            "cosine_similarity": round(score, 6),
            "left_character": str(properties[left].get("character", "")),
            "left_content": str(properties[left].get("content", ""))[:300],
            "right_content": str(properties[right].get("content", ""))[:300],
        }
        for left, right, score in qualifying_pairs[:10]
    ]
    return redundant, examples, len(qualifying_pairs)


def backfill_payload() -> dict[str, Any]:
    with (DATA_DIR / "phase1_missing_bible_verses.csv").open(encoding="utf-8", newline="") as handle:
        missing_verses = list(csv.DictReader(handle))
    with (DATA_DIR / "phase1_homer_missing_source_rows.csv").open(encoding="utf-8", newline="") as handle:
        all_missing_homer = [row for row in csv.DictReader(handle) if row["character"] == "Homer Simpson"]
    missing_homer = [row for row in all_missing_homer if row["dialogue"].strip()]

    payload = {
        "description": "Non-empty records missing from live Weaviate that should be embedded during a Supabase migration load.",
        "jesus": [
            {
                "content": f"{row['verse']}\t{row['content']}",
                "metadata": {"source": "AKJV", "verse": row["verse"], "doc_id": int(row["line_number"]) - 1},
                "embedding_input": serialized_text("Jesus", {
                    "content": f"{row['verse']}\t{row['content']}", "source": "AKJV", "verse": row["verse"],
                    "doc_id": int(row["line_number"]) - 1,
                }),
            }
            for row in missing_verses
        ],
        "homer": [
            {
                "content": row["dialogue"],
                "metadata": {
                    "source": "source-files/simpsons_dataset.csv",
                    "character": "Homer Simpson",
                    "row": int(row["row"]),
                    "doc_id": int(row["row"]) + 1,
                },
                "embedding_input": serialized_text("Homer", {
                    "content": row["dialogue"], "character": "Homer Simpson",
                    "source": "source-files/simpsons_dataset.csv", "row": int(row["row"]),
                    "doc_id": int(row["row"]) + 1,
                }),
            }
            for row in missing_homer
        ],
    }
    output = DATA_DIR / "phase2_migration_backfill.json"
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {
        "file": output.name,
        "jesus_missing_verses": len(payload["jesus"]),
        "homer_simpson_source_rows_missing": len(all_missing_homer),
        "homer_simpson_nonempty_lines_to_embed": len(payload["homer"]),
        "homer_simpson_empty_lines_omitted": len(all_missing_homer) - len(payload["homer"]),
        "homer_source_rows": [record["metadata"]["row"] for record in payload["homer"]],
    }


def analyze_collection(name: str) -> dict[str, Any]:
    properties, vectors = load_collection(name)
    total = len(properties)
    target_character = COLLECTION_RULES[name]
    reachable = list(range(total)) if target_character is None else [
        index for index, props in enumerate(properties) if props.get("character") == target_character
    ]
    unreachable = set(range(total)) - set(reachable)
    exact_redundant, exact_examples = exact_duplicate_stats(properties, reachable)
    near_redundant, near_examples, near_pair_count = near_duplicate_stats(properties, vectors, reachable)
    short_reachable = [index for index in reachable if word_count(str(properties[index].get("content", ""))) < 4]

    combined = set(unreachable) | exact_redundant | near_redundant
    return {
        "total_objects": total,
        "reachable_objects": len(reachable),
        "reachable_percent": round(100 * len(reachable) / total, 2),
        "unreachable_objects": len(unreachable),
        "unreachable_percent": round(100 * len(unreachable) / total, 2),
        "exact_duplicate_redundant_objects_within_reachable": len(exact_redundant),
        "exact_duplicate_percent_of_collection": round(100 * len(exact_redundant) / total, 2),
        "exact_duplicate_examples": exact_examples,
        "near_duplicate_redundant_objects_within_reachable": len(near_redundant),
        "near_duplicate_percent_of_collection": round(100 * len(near_redundant) / total, 2),
        "near_duplicate_qualifying_pairs": near_pair_count,
        "near_duplicate_examples": near_examples,
        "under_4_words_reachable": len(short_reachable),
        "under_4_words_reachable_percent": round(100 * len(short_reachable) / len(reachable), 2) if reachable else 0,
        "combined_removable_objects": len(combined),
        "combined_removable_percent": round(100 * len(combined) / total, 2),
        "recommended_phase3_corpus_count": total - len(combined),
    }


def main() -> None:
    faiss.omp_set_num_threads(4)
    result = {name: analyze_collection(name) for name in COLLECTION_RULES}
    result["migration_backfill"] = backfill_payload()
    output = DATA_DIR / "phase2_reduction_candidates.json"
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {output}")
    for name, values in result.items():
        if name != "migration_backfill":
            print(f"{name}: {values['recommended_phase3_corpus_count']:,} Phase 3 candidate records")


if __name__ == "__main__":
    main()
