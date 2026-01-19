# NovellaForge - Studio d'ecriture long format

NovellaForge accompagne les auteurs francophones pour construire des romans longs format.
Le systeme combine une application web, un backend API et un pipeline IA oriente roman.

## Architecture technique
- Frontend web: Next.js 15, TypeScript, Tailwind CSS.
- Backend API: FastAPI, Python 3.11, SQLAlchemy async.
- Donnees: PostgreSQL (projets, documents, metadata).
- Cache/queue: Redis, Celery.
- Vector store: Qdrant pour la RAG documentaire.
- Memoire: Neo4j (graphe de continuites) + ChromaDB (style/ton).
- IA: DeepSeek + LangGraph + LangChain.
- Uploads: stockage local via volume Docker.

## Fonctionnalites principales
### Roman long format
- Generation de concept (premisse, tonalite, tropes, orientation emotionnelle).
- Plan de roman (arcs et chapitres) editable.
- Generation de chapitres avec critique et validation.
- Rewrites guides par focus (pacing, romance, tension, etc.).

### Memoire & coherence
- Extraction automatique des faits (personnages, lieux, relations, evenements).
- Stockage optionnel dans Neo4j (graphe) et ChromaDB (style).
- Bloc de continuite injecte dans chaque chapitre.

### Projets & contexte
- Creation, mise a jour, suppression avec confirmation.
- Genre requis, objectifs de longueur et instructions de projet.
- Import de documents (txt, docx, pdf, md) pour la RAG.

## Flux long format (chapitre)
1. Creer un projet avec un genre.
2. Generer ou saisir le concept, puis le plan.
3. Lancer la generation d'un chapitre.
4. Lire la critique et approuver le chapitre.
5. La memoire est mise a jour automatiquement.

## API (principaux endpoints)
### Auth
- POST /api/v1/auth/register
- POST /api/v1/auth/login
- GET /api/v1/auth/me

### Projets
- GET /api/v1/projects
- POST /api/v1/projects
- PUT /api/v1/projects/{id}
- POST /api/v1/projects/{id}/delete
- GET /api/v1/projects/{id}/download

### Concept & plan
- GET /api/v1/projects/{id}/concept
- POST /api/v1/projects/{id}/concept/generate
- PUT /api/v1/projects/{id}/concept
- GET /api/v1/projects/{id}/plan
- POST /api/v1/projects/{id}/plan/generate
- PUT /api/v1/projects/{id}/plan

### Writing pipeline
- POST /api/v1/writing/index
- POST /api/v1/writing/generate-chapter
- POST /api/v1/writing/approve-chapter

### Upload & documents
- POST /api/v1/upload
- GET /api/v1/documents?project_id=...

## Demarrage rapide (Docker)
1. Copier `.env.example` vers `.env`
2. Renseigner `DEEPSEEK_API_KEY` et `SECRET_KEY`
3. Lancer `docker-compose up -d`

Acces:
- Web (Docker): http://localhost:3020
- API: http://localhost:8002/api/v1
- Docs API: http://localhost:8002/api/docs
- Health: http://localhost:8002/health

## Configuration (.env)
Variables cles:
- DEEPSEEK_API_KEY, DEEPSEEK_API_BASE, DEEPSEEK_MODEL
- SECRET_KEY
- DATABASE_URL / POSTGRES_*
- REDIS_URL
- QDRANT_URL, QDRANT_COLLECTION_NAME
- NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE
- CHROMA_HOST, CHROMA_PORT, CHROMA_COLLECTION_PREFIX
- CHAT_MAX_TOKENS, DEEPSEEK_TIMEOUT

## Chapter generation performance tuning
Optimisations applied in the writing pipeline:
- Plan: uses deepseek-chat by default, optional reasoning only on early/critical chapters, and skips plan LLM when scene beats already exist.
- Write: parallel beat generation, per-beat token caps, partial revision on last beat, early stop in sequential mode.
- Validation: single LLM call for coherence + plot points, graph checks run in parallel, optional fallback validation disabled by default.
- Context: memory context cache, prompt truncation for memory/style/RAG/story bible to reduce token load.
- Logs: [PERF] timings for nodes and LLM calls.

Tuning knobs (see .env.example):
- MAX_REVISIONS, QUALITY_GATE_COHERENCE_THRESHOLD, QUALITY_GATE_SCORE_THRESHOLD
- PLAN_REASONING_*
- WRITE_PARALLEL_BEATS, WRITE_PARTIAL_REVISION, WRITE_PREVIOUS_BEATS_MAX_CHARS
- WRITE_EARLY_STOP_RATIO, WRITE_MIN_BEAT_WORDS, WRITE_TOKENS_PER_WORD, WRITE_MAX_TOKENS
- MEMORY_CONTEXT_MAX_CHARS, RAG_CONTEXT_MAX_CHARS, STYLE_CONTEXT_MAX_CHARS, STORY_BIBLE_MAX_CHARS
- VALIDATION_MAX_CHARS, VALIDATION_ALLOW_FALLBACK, CRITIC_MAX_CHARS

## Tests
Backend: pytest (voir `backend/tests`).
