# Vector Reduction Investigation: Conversation History

This is a repository record of the user’s investigation instructions and the corresponding summaries reported in this conversation. Prompts are preserved substantively, with only whitespace normalized; summaries are condensed where the original response was a progress report rather than a final result.

## Initial investigation request

**User prompt**

> I have a follow up task on your investigation for the 'migration' from weaviate to supabase. Read `docs/vector_reduction_investigation.md` and `weaviate_to_supabase_assessment.md`, then execute the investigation exactly as specified. Stay read-only on Weaviate, make no app/Supabase changes, and stop for my approval before any full-corpus re-embedding. Start with Phase 0 and report the live schema + per-collection counts before continuing to Phase 1.
>
> Final output: `vector_reduction_findings.md` plus reproducible scripts in `scripts/vector-investigation/`.

**Reported summary**

> Phase 0 completed read-only. Live collections were Barbie 1,274, Homer 158,014, and Jesus 31,002 (190,290 total). All used `text2vec-openai` with `text-embedding-3-large`, 3,072 dimensions, cosine HNSW, and the full snapshot was exported locally to ignored Parquet files. No application, Supabase, or Weaviate writes were made.

## Phase 1 authorization and additions

**User prompt**

> Proceed to Phase 1. Also include: (1) where the 570,870 figure came from (it's exactly 3× the live count), (2) Homer character distribution vs. the full Kaggle `simpsons_dataset.csv` row count, (3) which Bible verses from `source-files/bible.txt` are missing from the Jesus collection. Stop after Phase 1 and report.

**Reported summary**

> Phase 1 found that 570,870 was a stale manual documentation value: exactly 3 × the verified 190,290 live objects, with no reproducible query or calculation behind it. The Homer source has 158,314 rows versus 158,014 live objects (300 absent rows); Homer Simpson has 29,782 source rows versus 29,735 live rows (47 missing). The Bible source has 31,102 verses versus 31,002 live Jesus objects; the 100 omissions are Psalm 116:2–119:1 and Matthew 26:46–27:20.

## Phase 2 authorization and additions

**User prompt**

> Proceed to Phase 2. Also: (1) report Barbie counts by character, (2) report under-4-word counts within the reachable subsets only (Homer Simpson, Barbie Margot), (3) add a "migration backfill" section to the findings listing the 100 missing verses and 47 missing Homer Simpson lines to embed at Supabase load time. Don't write to Weaviate, (4) correct the 570,870 figure in `docs/migration_questions.md` and `weaviate_to_supabase_assessment.md`. Stop after Phase 2 and report the numbers inline.

**Reported summary**

> Phase 2 found only 278 of 1,274 Barbie records are reachable (Barbie Margot), 29,735 of 158,014 Homer records are reachable (Homer Simpson), and all 31,002 Jesus records are reachable. Candidate deduplication yielded 274 Barbie, 25,068 Homer, and 31,001 Jesus records. Under-four-word reachable counts were 38 Barbie Margot records and 7,716 Homer Simpson records. The migration backfill was documented; the later corrected payload contains 100 Jesus records plus 37 non-empty Homer records, omitting 10 blank Homer rows.

## Phase 3 authorization and additions

**User prompt**

> Proceed to Phase 3 with these additions: (1) add a "live baseline": the reachable corpus WITH duplicates at 3072. Report how often live top-3 contains duplicate or near-duplicate lines, and unique-content-per-top-3 for live vs. deduped. (2) check whether Barbie character="none" (278) is narration/action or a parsing artifact tied to Barbie Margot's 278 lines; show 5 samples. (3) omit the 10 empty Homer rows from backfill. (4) use gpt-4o-mini as the judge model, and never print vectors or full exports to the console. Stop after Phase 3 and report results inline.

**Reported summary**

> The Phase 3 live baseline showed duplicate/near-duplicate top-3 results for 0.0% of Barbie queries, 2.5% of Homer queries, and 0.0% of Jesus queries. Mean unique content per top-3 was 2.125 for Barbie and 3.0 for Homer and Jesus, unchanged by deduplication for this query set. Barbie `character = none` was confirmed as 196 action and 82 scene-heading parser records, not Barbie Margot dialogue; the equal count of 278 is coincidental. The answer-level comparison used `gpt-4o-mini` and found 97.78% tie-or-better for each high-fidelity dimensional candidate, but retrieval-level criteria did not approve a reduced dimension.

## Halfvec approval, serialization validation, and Phase 4 authorization

**User prompt**

> Accept halfvec(3072) for the 56,343-vector reachable corpus. Before Phase 4: the 0.71 validation compared different inputs, so it doesn't test truncation. Inspect each collection's text2vec-openai module config (vectorizeClassName, per-property skip/vectorizePropertyName) and reconstruct the exact serialized string Weaviate embedded. Confirm on 20 objects per collection that fresh text-embedding-3-large vectors of that string match stored vectors at cosine ≥ 0.999. Document the serialization function in findings and use it to generate the backfill payload's input strings (don't embed yet). Then do Phase 4 sizing for halfvec(3072) only: 56,343 + 137 backfill rows, HNSW index size, and the minimum Supabase compute tier. Stop and report.

**Reported summary**

> Completed Phase 4 sizing and serialization validation. No Weaviate writes, Supabase/app changes, or full-corpus/backfill embedding occurred.
>
> - Exact Weaviate object serialization was confirmed on 20 objects per collection at cosine ≥ 0.999: Barbie minimum 0.999363; Homer minimum 0.999937; Jesus minimum 0.999898.
> - The old ~0.71 result was withdrawn because it used different inputs (`content` only), so it did not test truncation.
> - The backfill payload now has exact `embedding_input` strings for 100 Jesus + 37 non-empty Homer records; none were embedded.
> - Accepted scope: 56,343 reachable + 137 backfill = 56,480 rows.
> - `halfvec(3072)` raw vector payload: 331.37 MiB.
> - Estimated HNSW index: 477.79–523.29 MiB; vectors plus index: 809.16–854.66 MiB.
> - Minimum recommended Supabase tier: Small (2 GB RAM). Micro is too tight; use Medium temporarily only if index construction swaps.

## Documentation-history question

**User prompt**

> Are the summaries you printed above and their corresponding prompts from me documented in the repo somewhere?

**Reported summary**

> The results and phase requirements were documented in the findings, investigation specification, and scripts README, but the follow-up prompts themselves were not preserved verbatim in a repository file.
