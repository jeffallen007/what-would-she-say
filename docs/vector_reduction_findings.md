# Vector Reduction Findings

> Status: complete through Phase 4 sizing. No Weaviate writes, Supabase changes, application changes, or full-corpus re-embedding were performed.

## Phase 0 and 1 Baseline

The read-only snapshot verified 190,290 live vectors: Barbie 1,274; Homer 158,014; and Jesus 31,002. All are 3,072-dimensional `text-embedding-3-large` vectors with cosine distance. The prior 570,870 count was a stale/manual documentation figure, exactly three times the verified live total.

| Collection | Live objects | Source objects | Difference |
|---|---:|---:|---:|
| Barbie | 1,274 | 1,274 parsed screenplay documents | 0 |
| Homer | 158,014 | 158,314 Kaggle CSV rows | -300 |
| Jesus | 31,002 | 31,102 Bible verses | -100 |

## Phase 2 Reduction Candidates

Near-duplicate detection uses a high-recall HNSW nearest-neighbor scan over only the reachable corpus, since unreachable records are not migration candidates. Exact duplicates are normalized by lowercasing, collapsing whitespace, and stripping punctuation. The combined count unions unreachable, exact-duplicate, and near-duplicate candidates so an object is never counted twice. Short chunks are flagged only, not included in the removable total.

| Collection | Reachable | Unreachable | Exact duplicate removals | Near-duplicate removals | Under 4 words in reachable subset | Combined removable | Phase 3 candidate corpus |
|---|---:|---:|---:|---:|---:|---:|---:|
| Barbie | 278 | 996 (78.18%) | 2 | 4 | 38 (13.67%) | 1,000 (78.49%) | 274 |
| Homer | 29,735 | 128,279 (81.18%) | 4,273 | 4,329 | 7,716 (25.95%) | 132,946 (84.14%) | 25,068 |
| Jesus | 31,002 | 0 | 1 | 0 | 0 | 1 | 31,001 |

The removal candidates are not an approved deletion plan. In particular, low-value short chunks need the Phase 3 baseline-retrieval test before any recommendation to remove them.

## Barbie Character Counts

The full 89-value distribution is generated reproducibly at the ignored local path `scripts/vector-investigation/data/phase1_barbie_character_distribution.csv`. The principal values are: Barbie Margot 278; `none` 278; Ken Ryan Gosling 145; Gloria 84; Sasha 60; Mattel Ceo 54; Weird Barbie 52; Ken Kingsley 26; Aaron Dinkins 25; Allan, Barbie Issa, and Ruth 20 each; Ken Simu 17; Helen Mirren 16; Barbie Alexandra 14; Barbie Emma 13; Barbie Hari and Barbie Sharon 12 each. Every value except Barbie Margot is unreachable in the live retrieval path.

## Migration Backfill

The following source records are absent from Weaviate and must be backfilled during the Supabase load. The complete ready-to-embed payload is generated locally at `scripts/vector-investigation/data/phase2_migration_backfill.json`; it contains 100 Jesus records and 37 non-empty Homer Simpson records. The 10 missing Homer rows with empty dialogue are intentionally omitted from that payload and should not receive embedding requests.

### Jesus: 100 missing verses

- Psalm 116:2 through Psalm 119:1, inclusive (50 verses).
- Matthew 26:46 through Matthew 27:20, inclusive (50 verses).

### Homer Simpson: 47 missing source lines

