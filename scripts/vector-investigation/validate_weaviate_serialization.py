#!/usr/bin/env python3
"""Read-only proof that the reconstructed text2vec-openai inputs reproduce live vectors.

Reads collection configuration and the immutable Phase 0 snapshot. It requests
only 60 fresh OpenAI embeddings (20 deterministic objects per collection),
never sends data to Weaviate, and records hashes/metrics rather than vectors or
full object text.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow.parquet as pq
from dotenv import load_dotenv

from export_weaviate_snapshot import connect
from weaviate_serialization import serialization_description, serialized_text


ROOT = Path(__file__).resolve().parents[2]
DATA = Path(__file__).resolve().parent / "data"
COLLECTIONS = ("Barbie", "Homer", "Jesus")
SAMPLE_SIZE = 20


def openai_key() -> str:
    load_dotenv(ROOT / "scripts" / "vectorstore-generation" / ".env", override=False)
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is required")
    return key


def embed(texts: list[str]) -> np.ndarray:
    request = urllib.request.Request(
        "https://api.openai.com/v1/embeddings",
        data=json.dumps({"model": "text-embedding-3-large", "input": texts, "encoding_format": "float"}).encode(),
        headers={"Authorization": f"Bearer {openai_key()}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        data = json.loads(response.read())
    return np.asarray([item["embedding"] for item in data["data"]], dtype=np.float32)


def cosine(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    left = left / np.maximum(np.linalg.norm(left, axis=1, keepdims=True), 1e-12)
    right = right / np.maximum(np.linalg.norm(right, axis=1, keepdims=True), 1e-12)
    return np.sum(left * right, axis=1)


def config_summary(config: Any) -> dict[str, Any]:
    return {
        "vectorizer": str(config.vectorizer_config.vectorizer),
        "model": config.vectorizer_config.model,
        "vectorize_collection_name": config.vectorizer_config.vectorize_collection_name,
        "properties": [
            {
                "name": prop.name,
                "data_type": str(prop.data_type),
                "skip": prop.vectorizer_config.skip,
                "vectorize_property_name": prop.vectorizer_config.vectorize_property_name,
            }
            for prop in config.properties
        ],
    }


def sample_from_snapshot(name: str) -> tuple[list[dict[str, Any]], np.ndarray, list[str]]:
    table = pq.read_table(DATA / f"{name.lower()}.parquet", columns=["uuid", "properties_json", "vector"])
    rows = table.slice(0, SAMPLE_SIZE)
    properties = [json.loads(item) for item in rows.column("properties_json").to_pylist()]
    vector_array = rows.column("vector").combine_chunks()
    stored = vector_array.values.to_numpy(zero_copy_only=False).reshape(SAMPLE_SIZE, vector_array.type.list_size)
    uuids = rows.column("uuid").to_pylist()
    return properties, np.asarray(stored, dtype=np.float32), uuids


def main() -> None:
    DATA.mkdir(exist_ok=True)
    report: dict[str, Any] = {
        "model": "text-embedding-3-large",
        "sample_size_per_collection": SAMPLE_SIZE,
        "serialization_function": serialization_description(),
        "collections": {},
    }
    client = connect()
    try:
        for name in COLLECTIONS:
            config = client.collections.get(name).config.get()  # configuration read only
            props, stored, uuids = sample_from_snapshot(name)
            inputs = [serialized_text(name, item) for item in props]
            fresh = embed(inputs)
            scores = cosine(fresh, stored)
            report["collections"][name] = {
                "live_module_config": config_summary(config),
                "sample_uuid_sha256": [hashlib.sha256(value.encode()).hexdigest() for value in uuids],
                "input_sha256": [hashlib.sha256(value.encode()).hexdigest() for value in inputs],
                "cosine": {
                    "minimum": round(float(scores.min()), 8),
                    "mean": round(float(scores.mean()), 8),
                    "all_at_least_0_999": bool(np.all(scores >= 0.999)),
                },
            }
    finally:
        client.close()
    (DATA / "serialization_validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("Serialization validation complete; metrics written to data/serialization_validation.json")
    for name, result in report["collections"].items():
        print(f"{name}: min cosine {result['cosine']['minimum']:.8f}; mean {result['cosine']['mean']:.8f}; >= 0.999: {result['cosine']['all_at_least_0_999']}")


if __name__ == "__main__":
    main()
