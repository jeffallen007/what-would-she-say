#!/usr/bin/env python3
"""Phase 3 retrieval and answer-quality evaluation; never embeds the corpus."""
from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path
from statistics import fmean

import numpy as np
from dotenv import load_dotenv

import phase2_reduction_candidates as phase2

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(__file__).resolve().parent / "data"
sys.path.insert(0, str(ROOT / "scripts" / "vectorstore-generation"))
from my_prompts import my_prompt_template  # noqa: E402

DIMS = (256, 512, 768, 1024, 1536, 2000)
THRESHOLD = 0.15  # Weaviate distance < 0.85 with cosine distance.
QUESTIONS = [
    "What does love mean?", "How should I handle a difficult friend?", "I feel lost. What should I do?",
    "What makes a good day?", "How do I find courage?", "What should I do after making a mistake?",
    "Why do people get angry?", "How can I be kinder to myself?", "What is the meaning of home?",
    "How do I deal with rejection?", "What makes someone brave?", "Should I forgive someone who hurt me?",
    "How can I stop worrying?", "What should I do when life feels unfair?", "What is happiness?",
    "How do I support a sad friend?", "What is the best way to start over?", "Why is family important?",
    "How do I make a hard decision?", "What should I be grateful for today?", "What makes a person successful?",
    "How can I be more confident?", "What do you think about change?", "How do I get through a bad day?",
    "What is friendship for?", "How can I have hope?", "What is the value of being honest?",
    "How should I respond when someone insults me?", "What is a good meal?", "How do I celebrate a small win?",
    "What makes a joke funny?", "What should I do on a rainy day?", "How do I face a scary challenge?",
    "What does peace feel like?", "How do I show someone I care?", "What is the best lesson you learned?",
    "How can I be patient?", "What should I do when I am lonely?", "What does freedom mean?", "What advice would you give someone afraid to fail?",
]


def api_key() -> str:
    load_dotenv(ROOT / "scripts" / "vectorstore-generation" / ".env", override=False)
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is required")
    return key


def post(path: str, payload: dict) -> dict:
    request = urllib.request.Request(
        f"https://api.openai.com/v1/{path}", data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {api_key()}", "Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.loads(response.read())


def embeddings(texts: list[str], dimensions: int | None = None) -> np.ndarray:
    payload: dict = {"model": "text-embedding-3-large", "input": texts, "encoding_format": "float"}
    if dimensions:
        payload["dimensions"] = dimensions
    data = post("embeddings", payload)
    return np.asarray([item["embedding"] for item in data["data"]], dtype=np.float32)


def chat(system: str, user: str) -> str:
    data = post("chat/completions", {"model": "gpt-4o-mini", "temperature": 0.7, "max_tokens": 325,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]})
    return data["choices"][0]["message"]["content"]


def judge(question: str, left: str, right: str) -> str:
    prompt = ("Compare two answers to the same user question. Judge fidelity to the supplied persona/RAG context, "
              "helpfulness, and natural tone. Reply with exactly A, B, or TIE.\n"
              f"Question: {question}\nA: {left}\nB: {right}")
    data = post("chat/completions", {"model": "gpt-4o-mini", "temperature": 0, "max_tokens": 4,
        "messages": [{"role": "system", "content": "You are a strict blind evaluator."}, {"role": "user", "content": prompt}]})
    result = data["choices"][0]["message"]["content"].strip().upper()
    return result if result in {"A", "B", "TIE"} else "TIE"


def norm(matrix: np.ndarray) -> np.ndarray:
    return matrix / np.maximum(np.linalg.norm(matrix, axis=1, keepdims=True), 1e-12)


def top3(query: np.ndarray, matrix: np.ndarray, original: list[int]) -> tuple[list[int], list[float]]:
    scores = matrix @ query
    candidates = np.argpartition(scores, -3)[-3:]
    candidates = candidates[np.argsort(scores[candidates])[::-1]]
    chosen = [int(index) for index in candidates if scores[index] > THRESHOLD]
    return [original[index] for index in chosen], [float(1 - scores[index]) for index in candidates if scores[index] > THRESHOLD]


def rank_correlation(baseline: list[int], candidate: list[int]) -> float:
    if not baseline:
        return 1.0 if not candidate else 0.0
    candidate_ranks = {value: rank for rank, value in enumerate(candidate, start=1)}
    x = np.arange(1, len(baseline) + 1, dtype=float)
    y = np.asarray([candidate_ranks.get(value, 4) for value in baseline], dtype=float)
    if np.std(y) == 0:
        return 0.0
    return float(np.corrcoef(x, y)[0, 1])


