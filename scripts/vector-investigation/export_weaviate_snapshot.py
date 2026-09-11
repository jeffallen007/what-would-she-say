#!/usr/bin/env python3
"""Export a read-only, full-fidelity Weaviate snapshot for Phase 0.

Writes UUIDs, all object properties, and float32 vectors to Parquet. This
script only calls Weaviate read/configuration APIs; it makes no mutations.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
import weaviate
from dotenv import load_dotenv
from weaviate.classes.init import Auth


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "data"
ENV_FILE = REPO_ROOT / "scripts" / "vectorstore-generation" / ".env"
COLLECTIONS = ("Barbie", "Homer", "Jesus")


def connect() -> Any:
    """Connect with environment values, never logging credentials."""
    load_dotenv(ENV_FILE, override=False)
    endpoint = os.getenv("WEAVIATE_REST_ENDPOINT") or os.getenv("WEAVIATE_URL")
    api_key = os.getenv("WEAVIATE_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    missing = [
        name
        for name, value in (("WEAVIATE_REST_ENDPOINT/WEAVIATE_URL", endpoint), ("WEAVIATE_API_KEY", api_key))
        if not value
    ]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

    headers = {"X-OpenAI-Api-Key": openai_key} if openai_key else None
    return weaviate.connect_to_weaviate_cloud(
        cluster_url=endpoint,
        auth_credentials=Auth.api_key(api_key),
        headers=headers,
    )


def vector_values(vector: Any) -> list[float]:
    """Return the default vector, failing safely if a named-vector shape appears."""
    if isinstance(vector, dict):
        if "default" not in vector:
            raise ValueError(f"Expected default vector; received named vectors: {list(vector)}")
        vector = vector["default"]
    if vector is None:
        raise ValueError("Object has no vector; snapshot would be incomplete")
    return [float(value) for value in vector]


def collection_summary(config: Any, count: int, vector_dimensions: int) -> dict[str, Any]:
    return {
        "count": count,
        "vector_dimensions": vector_dimensions,
        "vectorizer": str(config.vectorizer_config),
        "vector_index": str(config.vector_index_config),
        "properties": [
            {
                "name": prop.name,
                "data_type": str(prop.data_type),
                "filterable": prop.index_filterable,
                "searchable": prop.index_searchable,
            }
            for prop in config.properties
        ],
    }


def export_collection(client: Any, name: str, output_dir: Path) -> dict[str, Any]:
    collection = client.collections.get(name)
    config = collection.config.get()
    aggregate_count = collection.aggregate.over_all(total_count=True).total_count

    iterator = collection.iterator(include_vector=True)
    try:
        first = next(iterator)
    except StopIteration:
        raise RuntimeError(f"Collection {name} is empty; no snapshot written")

    first_vector = vector_values(first.vector)
    dimensions = len(first_vector)
    schema = pa.schema(
        [
            pa.field("uuid", pa.string(), nullable=False),
            pa.field("properties_json", pa.string(), nullable=False),
            pa.field("vector", pa.list_(pa.float32(), dimensions), nullable=False),
        ]
    )
    output_path = output_dir / f"{name.lower()}.parquet"
    written = 0

    def row(item: Any, vector: list[float] | None = None) -> dict[str, Any]:
        values = vector if vector is not None else vector_values(item.vector)
        if len(values) != dimensions:
            raise ValueError(f"{name} contains mixed vector dimensions: expected {dimensions}, got {len(values)}")
        return {
            "uuid": str(item.uuid),
            "properties_json": json.dumps(item.properties, ensure_ascii=False, sort_keys=True, default=str),
            "vector": values,
        }

    with pq.ParquetWriter(output_path, schema, compression="zstd") as writer:
        batch: list[dict[str, Any]] = [row(first, first_vector)]
        while True:
            try:
                item = next(iterator)
            except StopIteration:
                break
            batch.append(row(item))
            if len(batch) >= 100:
                writer.write_table(pa.Table.from_pylist(batch, schema=schema))
                written += len(batch)
                batch.clear()
                if written % 10_000 == 0:
                    print(f"{name}: exported {written:,} objects", flush=True)
        if batch:
            writer.write_table(pa.Table.from_pylist(batch, schema=schema))
            written += len(batch)

    if written != aggregate_count:
        raise RuntimeError(
            f"{name}: exported {written:,} objects but aggregate count is {aggregate_count:,}; retaining snapshot for inspection"
        )
    print(f"{name}: verified {written:,} exported objects", flush=True)
    return {
        "collection": name,
        "parquet_file": output_path.name,
        "parquet_sha256": None,
        **collection_summary(config, aggregate_count, dimensions),
        "exported_count": written,
        "count_matches_aggregate": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collection", choices=COLLECTIONS, action="append", help="Export only this collection; repeatable")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    collections = tuple(args.collection) if args.collection else COLLECTIONS
    args.output_dir.mkdir(parents=True, exist_ok=True)

    client = connect()
    try:
        manifest = {
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "read_only": True,
            "collections": [export_collection(client, name, args.output_dir) for name in collections],
        }
    finally:
        client.close()

    manifest_path = args.output_dir / "phase0_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
