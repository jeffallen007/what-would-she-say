# LLM / RAG App Migration Discovery Questions

## 1. Current Architecture

### Frontend

* What frontend framework is the application using?

  * Next.js (App Router?)
  * Vite React
  * Other

Answer: Vite React. The repo has `vite.config.ts`, `src/main.tsx`, and `react-router-dom`; there is no Next.js/App Router code.

* Is the frontend:

  * SPA
  * SSR
  * Hybrid

Answer: SPA. There is no server-rendered frontend framework or SSR entrypoint in the repo.

### Backend / Runtime

* Where does backend logic run?

  * Vercel API routes
  * Edge functions
  * Separate backend service
  * Python backend
  * Other

Answer: Edge functions plus Python scripts. The runtime logic is in `supabase/functions/*` and the offline vectorstore tooling is in `scripts/vectorstore-generation/*`.

* Are there any background jobs or schedulers?

  * Cron jobs
  * Queues
  * Workers
  * Serverless scheduled tasks

Answer: No background jobs or schedulers are defined in the repo. The only repeated work is client-triggered warmup, which is not a scheduler.

### LLM Providers

* Which LLM providers are currently used?

  * OpenAI
  * Anthropic
  * Azure OpenAI
  * Other

Answer: OpenAI only.

* Which specific models are used?

Answer: The runtime chat path uses `gpt-4o-mini`. The repo also uses OpenAI embeddings in multiple places: the checked-in Weaviate collection schemas declare `text-embedding-3-large`, and `supabase/functions/generate-vectorstore/index.ts` explicitly calls `text-embedding-3-small`. The query-time `OpenAIEmbeddings` instances in the chat functions do not pin a model in code.

### Embeddings

* Which embedding model is currently used?
* What embedding dimensions are stored in Weaviate?

Answer: The repo does not pin a single embedding model. The checked-in Weaviate collection schemas use `text2vec-openai` with `text-embedding-3-large`; the Supabase vectorstore generation function uses `text-embedding-3-small`; and the query paths use LangChain `OpenAIEmbeddings` without an explicit model setting.

Answer: the live Weaviate collection dimensions are not exported in the repo. Inference from the checked-in model choice is 3072 for `text-embedding-3-large`, while `text-embedding-3-small` would be 1536. Within Weaviate, there are 3 Collections (1 for each "persona"). Looks like the default is (dimension size: 3072). If migrating, I think this dimensions can be reduced. All Collections have the following vector configurations setup:
- Vector name:  Default
- Model: text-embedding-3-large
- Dimensions:  N/A
- Vectorized properties:  None
- Collection name:  Vectorized
- Compression:  RQ 8-bit


### RAG Framework

* Which framework is used?

  * LangChain
  * LlamaIndex
  * Custom retrieval pipeline
  * Other

Answer: LangChain plus a custom retrieval pipeline. `supabase/functions/chat/index.ts` does cosine similarity over stored embeddings, and `supabase/functions/weaviate-chat/index.ts` uses raw Weaviate GraphQL `nearText` queries, both wrapped in LangChain prompt/LLM calls.

### Authentication / User Management

* Is there user authentication?
* Which auth provider is used?

  * Supabase Auth
  * Clerk
  * Auth0
  * Custom
  * Other

Answer: No user authentication is implemented in the app code. The Supabase client uses the anon key, but there is no sign-in, login, or session flow in the repo.

Answer: Auth provider: none / not used.

### Database / Persistence

* Besides Weaviate, what databases are used?

  * Supabase Postgres
  * Firebase
  * MongoDB
  * Other

Answer: No relational database is defined in the repo. The only persistent app storage outside Weaviate is Supabase Storage bucket data, plus static source files such as `public/bible.txt`. The generated Supabase types file contains no tables, views, functions, or enums.

### Hosting / Infrastructure

* What services are currently involved?

  * Vercel
  * Weaviate
  * Lovable
  * Supabase
  * GitHub
  * Cloudflare
  * Other

Answer: Supabase, Weaviate, GitHub, OpenAI, and Lovable-related dev/tooling residue. I do not see Vercel or Cloudflare config in the repo.

---

# 2. Weaviate Usage

## Weaviate Hosting

* Is Weaviate:

  * Cloud hosted
  * Self hosted
  * Embedded/local

