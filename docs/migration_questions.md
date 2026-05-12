# LLM / RAG App Migration Discovery Questions

## 1. Current Architecture

### Frontend

* What frontend framework is the application using?

  * Next.js (App Router?)
  * Vite React
  * Other

* Is the frontend:

  * SPA
  * SSR
  * Hybrid

### Backend / Runtime

* Where does backend logic run?

  * Vercel API routes
  * Edge functions
  * Separate backend service
  * Python backend
  * Other

* Are there any background jobs or schedulers?

  * Cron jobs
  * Queues
  * Workers
  * Serverless scheduled tasks

### LLM Providers

* Which LLM providers are currently used?

  * OpenAI
  * Anthropic
  * Azure OpenAI
  * Other

* Which specific models are used?

### Embeddings

* Which embedding model is currently used?
* What embedding dimensions are stored in Weaviate?

### RAG Framework

* Which framework is used?

  * LangChain
  * LlamaIndex
  * Custom retrieval pipeline
  * Other

### Authentication / User Management

* Is there user authentication?
* Which auth provider is used?

  * Supabase Auth
  * Clerk
  * Auth0
  * Custom
  * Other

### Database / Persistence

* Besides Weaviate, what databases are used?

  * Supabase Postgres
  * Firebase
  * MongoDB
  * Other

### Hosting / Infrastructure

* What services are currently involved?

  * Vercel
  * Weaviate
  * Lovable
  * Supabase
  * GitHub
  * Cloudflare
  * Other

---

# 2. Weaviate Usage

## Weaviate Hosting

* Is Weaviate:

  * Cloud hosted
  * Self hosted
  * Embedded/local

* Which pricing tier or cluster size?

## Data Scale

* Approximately how many vector objects/documents exist?
* Approximately how many source documents?
* Average chunk size?
* Average chunks per document?

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

## Retrieval Features Used

Which Weaviate features are currently used?

### Search

* Pure vector similarity
* Hybrid search (BM25 + vector)
* Keyword search
* Metadata filtering
* Semantic reranking

### Advanced Features

* Multi-tenancy
* Named vectors
* Cross references
* Generative modules
* Agents/modules
* Custom vectorizers

## Ingestion Pipeline

* How are documents ingested?

  * Python scripts
  * LangChain loaders
  * Manual upload
  * Background jobs
  * API endpoints
  * Webhooks

* Is ingestion:

  * Manual
  * Automated
  * Incremental
  * Real-time

## Source of Truth

Do you still have:

* Original source documents
* Chunking logic
* Embedding generation code
* Metadata enrichment logic

Or is Weaviate the only source of truth?

## Current Pain Points

What problems currently exist with Weaviate?

* Cost
* Complexity
* Performance
* Reliability
* Vendor lock-in
* Maintenance
* Other

---

# 3. Lovable Dependency

## Current Usage

What is Lovable currently responsible for?

### Development

* Initial scaffolding only
* Ongoing code generation
* UI generation
* Component management

### Infrastructure

* Hosting
* Deployments
* CI/CD
* Environment variable management
* Database setup
* Auth setup

### Design System

* Styling system
* Tailwind setup
* UI components
* Theme management

## Operational Independence

Can you currently:

### Local Development

* Run locally without Lovable?
* Build locally?
* Test locally?

### Deployment

* Push directly to GitHub?
* Deploy directly through Vercel?
* Deploy without touching Lovable?

### Code Ownership

* Is all source code fully available locally?
* Any generated code still tied to Lovable APIs/services?

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

## Goal

What does “fully migrated off Lovable” mean to you?

* No dependency whatsoever
* No billing relationship
* No deployment dependency
* No generated code dependency
* Other

---

# 4. Current Repo Structure

## Repository Information

* Link to repo (optional)
* Monorepo or single app?
* Approximate repo size?

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

## Package Dependencies

Please paste:

* package.json
* requirements.txt
* pyproject.toml
* or equivalent dependency files

## Vector Store Code

Please identify or paste:

* Weaviate client setup
* Vector search logic
* Embedding generation logic
* Retrieval chain setup
* RAG orchestration code

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

## Deployment Configuration

Please share any relevant:

* vercel.json
* Docker files
* CI/CD configs
* GitHub Actions
* deployment scripts

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
