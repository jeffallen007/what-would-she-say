#!/usr/bin/env python3
"""Blind gpt-4o-mini answer check on Homer content misses plus one control."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.error
import urllib.request

import psycopg

from parity_test import DATA, ROOT, database_ids, exact_baseline, load_environment, openai_embeddings, snapshot_matrix
from phase3_homer_content_check import rpc_http_rows

sys.path.insert(0, str(ROOT / "scripts" / "vectorstore-generation"))
from my_prompts import my_prompt_template  # noqa: E402


def chat(messages: list[dict], temperature: float, max_tokens: int) -> str:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is required")
    request = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps({"model": "gpt-4o-mini", "temperature": temperature,
                         "max_tokens": max_tokens, "messages": messages}).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            body = json.loads(response.read())
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"OpenAI chat HTTP {error.code}") from None
    return body["choices"][0]["message"]["content"].strip()


def generate(question: str, context: str) -> str:
    system = my_prompt_template("homer").format(context=context, question=question)
    return chat([{"role": "system", "content": system},
                 {"role": "user", "content": question}], 0.7, 325)


def judge(question: str, context_a: str, answer_a: str, context_b: str, answer_b: str) -> str:
    prompt = (
        "Compare two answers to the same user question. Judge Homer Simpson persona fidelity, "
        "helpfulness, natural tone, and sensible use of each answer's supplied context. "
        "Choose TIE if neither is meaningfully better. Reply with exactly A, B, or TIE.\n\n"
        f"Question: {question}\n\nContext A:\n{context_a}\nAnswer A:\n{answer_a}"
        f"\n\nContext B:\n{context_b}\nAnswer B:\n{answer_b}"
    )
    verdict = chat([{"role": "system", "content": "You are a strict blind evaluator."},
                    {"role": "user", "content": prompt}], 0, 8).upper()
    if verdict not in {"A", "B", "TIE"}:
        raise RuntimeError("Judge returned an invalid verdict")
    return verdict


def main() -> None:
    load_environment()
    previous = json.loads((DATA / "phase3_homer_content_check.json").read_text(encoding="utf-8"))
    mismatch_numbers = [row["query_number"] for row in previous["mismatches"]]
    if len(mismatch_numbers) != 14:
        raise RuntimeError("Expected 14 Homer content-mismatch queries")
    control = next(number for number in range(1, 41) if number not in mismatch_numbers)
    selected = sorted(mismatch_numbers + [control])
    queries = json.loads((DATA / "queries.json").read_text(encoding="utf-8"))["homer"]
    selected_questions = [queries[number - 1] for number in selected]
    vectors = openai_embeddings(selected_questions)
    with psycopg.connect(os.environ["SUPABASE_DB_URL"], connect_timeout=20, autocommit=True) as conn:
        ids, matrix = snapshot_matrix("homer", database_ids(conn, "homer"))
        baseline = exact_baseline(ids, matrix, vectors)
        rpc = [[str(row["id"]) for row in rpc_http_rows(vector)] for vector in vectors]
        needed = list({ident for rows in baseline + rpc for ident in rows})
        with conn.cursor() as cursor:
            cursor.execute("select id, content from public.rag_homer where id = any(%s::uuid[])", (needed,))
            content = {str(ident): value for ident, value in cursor.fetchall()}
        if len(content) != len(needed):
            raise RuntimeError("Answer-check context ID missing from loaded table")
    records: list[dict] = []
    for number, question, left_ids, right_ids in zip(selected, selected_questions, baseline, rpc):
        baseline_context = "\n\n".join(content[ident] for ident in left_ids)
        rpc_context = "\n\n".join(content[ident] for ident in right_ids)
        baseline_answer = generate(question, baseline_context)
        rpc_answer = generate(question, rpc_context)
        rpc_first = int(hashlib.sha256(f"homer:pgvector:{number}".encode()).hexdigest(), 16) % 2 == 0
        if rpc_first:
            raw = judge(question, rpc_context, rpc_answer, baseline_context, baseline_answer)
            verdict = {"A": "rpc_win", "B": "rpc_loss", "TIE": "tie"}[raw]
        else:
            raw = judge(question, baseline_context, baseline_answer, rpc_context, rpc_answer)
            verdict = {"A": "rpc_loss", "B": "rpc_win", "TIE": "tie"}[raw]
        records.append({"query_number": number, "was_content_miss": number in mismatch_numbers,
                        "context_ids_equal": left_ids == right_ids, "verdict": verdict})
        print({"judged": len(records), "total": len(selected)}, flush=True)
    wins = sum(row["verdict"] == "rpc_win" for row in records)
    ties = sum(row["verdict"] == "tie" for row in records)
    losses = sum(row["verdict"] == "rpc_loss" for row in records)
    report = {"model": "gpt-4o-mini", "generation_temperature": 0.7,
              "generation_max_tokens": 325, "judge_temperature": 0,
              "selection": "14 preidentified normalized-content misses plus first matching control",
              "comparison_count": len(records), "rpc_wins": wins, "ties": ties,
              "rpc_losses": losses, "tie_or_better_percent": round(100 * (wins + ties) / len(records), 2),
              "records": records}
    output = DATA / "phase3_homer_answer_check.json"
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print({key: value for key, value in report.items() if key != "records"}, flush=True)
    print({"report_file": output.name}, flush=True)


if __name__ == "__main__":
    main()
