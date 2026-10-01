#!/usr/bin/env python3
"""Repeated blind answer check on Homer content misses and five controls."""

from __future__ import annotations

import json
import os
import secrets
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import psycopg

from parity_test import DATA, ROOT, database_ids, exact_baseline, load_environment, openai_embeddings, snapshot_matrix
from phase3_homer_content_check import normalized_content, rpc_http_rows

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
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                body = json.loads(response.read())
            break
        except urllib.error.HTTPError as error:
            if error.code not in {429, 500, 502, 503, 504} or attempt == 3:
                raise RuntimeError(f"OpenAI chat HTTP {error.code}") from None
            time.sleep(2 ** attempt)
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
    queries = json.loads((DATA / "queries.json").read_text(encoding="utf-8"))["homer"]
    vectors = openai_embeddings(queries)
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
    mismatch_numbers = [i + 1 for i, (left, right) in enumerate(zip(baseline, rpc))
                        if Counter(normalized_content(content[ident]) for ident in left)
                        != Counter(normalized_content(content[ident]) for ident in right)]
    control_numbers = [i for i in range(1, 41) if i not in mismatch_numbers][:5]
    if len(control_numbers) != 5:
        raise RuntimeError("Could not select five matching-context controls")
    selected = sorted(mismatch_numbers + control_numbers)
    print({"mismatch_queries": len(mismatch_numbers), "control_queries": len(control_numbers),
           "judged_pairs_planned": 3 * len(selected)}, flush=True)

    output = DATA / "phase3_homer_answer_check_repeated.json"
    protocol = "three_independent_generations_per_condition_five_controls"
    if output.exists():
        report = json.loads(output.read_text(encoding="utf-8"))
        if report.get("protocol") != protocol or report.get("selected_query_numbers") != selected:
            raise RuntimeError("Existing repeated-check report has a different protocol or query selection")
        records: list[dict] = report["records"]
    else:
        report = {"protocol": protocol, "model": "gpt-4o-mini",
                  "generation_temperature": 0.7, "generation_max_tokens": 325,
                  "judge_temperature": 0, "selected_query_numbers": selected,
                  "mismatch_query_numbers": mismatch_numbers, "control_query_numbers": control_numbers,
                  "records": [], "complete": False}
        records = report["records"]
    completed = {row["query_number"] for row in records}
    if any(sum(row["query_number"] == number for row in records) != 3 for number in completed):
        raise RuntimeError("Repeated-check report has an incomplete query checkpoint")

    for number in selected:
        if number in completed:
            continue
        question = queries[number - 1]
        left_ids = baseline[number - 1]
        right_ids = rpc[number - 1]
        baseline_context = "\n\n".join(content[ident] for ident in left_ids)
        rpc_context = "\n\n".join(content[ident] for ident in right_ids)
        if number in control_numbers:
            # Controls isolate generation and judging variance: both sides get
            # byte-for-byte identical context, even if the RPC order differs.
            rpc_context = baseline_context
        with ThreadPoolExecutor(max_workers=3) as pool:
            baseline_futures = [pool.submit(generate, question, baseline_context) for _ in range(3)]
            rpc_futures = [pool.submit(generate, question, rpc_context) for _ in range(3)]
            baseline_answers = [future.result() for future in baseline_futures]
            rpc_answers = [future.result() for future in rpc_futures]
        order = [True, False, bool(secrets.randbits(1))]
        secrets.SystemRandom().shuffle(order)
        group = "mismatch" if number in mismatch_numbers else "control"
        query_records = []
        for replicate in range(3):
            rpc_first = order[replicate]
            if rpc_first:
                raw = judge(question, rpc_context, rpc_answers[replicate],
                            baseline_context, baseline_answers[replicate])
                verdict = {"A": "rpc_win", "B": "rpc_loss", "TIE": "tie"}[raw]
            else:
                raw = judge(question, baseline_context, baseline_answers[replicate],
                            rpc_context, rpc_answers[replicate])
                verdict = {"A": "rpc_loss", "B": "rpc_win", "TIE": "tie"}[raw]
            query_records.append({"query_number": number, "group": group,
                                  "replicate": replicate + 1, "rpc_first": rpc_first,
                                  "context_text_equal": baseline_context == rpc_context,
                                  "verdict": verdict})
        records.extend(query_records)
        report["records"] = records
        temporary = output.with_suffix(".tmp")
        temporary.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        temporary.replace(output)
        print({"completed_queries": len({row["query_number"] for row in records}),
               "total_queries": len(selected), "judged_pairs": len(records)}, flush=True)

    summary = {}
    for group in ("control", "mismatch"):
        subset = [row for row in records if row["group"] == group]
        wins = sum(row["verdict"] == "rpc_win" for row in subset)
        ties = sum(row["verdict"] == "tie" for row in subset)
        losses = sum(row["verdict"] == "rpc_loss" for row in subset)
        summary[group] = {"queries": len({row["query_number"] for row in subset}),
                          "pairs": len(subset), "pseudo_rpc_wins" if group == "control" else "rpc_wins": wins,
                          "ties": ties, "pseudo_rpc_losses" if group == "control" else "rpc_losses": losses,
                          "tie_rate_percent": round(100 * ties / len(subset), 2),
                          "loss_rate_percent": round(100 * losses / len(subset), 2)}
    report["summary"] = summary
    report["complete"] = True
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print({"summary": summary}, flush=True)
    print({"report_file": output.name}, flush=True)


if __name__ == "__main__":
    main()
