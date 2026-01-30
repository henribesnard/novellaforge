# NovellaForge - Studio d'ecriture long format

NovellaForge accompagne les auteurs francophones pour construire des romans longs format.
Le systeme combine une application web, un backend API et un pipeline IA oriente roman.

## Architecture technique
- Frontend web: Next.js 15, TypeScript, Tailwind CSS, architecture feature-based.
- Backend API: FastAPI, Python 3.11, SQLAlchemy async.
- Donnees: PostgreSQL (projets, documents, metadata).
- Cache/queue: Redis, Celery (queues prioritaires).
- Vector store: Qdrant pour la RAG documentaire.
- Memoire: Neo4j (graphe de continuites) + ChromaDB (style/ton).
- IA: DeepSeek + LangGraph + LangChain.
- Uploads: stockage local via volume Docker.
- Streaming: WebSocket pour generation temps reel.
- Audio: Web Speech API (TTS navigateur) avec sanitisation markdown.

## Structure du projet

```
NovellaForge/
  backend/
    app/
      api/v1/          # Endpoints FastAPI
      core/            # Config, securite, Celery
      db/              # Session async, base SQLAlchemy
      models/          # Modeles ORM (Project, Document, Character, ...)
      schemas/         # Schemas Pydantic
      services/        # Logique metier (writing_pipeline, memory, RAG, ...)
    scripts/           # Scripts utilitaires (nettoyage, migration)
    tests/             # Tests pytest
  frontend/
    src/
      app/             # Pages Next.js (App Router)
      features/        # Modules fonctionnels
        audio/         # Lecteur TTS (ChapterAudioPlayer, controles, mini-player)
        dashboard/     # Statistiques, vue d'ensemble
        editor/        # Editeur de chapitre (TipTap)
        projects/      # Carte projet, gestion chapitres
        chat/          # Chat assistant IA
      hooks/           # Hooks React (useSpeechSynthesis, useAudioKeyboard)
      lib/             # Utilitaires (api-client, tts-sanitizer, utils)
      components/ui/   # Composants generiques (Card, Button, Badge, ...)
      types/           # Types TypeScript partages
  docker-compose.yml   # Infrastructure complete (PostgreSQL, Redis, Qdrant, Neo4j, Chroma)
```

## Fonctionnalites principales

### Roman long format
- Generation de concept (premisse, tonalite, tropes, orientation emotionnelle).
- Plan de roman (arcs et chapitres) editable.
- Generation de chapitres avec critique et validation.
- Rewrites guides par focus (pacing, romance, tension, etc.).

### Lecture audio (TTS)
- Lecteur audio integre par chapitre via Web Speech API.
- Sanitisation automatique du markdown avant lecture (suppression `**`, `*`, `#`, `---`, etc.).
- Controles: lecture/pause, stop, avance/recul rapide, vitesse, choix de voix.
- Barre de progression avec seek.
- Raccourcis clavier: Espace (lecture/pause), Fleches (avancer/reculer), Echap (stop).
- Mini-player compact dans l'en-tete du chapitre.

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
5. Ecouter le chapitre via le lecteur audio integre.
6. La memoire est mise a jour automatiquement.

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
- POST /api/v1/writing/pregenerate-plans
- WS /api/v1/writing/ws/generate/{project_id}

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

## Scripts utilitaires

### Nettoyage markdown des chapitres
Supprime les artefacts markdown (`**`, `*`, `#`, `---`, etc.) du contenu des chapitres existants en base.

```bash
cd backend
python -m scripts.clean_chapter_markdown
```

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

## Performance et optimisations

### Temps de generation
- Temps initial: ~10 minutes par chapitre
- Temps optimise: ~3-4 minutes par chapitre
- Amelioration: 60-65%

### Optimisations implementees

#### Cache distribue (Redis)
- Cache memoire context (TTL 30 min)
- Cache resultats RAG (TTL 1h)
- Cache Neo4j contradictions (TTL 10 min)

#### Streaming LLM
- Generation token par token via `chat_stream()`
- WebSocket `/ws/generate/{project_id}` pour feedback temps reel

#### Generation distribuee (Celery)
- Beats generes en parallele sur workers dedies
- Queues prioritaires: `beats_high`, `generation_medium`, `maintenance_low`
- Activer avec `WRITE_DISTRIBUTED_BEATS=true`

#### Pre-generation des plans
- Endpoint `POST /pregenerate-plans` pour preparer N plans en avance
- Les plans sont reutilises automatiquement lors de la generation

#### Truncation intelligente
- Priorisation: personnages mentionnes > evenements recents > relations > threads ouverts
- Reduction du contexte sans perte de coherence

#### Sanitisation TTS
- Frontend: fonction `sanitizeForTTS()` avec 16 regles regex appliquees avant la synthese vocale
- Backend: prompt LLM instruit de generer du texte narratif sans markdown

### Workers Celery

```bash
# Worker haute priorite (beats)
celery -A app.core.celery_app worker -Q beats_high --concurrency=4 -n beats@%h

# Worker generation (chapitres/plans)
celery -A app.core.celery_app worker -Q generation_medium --concurrency=2 -n gen@%h

# Worker maintenance
celery -A app.core.celery_app worker -Q maintenance_low --concurrency=1 -n maint@%h

# Ou tous ensemble
celery -A app.core.celery_app worker -Q beats_high,generation_medium,maintenance_low,celery --concurrency=4
```

### Variables de configuration

#### Performance
```env
WRITE_PARALLEL_BEATS=true
WRITE_DISTRIBUTED_BEATS=false  # true si workers Celery actifs
WRITE_PARTIAL_REVISION=true
MAX_REVISIONS=2
QUALITY_GATE_COHERENCE_THRESHOLD=6.0
RAG_PRELOAD_MODELS=true        # pre-charge les embeddings au demarrage
CONSISTENCY_ANALYST_TIMEOUT=60  # timeout analyste de coherence (secondes)
```

#### Tokens et limites
```env
WRITE_TOKENS_PER_WORD=1.5
WRITE_MAX_TOKENS=1800
WRITE_MIN_BEAT_WORDS=120
WRITE_EARLY_STOP_RATIO=1.05
```

#### Contexte
```env
MEMORY_CONTEXT_MAX_CHARS=4000
RAG_CONTEXT_MAX_CHARS=4000
STYLE_CONTEXT_MAX_CHARS=2000
STORY_BIBLE_MAX_CHARS=2500
VALIDATION_MAX_CHARS=12000
```

#### Planification
```env
PLAN_REASONING_ENABLED=true
PLAN_REASONING_FIRST_CHAPTERS=3
PLAN_REASONING_INTERVAL=10
```

### Workflow optimal

1. Pre-generer les plans:
```http
POST /api/v1/writing/pregenerate-plans
{"project_id": "...", "count": 5}
```

2. Generer via API standard:
```http
POST /api/v1/writing/generate-chapter
{"project_id": "...", "chapter_index": 1}
```

3. Ou via WebSocket (temps reel):
```javascript
const ws = new WebSocket(`ws://host/api/v1/writing/ws/generate/${projectId}`);
ws.send(JSON.stringify({token: "jwt", chapter_index: 1}));
ws.onmessage = (e) => console.log(JSON.parse(e.data));
```

## Tests
- Backend: `pytest` (voir `backend/tests`)
- Frontend: `vitest` (voir `frontend/src/lib/__tests__`)