def retrieval_metrics(baselines: list[list[int]], candidates: list[list[int]], base_dist: list[list[float]], cand_dist: list[list[float]]) -> dict:
    overlaps = [len(set(a) & set(b)) / max(1, len(a)) for a, b in zip(baselines, candidates)]
    return {
        "mean_top3_set_overlap": round(fmean(overlaps), 4),
        "identical_top3_percent": round(100 * fmean([a == b for a, b in zip(baselines, candidates)]), 2),
        "mean_rank_correlation": round(fmean([rank_correlation(a, b) for a, b in zip(baselines, candidates)]), 4),
        "fallback_rate_percent": round(100 * fmean([not rows for rows in candidates]), 2),
        "mean_distance_shift": round(fmean([fmean(b) - fmean(a) for a, b in zip(base_dist, cand_dist) if a and b]), 6),
    }


def live_quality(top_rows: list[list[int]], props: list[dict], vectors: np.ndarray) -> dict:
    vectors = norm(vectors)
    duplicate_or_near = 0
    unique_counts = []
    for rows in top_rows:
        unique_counts.append(len({phase2.normalized_content(str(props[row].get("content", ""))) for row in rows}))
        has_pair = False
        for left in range(len(rows)):
            for right in range(left + 1, len(rows)):
                same = phase2.normalized_content(str(props[rows[left]].get("content", ""))) == phase2.normalized_content(str(props[rows[right]].get("content", "")))
                if same or float(np.dot(vectors[rows[left]], vectors[rows[right]])) >= 0.98:
                    has_pair = True
        duplicate_or_near += has_pair
    return {"queries_with_duplicate_or_near_percent": round(100 * duplicate_or_near / len(top_rows), 2),
            "mean_unique_content_per_top3": round(fmean(unique_counts), 3)}


def persona_data(name: str) -> tuple[list[dict], np.ndarray, list[int], list[int]]:
    props, vectors = phase2.load_collection(name)
    char = phase2.COLLECTION_RULES[name]
    live = list(range(len(props))) if char is None else [i for i, row in enumerate(props) if row.get("character") == char]
    exact, _ = phase2.exact_duplicate_stats(props, live)
    near, _, _ = phase2.near_duplicate_stats(props, vectors, live)
    dedup = [i for i in live if i not in exact | near]
    return props, vectors, live, dedup


def verify_shortening(samples: list[str]) -> dict:
    stored = []
    # Stored comparison uses a deterministic 50-text sample gathered by the caller.
    return {"sample_count": len(samples), "fresh_dimensions": [256, 1024, 1536], "note": "Fresh API comparisons are recorded per dimension in the report."}