Answer: Cloud hosted. The Python client uses `weaviate.connect_to_weaviate_cloud(...)` and the docs point to Weaviate Cloud Collections.

* Which pricing tier or cluster size?

Answer: the tier/cluster size is not stored in the repo. The Weaviate console is not great about displaying these details, but on my invoice, the following are listed:
- Flex Shared - Storage GBs (backups) (GCP, us-west3) (Qty. 66)
- Flex Shared - Storage GBs (objects, indexes) (GCP, us-west3) (Qty. 10)
- Flex Shared - Millions of vector dimensions - HNSW, RQ8 (GCP, us-west3) (Qty. 1754)

## Data Scale

* Approximately how many vector objects/documents exist?
* Approximately how many source documents?
* Average chunk size?
* Average chunks per document?

Answer: Jesus source text has 31,102 lines total in `scripts/vectorstore-generation/source-files/bible.txt`, so the Jesus collection is approximately 31,101 documents if ingested 1:1 from verse lines. Homer source CSV has 158,315 lines total in `scripts/vectorstore-generation/source-files/simpsons_dataset.csv`, so the Homer collection is approximately 158,314 documents if ingested 1:1 from rows. Barbie scale is not recoverable from the repo because the PDF parser groups scene/dialogue/action into documents and the live object count is not exported.

Answer: Average chunk size and average chunks per document are not fixed in the Weaviate path. Jesus and Homer are effectively 1 source row or verse per object; Barbie is parser-driven and variable.
- Total object count per Weaviate cloud is 570,870.

## Collections / Schema

* How many collections/classes are used?
* What are the collection names?
* What metadata fields are stored?

Example:

* source
* title
* url
* timestamp
* tags
* tenant_id
* author
* custom fields

Answer: Three collections/classes are used: `Jesus`, `Homer`, and `Barbie`.

Answer: The checked-in collection JSON files only declare `content` as a text property for each collection, with `text2vec-openai` as the vectorizer and `text-embedding-3-large` in module config.

