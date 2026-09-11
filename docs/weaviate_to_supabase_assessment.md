# Weaviate to Supabase Assessment

## Summary

This assessment reviews the repository’s current RAG path and the feasibility of moving its Weaviate-backed vectors to Supabase pgvector without changing the site’s frontend experience. No application code or configuration was modified as part of the assessment.

## Findings

The UI sends only `{ prompt, persona }` to Supabase Edge Functions and expects `{ response }`, so the vector-store replacement can remain entirely behind the existing interface. The live custom-persona path is Weaviate-specific, but the LLM, system prompts, frontend, and Supabase Edge Function runtime already exist independently. The repository retains the original source files and document-generation logic, so Weaviate is not the sole copy of the data.

## Current RAG Flow

1. A user selects Barbie, Homer, or Jesus in the React dropdown. Selecting one triggers a non-critical `weaviate-warmup` request.
2. The user enters a question and clicks Send (or presses Enter).
3. The frontend immediately displays the user message and invokes `weaviate-chat` with the question and selected persona.
4. `weaviate-chat` maps the persona to Weaviate collections: `Barbie`, `Homer`, or `Jesus`.
5. It runs a Weaviate GraphQL `nearText` semantic query with `limit: 3`.
   - Barbie filters to `character = "Barbie Margot"`.
   - Homer filters to `character = "Homer Simpson"`.
   - Jesus has no character filter.
6. It retains results whose Weaviate cosine distance is below `0.85`, joins their `content` fields as RAG context, and falls back to a persona-only prompt if no context is available.
7. It builds a system message containing persona instructions plus retrieved material, then sends that system message and the user question to OpenAI through LangChain.
8. The model is `gpt-4o-mini`, with temperature `0.7` and a 325-token cap—not GPT-4o despite the UI label.
9. The Edge Function returns `{ response }`; the UI appends and displays it. There is no server-side conversation memory: each request is independent.

## Feasibility Report

| Work item | Feasibility | Notes |
|---|---|---|
| Download vectors from Weaviate | High | Weaviate supports iterating every object and explicitly requesting each stored vector plus properties/UUIDs. Export all three collections before cancellation. [Weaviate read-all-objects docs](https://docs.weaviate.io/weaviate/manage-objects/read-all-objects) |
| Upload vectors to Supabase | High, with a design choice | Supabase Postgres supports pgvector storage, bulk loading, metadata, cosine search, and RPC-based retrieval. [Supabase vector columns](https://supabase.com/docs/guides/ai/vector-columns) |
| Replace semantic-search plumbing | High | Generate a query embedding with the same model, call a Postgres RPC similarity function, return the top three context strings, and leave prompt construction/OpenAI/UI behavior intact. [Supabase semantic search](https://supabase.com/docs/guides/ai/semantic-search) |

### Important Constraint: Embedding Dimensions

The checked-in Weaviate configuration uses `text-embedding-3-large` (3072 dimensions), while a normal indexed pgvector `vector` column supports up to 2,000 dimensions. Supabase supports indexed `halfvec` up to 4,000 dimensions, so direct migration is possible with `halfvec(3072)`. Alternatively, regenerate embeddings at 1,536 dimensions (or fewer) for simpler and lower-storage indexed vectors; this changes retrieval behavior and requires evaluation. [Supabase vector-index limits](https://supabase.com/docs/guides/ai/vector-indexes), [OpenAI embeddings dimensions](https://developers.openai.com/api/docs/guides/embeddings)

Phase 0 verified a live total of 190,290 vectors: Barbie 1,274, Homer 158,014, and Jesus 31,002. At 3,072 float32 dimensions, that is roughly 2.18 GiB of raw vector values before text, metadata, and HNSW index overhead. The previously documented 570,870 figure was exactly three times the verified total and was a stale/manual documentation error, not a live object count. A direct migration is technically viable, but Supabase database disk and compute capacity must still be checked first.

## Recommendation

Proceed with Supabase pgvector, using three persona-specific tables (or partitions) and HNSW indexes, rather than one cross-persona index with filters. That mirrors today’s separate Weaviate collections and avoids filtered approximate-search recall pitfalls noted by pgvector. [pgvector filtering guidance](https://github.com/pgvector/pgvector#filtering)

For the lowest-risk cutover:

1. Export Weaviate objects, UUIDs, properties, and vectors as a rollback snapshot.
2. Import into Supabase as `halfvec(3072)` to preserve the current embeddings and avoid re-embedding delay and cost.
3. Add a Supabase RPC per persona that returns `content`, metadata, and cosine distance for the top three matches.
4. Replace the internals of `weaviate-chat`; preserve its request/response contract so the UI remains unchanged. Remove the warmup call once Supabase retrieval is live.
5. Run a fixed test set of Barbie, Homer, and Jesus prompts against both backends, compare retrieved passages and answer quality, then switch traffic and retain Weaviate briefly for rollback.

For ongoing cost reduction, a follow-up optimization should remove duplicate or unneeded objects and evaluate regenerated lower-dimensional embeddings. That is likely more economical than permanently copying all 570,000 current vectors, but it should be a separate, quality-tested step rather than part of the initial no-UX-change migration.
