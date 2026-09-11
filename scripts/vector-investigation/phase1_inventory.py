#!/usr/bin/env python3
"""Phase 1 inventory for the immutable local Phase 0 snapshot.

No network APIs are called. The script compares the snapshot with the checked-in
source files and writes derived, ignored reports to the snapshot data directory.
"""

from __future__ import annotations

import csv
import json
import re
import statistics
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

import pyarrow.parquet as pq
from pypdf import PdfReader


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(__file__).resolve().parent / "data"
SOURCE_DIR = REPO_ROOT / "scripts" / "vectorstore-generation" / "source-files"
WORD_RE = re.compile(r"\b[\w']+\b")


def snapshot_properties(collection: str) -> list[dict[str, Any]]:
    path = DATA_DIR / f"{collection.lower()}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"Missing Phase 0 snapshot: {path}")
    values = pq.ParquetFile(path).read(columns=["properties_json"]).column("properties_json").to_pylist()
    return [json.loads(value) for value in values]


def percentile(values: list[int], fraction: float) -> float:
    if not values:
        return 0.0
    position = (len(values) - 1) * fraction
    lower, upper = int(position), min(int(position) + 1, len(values) - 1)
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


def length_distribution(properties: Iterable[dict[str, Any]]) -> dict[str, float | int]:
    words = sorted(len(WORD_RE.findall(str(props.get("content", "")))) for props in properties)
    return {
        "count": len(words),
        "mean_words": round(statistics.fmean(words), 2) if words else 0,
        "min_words": words[0] if words else 0,
        "p25_words": round(percentile(words, 0.25), 2),
        "median_words": round(percentile(words, 0.50), 2),
        "p75_words": round(percentile(words, 0.75), 2),
        "p95_words": round(percentile(words, 0.95), 2),
        "max_words": words[-1] if words else 0,
        "under_4_words": sum(word_count < 4 for word_count in words),
    }


def read_homer_source() -> tuple[list[dict[str, str]], Counter[str]]:
    with (SOURCE_DIR / "simpsons_dataset.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return rows, Counter(row["character"] for row in rows)


def compare_homer(live: list[dict[str, Any]], output_dir: Path) -> dict[str, Any]:
    source_rows, source_counts = read_homer_source()
    live_counts = Counter(str(row.get("character", "")) for row in live)
    expected_row_ids = set(range(len(source_rows)))
    live_row_ids = {int(float(row["row"])) for row in live if row.get("row") is not None}
    missing_rows = sorted(expected_row_ids - live_row_ids)

    characters = sorted(set(source_counts) | set(live_counts), key=lambda item: (-source_counts[item], item))
    distribution_path = output_dir / "phase1_homer_character_distribution.csv"
    with distribution_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["character", "source_rows", "live_objects", "difference", "live_percent_of_source"])
        writer.writeheader()
        for character in characters:
            source_count, live_count = source_counts[character], live_counts[character]
            writer.writerow(
                {
                    "character": character,
                    "source_rows": source_count,
                    "live_objects": live_count,
                    "difference": live_count - source_count,
                    "live_percent_of_source": round(100 * live_count / source_count, 2) if source_count else None,
                }
            )

    missing_rows_path = output_dir / "phase1_homer_missing_source_rows.csv"
    with missing_rows_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["row", "character", "dialogue"])
        writer.writeheader()
        for row_id in missing_rows:
            writer.writerow({"row": row_id, **source_rows[row_id]})

    return {
        "source_rows": len(source_rows),
        "live_objects": len(live),
        "difference": len(live) - len(source_rows),
        "source_character_values": len(source_counts),
        "live_character_values": len(live_counts),
        "homer_simpson_source_rows": source_counts["Homer Simpson"],
        "homer_simpson_live_objects": live_counts["Homer Simpson"],
        "homer_simpson_difference": live_counts["Homer Simpson"] - source_counts["Homer Simpson"],
        "missing_source_row_count": len(missing_rows),
        "missing_source_rows_file": missing_rows_path.name,
        "character_distribution_file": distribution_path.name,
        "top_source_characters": [
            {"character": character, "source_rows": source_counts[character], "live_objects": live_counts[character]}
            for character in characters[:20]
        ],
    }


def write_character_distribution(name: str, properties: list[dict[str, Any]], output_dir: Path) -> dict[str, int]:
    counts = Counter(str(row.get("character", "")) for row in properties)
    path = output_dir / f"phase1_{name.lower()}_character_distribution.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["character", "live_objects"])
        writer.writeheader()
        for character, count in sorted(counts.items(), key=lambda entry: (-entry[1], entry[0])):
            writer.writerow({"character": character, "live_objects": count})
    return dict(counts)