Answer: Runtime code also expects metadata fields such as `character`, `source`, `doc_id`, `verse`, `page_number`, `type`, and `voice_over`. I queried the schema using the Weaviate API.
```
{
  "Barbie": "_CollectionConfig(name='Barbie', description='Dialogue and actions from Barbie the Movie.', generative_config=None, inverted_index_config=_InvertedIndexConfig(bm25=_BM25Config(b=0.75, k1=1.2), cleanup_interval_seconds=60, index_null_state=False, index_property_length=False, index_timestamps=False, stopwords=_StopwordsConfig(preset=<StopwordsPreset.EN: 'en'>, additions=None, removals=None), stopword_presets=None), multi_tenancy_config=_MultiTenancyConfig(enabled=False, auto_tenant_creation=False, auto_tenant_activation=False), object_ttl_config=None, properties=[_Property(name='character', description=\"This property was generated by Weaviate's auto-schema feature on Sun Aug 10 05:20:30 2025\", data_type=<DataType.TEXT: 'text'>, index_filterable=True, index_range_filters=False, index_searchable=True, nested_properties=None, text_analyzer=None, tokenization=<Tokenization.WORD: 'word'>, vectorizer_config=_PropertyVectorizerConfig(skip=False, vectorize_property_name=False), vectorizer='text2vec-openai', vectorizer_configs=None), _Property(name='content', description='-', data_type=<DataType.TEXT: 'text'>, index_filterable=True, index_range_filters=False, index_searchable=True, nested_properties=None, text_analyzer=None, tokenization=<Tokenization.WORD: 'word'>, vectorizer_config=_PropertyVectorizerConfig(skip=False, vectorize_property_name=False), vectorizer='text2vec-openai', vectorizer_configs=None), _Property(name='doc_id', description=\"This property was generated by Weaviate's auto-schema feature on Sun Aug 10 05:20:30 2025\", data_type=<DataType.NUMBER: 'number'>, index_filterable=True, index_range_filters=False, index_searchable=False, nested_properties=None, text_analyzer=None, tokenization=None, vectorizer_config=_PropertyVectorizerConfig(skip=False, vectorize_property_name=False), vectorizer='text2vec-openai', vectorizer_configs=None), _Property(name='page_number', description=\"This property was generated by Weaviate's auto-schema feature on Sun Aug 10 05:20:30 2025\", data_type=<DataType.NUMBER: 'number'>, index_filterable=True, index_range_filters=False, index_searchable=False, nested_properties=None, text_analyzer=None, tokenization=None, vectorizer_config=_PropertyVectorizerConfig(skip=False, vectorize_property_name=False), vectorizer='text2vec-openai', vectorizer_configs=None), _Property(name='source', description=\"This property was generated by Weaviate's auto-schema feature on Sun Aug 10 05:20:30 2025\", data_type=<DataType.TEXT: 'text'>, index_filterable=True, index_range_filters=False, index_searchable=True, nested_properties=None, text_analyzer=None, tokenization=<Tokenization.WORD: 'word'>, vectorizer_config=_PropertyVectorizerConfig(skip=False, vectorize_property_name=False), vectorizer='text2vec-openai', vectorizer_configs=None), _Property(name='type', description=\"This property was generated by Weaviate's auto-schema feature on Sun Aug 10 05:20:30 2025\", data_type=<DataType.TEXT: 'text'>, index_filterable=True, index_range_filters=False, index_searchable=True, nested_properties=None, text_analyzer=None, tokenization=<Tokenization.WORD: 'word'>, vectorizer_config=_PropertyVectorizerConfig(skip=False, vectorize_property_name=False), vectorizer='text2vec-openai', vectorizer_configs=None), _Property(name='voice_over', description=\"This property was generated by Weaviate's auto-schema feature on Sun Aug 10 05:20:30 2025\", data_type=<DataType.BOOL: 'boolean'>, index_filterable=True, index_range_filters=False, index_searchable=False, nested_properties=None, text_analyzer=None, tokenization=None, vectorizer_config=_PropertyVectorizerConfig(skip=False, vectorize_property_name=False), vectorizer='text2vec-openai', vectorizer_configs=None)], references=[], replication_config=_ReplicationConfig(factor=3, async_enabled=False, deletion_strategy=<ReplicationDeletionStrategy.TIME_BASED_RESOLUTION: 'TimeBasedResolution'>, async_config=None), reranker_config=None, sharding_config=_ShardingConfig(virtual_per_physical=128, desired_count=1, actual_count=1, desired_virtual_count=128, actual_virtual_count=128, key='_id', strategy='hash', function='murmur3'), vector_index_config=_VectorIndexConfigHNSW(multi_vector=None, quantizer=_RQConfig(cache=None, bits=8, rescore_limit=20), cleanup_interval_seconds=300, distance_metric=<VectorDistances.COSINE: 'cosine'>, dynamic_ef_min=100, dynamic_ef_max=500, dynamic_ef_factor=8, ef=-1, ef_construction=128, filter_strategy=<VectorFilterStrategy.SWEEPING: 'sweeping'>, flat_search_cutoff=40000, max_connections=32, skip=False, vector_cache_max_objects=1000000000000), vector_index_type=<VectorIndexType.HNSW: 'hnsw'>, vectorizer_config=_VectorizerConfig(vectorizer=<Vectorizers.TEXT2VEC_OPENAI: 'text2vec-openai'>, model={'baseURL': 'https://api.openai.com', 'model': 'text-embedding-3-large', 'type': 'text'}, vectorize_collection_name=True), vectorizer=<Vectorizers.TEXT2VEC_OPENAI: 'text2vec-openai'>, vector_config=None)",
  "Homer": "_CollectionConfig(name='Homer', description='Dialogue from The Simpsons TV Show.', generative_config=None, inverted_index_config=_InvertedIndexConfig(bm25=_BM25Config(b=0.75, k1=1.2), cleanup_interval_seconds=60, index_null_state=False, index_property_length=False, index_timestamps=False, stopwords=_StopwordsConfig(preset=<StopwordsPreset.EN: 'en'>, additions=None, removals=None), stopword_presets=None), multi_tenancy_config=_MultiTenancyConfig(enabled=False, auto_tenant_creation=False, auto_tenant_activation=False), object_ttl_config=None, properties=[_Property(name='character', description=\"This property was generated by Weaviate's auto-schema feature on Sun Aug 10 06:14:51 2025\", data_type=<DataType.TEXT: 'text'>, index_filterable=True, index_range_filters=False, index_searchable=True, nested_properties=None, text_analyzer=None, tokenization=<Tokenization.WORD: 'word'>, vectorizer_config=_PropertyVectorizerConfig(skip=False, vectorize_property_name=False), vectorizer='text2vec-openai', vectorizer_configs=None), _Property(name='content', description='-', data_type=<DataType.TEXT: 'text'>, index_filterable=True, index_range_filters=False, index_searchable=True, nested_properties=None, text_analyzer=None, tokenization=<Tokenization.WORD: 'word'>, vectorizer_config=_PropertyVectorizerConfig(skip=False, vectorize_property_name=False), vectorizer='text2vec-openai', vectorizer_configs=None), _Property(name='doc_id', description=\"This property was generated by Weaviate's auto-schema feature on Sun Aug 10 06:14:51 2025\", data_type=<DataType.NUMBER: 'number'>, index_filterable=True, index_range_filters=False, index_searchable=False, nested_properties=None, text_analyzer=None, tokenization=None, vectorizer_config=_PropertyVectorizerConfig(skip=False, vectorize_property_name=False), vectorizer='text2vec-openai', vectorizer_configs=None), _Property(name='row', description=\"This property was generated by Weaviate's auto-schema feature on Sun Aug 10 06:14:51 2025\", data_type=<DataType.NUMBER: 'number'>, index_filterable=True, index_range_filters=False, index_searchable=False, nested_properties=None, text_analyzer=None, tokenization=None, vectorizer_config=_PropertyVectorizerConfig(skip=False, vectorize_property_name=False), vectorizer='text2vec-openai', vectorizer_configs=None), _Property(name='source', description=\"This property was generated by Weaviate's auto-schema feature on Sun Aug 10 06:14:51 2025\", data_type=<DataType.TEXT: 'text'>, index_filterable=True, index_range_filters=False, index_searchable=True, nested_properties=None, text_analyzer=None, tokenization=<Tokenization.WORD: 'word'>, vectorizer_config=_PropertyVectorizerConfig(skip=False, vectorize_property_name=False), vectorizer='text2vec-openai', vectorizer_configs=None)], references=[], replication_config=_ReplicationConfig(factor=3, async_enabled=False, deletion_strategy=<ReplicationDeletionStrategy.TIME_BASED_RESOLUTION: 'TimeBasedResolution'>, async_config=None), reranker_config=None, sharding_config=_ShardingConfig(virtual_per_physical=128, desired_count=1, actual_count=1, desired_virtual_count=128, actual_virtual_count=128, key='_id', strategy='hash', function='murmur3'), vector_index_config=_VectorIndexConfigHNSW(multi_vector=None, quantizer=_RQConfig(cache=None, bits=8, rescore_limit=20), cleanup_interval_seconds=300, distance_metric=<VectorDistances.COSINE: 'cosine'>, dynamic_ef_min=100, dynamic_ef_max=500, dynamic_ef_factor=8, ef=-1, ef_construction=128, filter_strategy=<VectorFilterStrategy.SWEEPING: 'sweeping'>, flat_search_cutoff=40000, max_connections=32, skip=False, vector_cache_max_objects=1000000000000), vector_index_type=<VectorIndexType.HNSW: 'hnsw'>, vectorizer_config=_VectorizerConfig(vectorizer=<Vectorizers.TEXT2VEC_OPENAI: 'text2vec-openai'>, model={'baseURL': 'https://api.openai.com', 'model': 'text-embedding-3-large', 'type': 'text'}, vectorize_collection_name=True), vectorizer=<Vectorizers.TEXT2VEC_OPENAI: 'text2vec-openai'>, vector_config=None)",
  "Jesus": "_CollectionConfig(name='Jesus', description='Verses from the Bible.', generative_config=None, inverted_index_config=_InvertedIndexConfig(bm25=_BM25Config(b=0.75, k1=1.2), cleanup_interval_seconds=60, index_null_state=False, index_property_length=False, index_timestamps=False, stopwords=_StopwordsConfig(preset=<StopwordsPreset.EN: 'en'>, additions=None, removals=None), stopword_presets=None), multi_tenancy_config=_MultiTenancyConfig(enabled=False, auto_tenant_creation=False, auto_tenant_activation=False), object_ttl_config=None, properties=[_Property(name='content', description='-', data_type=<DataType.TEXT: 'text'>, index_filterable=True, index_range_filters=False, index_searchable=True, nested_properties=None, text_analyzer=None, tokenization=<Tokenization.WORD: 'word'>, vectorizer_config=_PropertyVectorizerConfig(skip=False, vectorize_property_name=False), vectorizer='text2vec-openai', vectorizer_configs=None), _Property(name='doc_id', description=\"This property was generated by Weaviate's auto-schema feature on Sun Aug 10 05:26:54 2025\", data_type=<DataType.NUMBER: 'number'>, index_filterable=True, index_range_filters=False, index_searchable=False, nested_properties=None, text_analyzer=None, tokenization=None, vectorizer_config=_PropertyVectorizerConfig(skip=False, vectorize_property_name=False), vectorizer='text2vec-openai', vectorizer_configs=None), _Property(name='source', description=\"This property was generated by Weaviate's auto-schema feature on Sun Aug 10 05:26:54 2025\", data_type=<DataType.TEXT: 'text'>, index_filterable=True, index_range_filters=False, index_searchable=True, nested_properties=None, text_analyzer=None, tokenization=<Tokenization.WORD: 'word'>, vectorizer_config=_PropertyVectorizerConfig(skip=False, vectorize_property_name=False), vectorizer='text2vec-openai', vectorizer_configs=None), _Property(name='verse', description=\"This property was generated by Weaviate's auto-schema feature on Sun Aug 10 05:26:54 2025\", data_type=<DataType.TEXT: 'text'>, index_filterable=True, index_range_filters=False, index_searchable=True, nested_properties=None, text_analyzer=None, tokenization=<Tokenization.WORD: 'word'>, vectorizer_config=_PropertyVectorizerConfig(skip=False, vectorize_property_name=False), vectorizer='text2vec-openai', vectorizer_configs=None)], references=[], replication_config=_ReplicationConfig(factor=3, async_enabled=False, deletion_strategy=<ReplicationDeletionStrategy.TIME_BASED_RESOLUTION: 'TimeBasedResolution'>, async_config=None), reranker_config=None, sharding_config=_ShardingConfig(virtual_per_physical=128, desired_count=1, actual_count=1, desired_virtual_count=128, actual_virtual_count=128, key='_id', strategy='hash', function='murmur3'), vector_index_config=_VectorIndexConfigHNSW(multi_vector=None, quantizer=_RQConfig(cache=None, bits=8, rescore_limit=20), cleanup_interval_seconds=300, distance_metric=<VectorDistances.COSINE: 'cosine'>, dynamic_ef_min=100, dynamic_ef_max=500, dynamic_ef_factor=8, ef=-1, ef_construction=128, filter_strategy=<VectorFilterStrategy.SWEEPING: 'sweeping'>, flat_search_cutoff=40000, max_connections=32, skip=False, vector_cache_max_objects=1000000000000), vector_index_type=<VectorIndexType.HNSW: 'hnsw'>, vectorizer_config=_VectorizerConfig(vectorizer=<Vectorizers.TEXT2VEC_OPENAI: 'text2vec-openai'>, model={'baseURL': 'https://api.openai.com', 'model': 'text-embedding-3-large', 'type': 'text'}, vectorize_collection_name=True), vectorizer=<Vectorizers.TEXT2VEC_OPENAI: 'text2vec-openai'>, vector_config=None)"
}
```