| Source CSV row | Dialogue |
|---:|---|
| 16600 | Mmmmm... free goo. |
| 16619 | Marge, don't discourage the boy. Weaseling out of things is important to learn. It's what separates us from the animals. Except the weasel. |
| 82453 | Just like the Pope! |
| 82454 | Being unselfish is a natural high, like hiking or paint thinner. |
| 82455 | And here's another act of Christian charity I pulled out of my butt. |
| 82456 | I built a skating rink for the whole town! |
| 82465 | Here's your skates. Oh, you'll have to take off those boots. |
| 82467 | Ewww. |
| 82491 | Pathetic Flanders. Thinking he can buy people's love with thoughtful gifts. |
| 82494 | I'll show Flanders. I'm gonna get everyone a car. What's that one good American car? |
| 82496 | Uh... is it despair? |
| 82498 | Hmm. You've given me a lot to think about. |
| 117580 | The library? Bart, can you believe we're married to those nerds? |
| 117581 | *(empty dialogue)* |
| 122450 | Why couldn't it have been me? |
| 122452 | Shut up. |
| 122463 | Whose turn is it to cry? |
| 122465 | *(empty dialogue)* |
| 122467 | Look at that picture! |
| 122471 | *(empty dialogue)* |
| 122474 | Someday TV will be invented, and it will be free. Then it will cost money. |
| 130500 | Thank you. |
| 130503 | Woo hoo! Thank God it's T.G.I.F! |
| 130510 | You're outta here, drug-o. |
| 130512 | *(empty dialogue)* |
| 130517 | Well... I didn't really feel like going to Moe's today... thought I might hang out here for as long as I can take it. |
| 130519 | Yeah... but a weekend without drinking is no big deal. I did it when I was in that alcohol-induced coma. |
| 130520 | So, what's on the agenda? |
| 130522 | *(empty dialogue)* |
| 130524 | *(empty dialogue)* |
| 130526 | *(empty dialogue)* |
| 130528 | Why did I do that? / It sounds so dull and boring. / What was I thinking? |
| 130530 | *(empty dialogue)* |
| 130533 | What the-- Section 1 of Article 21 of the State Constitution is amended to read: Section 1. In the year following the year in which the national census is taken under the direction of Congress at the beginning of each decade, the Legislature shall adjust the boundary lines of Congressional, State Senate and Assembly districts. Liquor... mustn't think of liquor... |
| 130538 | So, a sober weekend hasn't been that hard. Let me just take a few antidepressants here. |
| 130539 | I feel sorry for people without willpower. I truly do. |
| 130541 | A surprisingly not-horrible fruit drink called a mimosa. |
| 130543 | Then there's champagne in me! What am I gonna do? It's less than twenty-four hours till my drug test. Maybe I can sweat it out. |
| 130544 | Oh man, I'd better have some coffee and iced tea. |
| 130546 | What about this lemonade? |
| 130548 | Then I'd better soak up the alcohol with some food! Oooh, cake! |
| 144863 | You don't know anything about hydraulic fracturing! You've just been brainwashed by liberal TV shows who use "fracking" as an easy bad guy. But it can save this country! |
| 144865 | Wait... I finally get what you're saying. Fracking is great. But the only place it should ever happen is in other people's towns! |
| 144884 | Hey, a couch is a couch. |
| 144885 | *(empty dialogue)* |
| 144886 | *(empty dialogue)* |
| 144887 | Woo hoo! |

## Phase 3 Dimension Evaluation

The Phase 3 live baseline uses the reachable corpus with duplicates at 3,072 dimensions. The comparison baseline uses its deduplicated reachable version at the same dimensions. Both use exact local cosine retrieval, the live threshold equivalent of cosine similarity greater than 0.15, and the fixed 40-question-per-persona query set.

| Persona | Live reachable | Deduplicated reachable | Live top-3 containing duplicate/near-duplicate content | Mean unique content returned per top-3: live / deduplicated |
|---|---:|---:|---:|---:|
| Barbie | 278 | 274 | 0.0% | 2.125 / 2.125 |
| Homer | 29,735 | 25,077 | 2.5% | 3.000 / 3.000 |
| Jesus | 31,002 | 31,001 | 0.0% | 3.000 / 3.000 |

The lower Barbie unique-content average results from threshold fallbacks, not duplicate lines. The live top-3 duplicate result shows that duplicate removal is a useful storage cleanup but does not materially change retrieved diversity for this query set.

| Persona | Dimension | Mean top-3 overlap with deduplicated 3072 baseline | Identical top-3 | Fallback rate |
|---|---:|---:|---:|---:|
| Barbie | 256 / 512 / 768 / 1024 / 1536 / 2000 | 0.483 / 0.608 / 0.658 / 0.708 / 0.750 / 0.775 | 2.5% / 17.5% / 20.0% / 27.5% / 40.0% / 65.0% | 2.5% / 5.0% / 7.5% / 7.5% / 10.0% / 15.0% |
| Homer | 256 / 512 / 768 / 1024 / 1536 / 2000 | 0.358 / 0.592 / 0.650 / 0.725 / 0.800 / 0.875 | 2.5% / 5.0% / 17.5% / 22.5% / 32.5% / 52.5% | 0.0% at every dimension |
| Jesus | 256 / 512 / 768 / 1024 / 1536 / 2000 | 0.375 / 0.517 / 0.667 / 0.733 / 0.825 / 0.875 | 2.5% / 2.5% / 7.5% / 20.0% / 30.0% / 40.0% | 0.0% at every dimension |

The live threshold already falls back for 7 of 40 Barbie queries (17.5%) and for no Homer or Jesus queries. No candidate passes the proposed decision rule: every persona must achieve at least 0.85 mean overlap with no increased fallback. Barbie fails the overlap requirement even at 2,000 dimensions (0.775); its candidate fallback rates are not higher than the 17.5% live baseline. The earlier 0.718/0.714/0.711 “validation” is withdrawn: it compared fresh `content`-only requests with stored object embeddings, so it was not a test of dimensional truncation.