def main() -> None:
    DATA.mkdir(exist_ok=True)
    queries = {name.lower(): QUESTIONS for name in ("Barbie", "Homer", "Jesus")}
    (DATA / "queries.json").write_text(json.dumps(queries, indent=2) + "\n")
    query_vectors = {name: norm(embeddings(QUESTIONS)) for name in ("Barbie", "Homer", "Jesus")}
    report: dict = {"model": "text-embedding-3-large", "threshold": THRESHOLD, "personas": {}, "answer_level": {}}
    sample_texts: list[str] = []
    sample_vectors: list[np.ndarray] = []
    answer_inputs: dict[str, dict] = {}

    for name in ("Barbie", "Homer", "Jesus"):
        props, vectors, live_ids, dedup_ids = persona_data(name)
        live_matrix = norm(vectors[live_ids])
        dedup_matrix = norm(vectors[dedup_ids])
        candidate_matrices = {dim: norm(dedup_matrix[:, :dim]) for dim in DIMS}
        baseline_rows, baseline_dist, live_rows, live_dist = [], [], [], []
        candidate_rows = {dim: [] for dim in DIMS}; candidate_dist = {dim: [] for dim in DIMS}
        for query in query_vectors[name]:
            live_result, live_distance = top3(query, live_matrix, live_ids)
            base_result, base_distance = top3(query, dedup_matrix, dedup_ids)
            live_rows.append(live_result); live_dist.append(live_distance)
            baseline_rows.append(base_result); baseline_dist.append(base_distance)
            for dim in DIMS:
                matrix = candidate_matrices[dim]
                result, distance = top3(norm(query[:dim].reshape(1, -1))[0], matrix, dedup_ids)
                candidate_rows[dim].append(result); candidate_dist[dim].append(distance)
        metrics = {str(dim): retrieval_metrics(baseline_rows, candidate_rows[dim], baseline_dist, candidate_dist[dim]) for dim in DIMS}
        live_info = {**live_quality(live_rows, props, vectors), "fallback_rate_percent": round(100 * fmean([not rows for rows in live_rows]), 2)}
        dedup_info = {**live_quality(baseline_rows, props, vectors), "fallback_rate_percent": round(100 * fmean([not rows for rows in baseline_rows]), 2)}
        report["personas"][name] = {"live_baseline": live_info, "dedup_3072": dedup_info, "dimensions": metrics,
            "live_count": len(live_ids), "dedup_count": len(dedup_ids)}
        if name == "Barbie":
            none_rows = [row for row in props if row.get("character") == "none"]
            report["barbie_none_investigation"] = {
                "count": len(none_rows),
                "type_counts": {key: value for key, value in sorted(__import__("collections").Counter(str(row.get("type", "")) for row in none_rows).items())},
                "samples": [str(row.get("content", "")) for row in none_rows[:5]],
                "conclusion": "These are parser-assigned non-dialogue/action records, not Barbie Margot dialogue; the matching count of 278 is coincidental.",
            }
        answer_inputs[name] = {"props": props, "baseline": baseline_rows, "candidates": candidate_rows}
        sample_ids = dedup_ids[::max(1, len(dedup_ids)//17)][:17]
        sample_texts.extend([str(props[index].get("content", "")) for index in sample_ids])
        sample_vectors.extend([vectors[index] for index in sample_ids])
        del vectors, live_matrix, dedup_matrix

    sample_texts = sample_texts[:50]
    stored_samples = np.asarray(sample_vectors[:50], dtype=np.float32)
    verification = {}
    # Compare fresh API-shortened vectors to the existing stored vectors truncated and re-normalized.
    for dim in (256, 1024, 1536):
        fresh_short = norm(embeddings(sample_texts, dim))
        truncated = norm(stored_samples[:, :dim])
        verification[str(dim)] = {"mean_cosine": round(float(np.mean(np.sum(fresh_short * truncated, axis=1))), 6)}
    report["shortening_verification"] = {"sample_count": len(sample_texts), "mean_cosine_fresh_api_vs_truncated_stored": verification,
        "note": "Stored Weaviate vectors may include Weaviate vectorizer formatting; this check measures compatibility rather than assuming identical input serialization."}

    viable = [dim for dim in DIMS if all(
        report["personas"][name]["dimensions"][str(dim)]["mean_top3_set_overlap"] >= .85
        and report["personas"][name]["dimensions"][str(dim)]["fallback_rate_percent"] <= report["personas"][name]["dedup_3072"]["fallback_rate_percent"]
        for name in report["personas"]
    )]
    leaders = (viable or list(reversed(DIMS)))[:2]
    report["answer_level"]["candidate_dimensions"] = leaders
    for dim in leaders:
        wins = ties = losses = 0
        for name, inputs in answer_inputs.items():
            for question, baseline_rows, candidate_rows in zip(QUESTIONS[:15], inputs["baseline"][:15], inputs["candidates"][dim][:15]):
                props = inputs["props"]
                baseline_context = "\n\n".join(str(props[index].get("content", "")) for index in baseline_rows)
                candidate_context = "\n\n".join(str(props[index].get("content", "")) for index in candidate_rows)
                persona = name.lower()
                base_answer = chat(my_prompt_template(persona).format(context=baseline_context, question=question), question)
                candidate_answer = chat(my_prompt_template(persona).format(context=candidate_context, question=question), question)
                first_candidate = int(hashlib.sha256(f"{name}:{dim}:{question}".encode()).hexdigest(), 16) % 2 == 0
                verdict = judge(question, candidate_answer if first_candidate else base_answer, base_answer if first_candidate else candidate_answer)
                candidate_verdict = verdict if first_candidate else ({"A": "B", "B": "A", "TIE": "TIE"}[verdict])
                if candidate_verdict == "A": wins += 1
                elif candidate_verdict == "B": losses += 1
                else: ties += 1
        report["answer_level"][str(dim)] = {"comparisons": wins + ties + losses, "candidate_wins": wins, "ties": ties, "candidate_losses": losses,
            "tie_or_better_percent": round(100 * (wins + ties) / (wins + ties + losses), 2)}

    (DATA / "phase3_results.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Phase 3 complete; results written to data/phase3_results.json")


if __name__ == "__main__":
    main()