## Retrieval Features Used

Which Weaviate features are currently used?

### Search

* Pure vector similarity
* Hybrid search (BM25 + vector)
* Keyword search
* Metadata filtering
* Semantic reranking

Answer: Pure vector similarity plus metadata filtering. The runtime query uses `nearText` and filters on `character` for Homer and Barbie. There is no hybrid/BM25, keyword search, or reranking in the checked-in code.

### Advanced Features

* Multi-tenancy
* Named vectors
* Cross references
* Generative modules
* Agents/modules
* Custom vectorizers

Answer: None of the advanced Weaviate features above are used in the checked-in runtime path.

## Ingestion Pipeline

* How are documents ingested?

  * Python scripts
  * LangChain loaders
  * Manual upload
  * Background jobs
  * API endpoints
  * Webhooks

Answer: Python scripts plus LangChain loaders. The workflow is manual and batch-oriented: `generate_document_objects.py` creates LangChain documents from CSV/TXT/PDF, `weaviate_generate_vectorstore.py` creates collections, and `weaviate_upload_to_vectorstore.py` batch uploads the objects.

* Is ingestion:

  * Manual
  * Automated
  * Incremental
  * Real-time

Answer: Manual. There is no incremental sync or real-time ingestion code in the repo.

## Source of Truth