def compare_jesus(live: list[dict[str, Any]], output_dir: Path) -> dict[str, Any]:
    with (SOURCE_DIR / "bible.txt").open(encoding="utf-8") as handle:
        nonempty_lines = [(line_number, line.strip()) for line_number, line in enumerate(handle, start=1) if line.strip()]
    source_label = nonempty_lines[0][1]
    source_verses = nonempty_lines[1:]
    live_content = Counter(str(row.get("content", "")) for row in live)
    observed = Counter()
    missing: list[dict[str, Any]] = []
    for line_number, verse_text in source_verses:
        observed[verse_text] += 1
        if observed[verse_text] > live_content[verse_text]:
            verse_ref, _, verse_body = verse_text.partition("\t")
            missing.append({"line_number": line_number, "verse": verse_ref, "content": verse_body})

    missing_path = output_dir / "phase1_missing_bible_verses.csv"
    with missing_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["line_number", "verse", "content"])
        writer.writeheader()
        writer.writerows(missing)

    return {
        "source_label": source_label,
        "source_verse_lines": len(source_verses),
        "live_objects": len(live),
        "difference": len(live) - len(source_verses),
        "missing_verse_count": len(missing),
        "missing_verses_file": missing_path.name,
        "missing_verse_references": [entry["verse"] for entry in missing],
    }


def count_barbie_source_documents() -> int:
    """Reproduce the counting behavior of generate_docs_from_pdf without embeddings."""
    scene_heading = re.compile(r"^(INT\.|EXT\.|EST\.)(.*)", re.IGNORECASE)
    character_voice = re.compile(r"^([A-Z][A-Z0-9 \-\.]+?)(?:\s*\((V\.O\.|O\.S\.)\))?$")
    document_count = 0
    current_character: str | None = None
    dialogue_buffer: list[str] = []
    action_buffer: list[str] = []

    def flush_dialogue() -> None:
        nonlocal current_character, document_count
        if current_character and dialogue_buffer and " ".join(dialogue_buffer).strip():
            document_count += 1
        dialogue_buffer.clear()
        current_character = None

    def flush_action() -> None:
        nonlocal document_count
        if action_buffer and " ".join(action_buffer).strip():
            document_count += 1
        action_buffer.clear()

    reader = PdfReader(SOURCE_DIR / "barbie_final_shooting_script.pdf")
    for page in reader.pages:
        for raw_line in (page.extract_text() or "").split("\n"):
            line = raw_line.strip()
            if not line:
                continue
            if scene_heading.match(line):
                flush_dialogue()
                flush_action()
                document_count += 1
            elif (match := character_voice.match(line)):
                flush_dialogue()
                flush_action()
                current_character = match.group(1).title()
            elif current_character:
                dialogue_buffer.append(line)
            else:
                flush_dialogue()
                action_buffer.append(line)
        flush_dialogue()
        flush_action()
    return document_count


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    collections = {name: snapshot_properties(name) for name in ("Barbie", "Homer", "Jesus")}
    barbie_source_documents = count_barbie_source_documents()
    summary = {
        "snapshot_counts": {name: len(properties) for name, properties in collections.items()},
        "word_length_distribution": {name: length_distribution(properties) for name, properties in collections.items()},
        "character_counts": {
            "Barbie": write_character_distribution("Barbie", collections["Barbie"], DATA_DIR),
            "Homer": dict(sorted(Counter(str(row.get("character", "")) for row in collections["Homer"]).items())),
        },
        "homer_source_comparison": compare_homer(collections["Homer"], DATA_DIR),
        "jesus_source_comparison": compare_jesus(collections["Jesus"], DATA_DIR),
        "barbie_source_comparison": {
            "source_documents_reparsed": barbie_source_documents,
            "live_objects": len(collections["Barbie"]),
            "difference": len(collections["Barbie"]) - barbie_source_documents,
        },
        "570870_investigation": {
            "documented_figure": 570870,
            "live_total": sum(len(properties) for properties in collections.values()),
            "ratio": 570870 / sum(len(properties) for properties in collections.values()),
            "repo_source": "docs/migration_questions.md, added in commit 57db872a",
            "conclusion": "The repository contains no query, export, or calculation that produces 570,870. It is exactly three times the verified live total and is treated as a stale/manual documentation error, not a live object count.",
        },
    }
    path = DATA_DIR / "phase1_inventory.json"
    path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {path}")
    print(json.dumps(summary["snapshot_counts"], indent=2))


if __name__ == "__main__":
    main()