The two highest-fidelity candidates (2,000 and 1,536) were tested at answer level: 15 queries per persona, with `gpt-4o-mini` used both for generation and blind judging. Each received 1 win, 43 ties, and 1 loss across 45 comparisons against the deduplicated 3,072-dimensional baseline (97.78% tie-or-better). This does not override the retrieval failure; it only indicates no answer-level difference detected in this small, model-judged sample.

### Barbie `character = none` Investigation

All 278 `none` records are parser-generated non-dialogue content: 196 `action` records and 82 `scene_heading` records. They are not Barbie Margot lines; the matching count of 278 is coincidental. Sample records include: `47.`; `int. nobel prize theatre. day.`; `35. - The Mom sadly drops her daughter off at school...`; `39. Aaron stops at the desk. Gloria is so lost in her drawing...`; and `int. office. continuous.`

## Serialization Validation for Migration Inputs

The live module configuration is the same for every collection: `text2vec-openai`, model `text-embedding-3-large`, and `vectorizeClassName=true`. There is no collection `properties` allow-list. Every inspected property is `skip=false` and `vectorizePropertyName=false`:

| Collection | Properties inspected (`type`; `skip`; `vectorizePropertyName`) |
|---|---|
| Barbie | `character`, `content`, `source`, `type` (text; false; false); `doc_id`, `page_number` (number; false; false); `voice_over` (boolean; false; false) |
| Homer | `character`, `content`, `source` (text; false; false); `doc_id`, `row` (number; false; false) |
| Jesus | `content`, `source`, `verse` (text; false; false); `doc_id` (number; false; false) |

Consequently, the Weaviate shared object vectorizer alphabetically sorts object fields, keeps textual values only, and joins the collection name plus those values with a single space. Numeric and boolean fields are not included; property names are not included; casing and embedded whitespace in values are preserved.

```text
serialize(collection, object) =
  join(" ", [splitCamelCase(collection), *textual_values(object, sorted_by_property_name)])
```

Thus the effective field order is: Barbie = `Barbie character content source type`; Homer = `Homer character content source`; Jesus = `Jesus content source verse`. The reusable implementation is [weaviate_serialization.py](../scripts/vector-investigation/weaviate_serialization.py), and [validate_weaviate_serialization.py](../scripts/vector-investigation/validate_weaviate_serialization.py) reads only the live configuration plus the Phase 0 snapshot. It sent 20 reconstructed inputs per collection to `text-embedding-3-large`, without vectors or full exports in console output:

| Collection | Sample size | Minimum cosine vs. stored vector | Mean cosine | All at least 0.999 |
|---|---:|---:|---:|---|
| Barbie | 20 | 0.999363 | 0.999956 | Yes |
| Homer | 20 | 0.999937 | 0.999994 | Yes |
| Jesus | 20 | 0.999898 | 0.999985 | Yes |

This confirms the reconstructed serialization is suitable for migration. The generated backfill payload now contains an `embedding_input` for each of its 100 Jesus and 37 non-empty Homer records. These strings are ready for a future migration load but have not been embedded.

## Phase 4: Accepted `halfvec(3072)` Sizing

The approved migration scope is 56,343 reachable vectors plus 137 non-empty backfill rows: **56,480 rows**. A `halfvec(3072)` value occupies 6,152 bytes, for 331.37 MiB (0.324 GiB) of raw vector-value payload. The intended HNSW index is `USING hnsw ((embedding::halfvec(3072)) halfvec_cosine_ops)`.

| Item | Estimate |
|---|---:|
| Raw `halfvec(3072)` value payload | 331.37 MiB |
| HNSW index, default `m=16` | 477.79–523.29 MiB |
| Values plus HNSW index | 809.16–854.66 MiB |

The HNSW range accounts for one 8 KiB index vector page per 3,072-dimensional `halfvec`, default graph links, and 5–15% index/page overhead; it excludes ordinary table rows, text/metadata, WAL during load, and Postgres overhead. Measure the actual result after a pilot load with `pg_relation_size` before committing to a production disk allowance.

**Minimum compute tier: Supabase Small (2 GB RAM).** Micro (1 GB) leaves insufficient headroom once the platform’s base memory, PostgreSQL work memory, normal traffic, and an approximately 0.46–0.50 GiB HNSW index coexist. Load in batches and build the index afterward; temporarily use Medium (4 GB) if the Small build swaps, then measure and scale back down. This recommendation aligns with Supabase’s current [compute sizing benchmarks](https://supabase.com/docs/guides/ai/choosing-compute-addon) and [2 GB Small specification](https://supabase.com/docs/guides/platform/compute-and-disk). Supabase documents the exact `halfvec(3072)` HNSW expression and its 4,000-dimension limit [here](https://supabase.com/docs/guides/ai/vector-indexes/hnsw-indexes).