Do you still have:

* Original source documents
* Chunking logic
* Embedding generation code
* Metadata enrichment logic

Or is Weaviate the only source of truth?

Answer: The original source documents and the generation logic still exist locally. Source files are in `scripts/vectorstore-generation/source-files`, and the chunking / metadata generation logic lives in `generate_document_objects.py` plus the Weaviate scripts.

Answer: Weaviate is not the only source of truth.

## Current Pain Points

What problems currently exist with Weaviate?

* Cost
* Complexity
* Performance
* Reliability
* Vendor lock-in
* Maintenance
* Other

Answer: The repo makes vendor lock-in, complexity, and maintenance overhead obvious. There is manual collection creation/upload, warmup logic, and multiple storage/schema paths to keep synchronized. Cost, reliability, and performance issues are not explicitly documented in code, so those remain unverified.

---

# 3. Lovable Dependency

## Current Usage

What is Lovable currently responsible for?

### Development

* Initial scaffolding only
* Ongoing code generation
* UI generation
* Component management

Answer: Initial scaffolding and UI generation, plus some dev-only tooling residue. The README says the GUI and edge functions were vibe coded using Lovable, and `vite.config.ts` still imports `lovable-tagger` in development.

### Infrastructure

* Hosting
* Deployments
* CI/CD
* Environment variable management
* Database setup
* Auth setup

Answer: There is no evidence that Lovable currently handles hosting, deployments, CI/CD, env vars, database setup, or auth in the repo.
- Added context:  I believe that I used Lovable to point to a custom domain on GoDaddy.
- NOTE: after searching my Vercel account, I can see that I was mistaken (Vercel was not used on this project). But can switch to that as a deployment / hosting provider if needed.

### Design System

* Styling system
* Tailwind setup
* UI components
* Theme management

Answer: The design system is local. The app uses Tailwind/shadcn in `src/components/*`, and Lovable only remains as a dev-only tagger plus branding in metadata and README links.

## Operational Independence

Can you currently:

### Local Development

* Run locally without Lovable?
* Build locally?
* Test locally?

Answer: Yes for local development. The repo supports `npm run dev`, `npm run build`, and `npm run lint`, and the edge functions include Deno-based test code.

### Deployment

* Push directly to GitHub?
* Deploy directly through Vercel?
* Deploy without touching Lovable?

Answer: Push directly to GitHub appears to be independent of Lovable because the code is already in a normal Git repo.

Answer: Deploying without touching Lovable is likely possible from a code standpoint, but the repo does not contain a Vercel config or GitHub Actions workflow, so the actual deployment path is TBD (easy to setup a Vercel deployment on existing account that hosts other sites).

### Code Ownership

* Is all source code fully available locally?
* Any generated code still tied to Lovable APIs/services?

Answer: All source code appears to be available locally.

Answer: There is no runtime Lovable API dependency in the app code. The remaining Lovable ties are the dev-only `lovable-tagger` plugin and Lovable branding/links in `index.html` and the README.

## Remaining Dependencies

Are any of the following still dependent on Lovable?

* Environment variables
* Build configuration
* Deployment hooks
* API endpoints
* Auth flows
* Database schema
* File storage
* Other

Answer: Environment variables are not Lovable-dependent. Build configuration still contains the dev-only `lovable-tagger` plugin import. No Lovable deployment hooks, API endpoints, auth flows, database schema, or file storage are present.

Answer: Other Lovable dependencies are branding and metadata only, such as the Lovable project links and social metadata in `index.html` and `README.md`.

## Goal

What does “fully migrated off Lovable” mean to you?

* No dependency whatsoever
* No billing relationship
* No deployment dependency
* No generated code dependency
* Other

Answer: For this repo, the practical definition should be no runtime, build, or deployment dependency on Lovable. If you want a weaker target, clarify whether the dev-only tagger and Lovable branding/metadata also need to be removed.

---

# 4. Current Repo Structure

## Repository Information

* Link to repo (optional)
* Monorepo or single app?
* Approximate repo size?

Answer: Single app repo, not a monorepo. The main top-level directories are `src/`, `supabase/`, `scripts/`, `public/`, and `docs/`. Repo size is not measured here.

## Folder Structure

Please paste the top-level folder structure.

Example:

```bash
src/
app/
components/
lib/
api/
scripts/
data/
```

Answer:

`src/`
`supabase/`
`scripts/`
`public/`
`docs/`
`venv/`
`.claude/`

## Package Dependencies

Please paste:

* package.json
* requirements.txt
* pyproject.toml
* or equivalent dependency files

Answer: See `package.json` for the Vite/React/Tailwind/shadcn/Supabase/LangChain frontend stack, and `requirements.txt` for the Python/LangChain/Weaviate/OpenAI/Chroma tooling. Those two files are the dependency sources actually used by the repo.

## Vector Store Code

Please identify or paste:

* Weaviate client setup
* Vector search logic
* Embedding generation logic
* Retrieval chain setup
* RAG orchestration code

Answer: Weaviate client setup lives in `scripts/vectorstore-generation/weaviate_connection.py`. Collection creation lives in `scripts/vectorstore-generation/weaviate_create_collection.py` and `scripts/vectorstore-generation/weaviate_generate_vectorstore.py`. Batch upload lives in `scripts/vectorstore-generation/weaviate_upload_to_vectorstore.py`. Weaviate query helpers live in `scripts/vectorstore-generation/weaviate_text_query.py`, `supabase/functions/weaviate-chat/index.ts`, and `supabase/functions/weaviate-warmup/index.ts`. Embedding generation and RAG orchestration live in `supabase/functions/chat/index.ts`, `supabase/functions/generate-vectorstore/index.ts`, and `scripts/vectorstore-generation/generate_vectorstore_chroma.py`.

## Environment Variables

Please list environment variable names only (no secrets).

Example:

```bash
OPENAI_API_KEY=
WEAVIATE_URL=
WEAVIATE_API_KEY=
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
```

Answer: `OPENAI_API_KEY`, `WEAVIATE_URL`, `WEAVIATE_API_KEY`, `WEAVIATE_REST_ENDPOINT`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`.

Answer: The frontend Supabase client is hardcoded to the project URL and anon key in `src/integrations/supabase/client.ts`, so there are currently no frontend env vars wired in.

## Deployment Configuration

Please share any relevant:

* vercel.json
* Docker files
* CI/CD configs
* GitHub Actions
* deployment scripts

Answer: No `vercel.json`, Dockerfile, or GitHub Actions workflow is present in the repo. The relevant config files are `vite.config.ts`, `supabase/config.toml`, `supabase/migrations/*`, and the `supabase/functions/*` tree.

## Current Build / Runtime Issues

Are there any existing issues with:

* Local development
* Build process
* Deployments
* Vector search
* Latency
* Memory usage
* Cold starts
* Auth
* Other

Answer: The main repo-level issues are configuration drift and deployment ambiguity. `supabase/functions/chat/index.ts` reads from the Supabase bucket `vectorstore`, while `supabase/functions/generate-vectorstore/index.ts` writes to `vectorstores`; the runtime Weaviate query path expects a `character` property that is not declared in the checked-in collection JSON; and the frontend invokes the `chat` function, but `supabase/config.toml` only lists `generate-vectorstore`, `weaviate-chat`, and `weaviate-warmup`.

Answer: Lovable branding and the dev-only `lovable-tagger` plugin are still present, so the repo is not fully cleanly detached from Lovable even though the runtime itself does not call Lovable services.

# 5. Desired End State

What do you want after migration?

OBJECTIVES:
- My main objective here is to keep the site up without having to pay the Weaviate fees which are ~$150 / month.
- My secondary objective is completing this in the least amount of time possible (no more than 4 hours).

Preferrably, Option A if it aligns with objectives above.

-----OPTIONS BELOW FOR REFERENCE-----

Choose one:

Option A — Simplest / Lowest Maintenance

Move vectors into:

Supabase pgvector

Pros:

one vendor
simpler stack
cheap
good enough for many RAG apps

Cons:

less sophisticated retrieval at scale

Option B — Best Retrieval / AI Native

Move to:

Pinecone
Qdrant
Chroma

Pros:

purpose-built vector DBs
better ANN performance/features

Cons:

another vendor
Option C — Fully Self Hosted

Move to:

Postgres + pgvector
self-hosted Qdrant

Pros:

full control
lowest long-term cost

Cons:

operational burden