# Prompt d'Implémentation - Système de Cohérence NovellaForge

## Contexte du Projet

Vous êtes un agent de coding expert travaillant sur **NovellaForge**, une plateforme de génération de romans longs format feuilleton (pay-to-read) assistée par IA.

Le système actuel génère des chapitres individuels mais manque de mécanismes robustes pour maintenir la **cohérence narrative** sur 100+ chapitres. Votre mission est d'implémenter un système complet de gestion de cohérence basé sur le plan détaillé dans `COHERENCE_IMPLEMENTATION_PLAN.md`.

### Architecture Actuelle

**Backend:**
- FastAPI (Python 3.11+)
- PostgreSQL avec SQLAlchemy (async)
- Qdrant (RAG vectoriel)
- Neo4j (optionnel, graphe de relations)
- ChromaDB (optionnel, mémoire de style)
- Celery (tâches async)
- LangGraph (orchestration pipeline d'écriture)
- DeepSeek API (LLM)

**Structure:**
```
backend/
├── app/
│   ├── api/v1/endpoints/     # FastAPI routes
│   ├── models/               # SQLAlchemy models
│   ├── schemas/              # Pydantic schemas
│   ├── services/             # Business logic
│   │   ├── agents/          # Specialized AI agents
│   │   ├── memory_service.py
│   │   ├── writing_pipeline.py
│   │   ├── rag_service.py
│   │   └── ...
│   ├── tasks/               # Celery tasks
│   └── core/                # Config, security
└── tests/                   # Unit & integration tests
```

### Fichiers Clés à Étudier

Avant de commencer l'implémentation, **lisez attentivement** ces fichiers pour comprendre le système existant:

1. **`COHERENCE_IMPLEMENTATION_PLAN.md`** - Plan complet d'implémentation (VOTRE GUIDE PRINCIPAL)
2. `backend/app/services/memory_service.py` - Gestion mémoire et continuité
3. `backend/app/services/writing_pipeline.py` - Pipeline de génération (LangGraph)
4. `backend/app/services/context_service.py` - Construction du contexte projet
5. `backend/app/services/rag_service.py` - Indexation et récupération vectorielle
6. `backend/app/services/novella_service.py` - Génération concept et plan
7. `backend/app/models/project.py` - Modèle de données projet
8. `backend/app/models/document.py` - Modèle de données document/chapitre

---

## Instructions Générales d'Implémentation

### 1. Principe de Travail Méthodique

**IMPORTANT:** Ne commencez JAMAIS à coder sans avoir:
- ✅ Lu le `COHERENCE_IMPLEMENTATION_PLAN.md` en entier
- ✅ Compris l'état actuel du code (section "État des Lieux")
- ✅ Identifié la priorité à implémenter (0, 1, ou 2)
- ✅ Lu les fichiers concernés par cette priorité

### 2. Workflow d'Implémentation par Priorité

Pour chaque priorité (ex: Priority 0.1, 0.2, etc.):

#### Phase 1: Analyse (15 min)
1. Lire la section correspondante dans `COHERENCE_IMPLEMENTATION_PLAN.md`
2. Identifier les fichiers impactés listés
3. Lire le code actuel de ces fichiers
4. Comprendre le "Problème actuel" décrit
5. Noter les "Critères d'acceptation" à satisfaire

#### Phase 2: Planification (10 min)
1. Décomposer l'amélioration en sous-tâches (3-8 tasks max)
2. Ordonner les sous-tâches par dépendances
3. Identifier les schémas Pydantic à créer/modifier
4. Identifier les tests unitaires nécessaires
5. **Créer une checklist de validation** avant de coder

#### Phase 3: Implémentation (60-120 min)
1. **Commencer TOUJOURS par les schémas Pydantic** (si applicable)
2. Implémenter les sous-tâches dans l'ordre
3. **Après chaque fichier modifié:**
   - Vérifier la syntaxe Python (pas d'erreurs)
   - Vérifier les imports
   - Ajouter des docstrings claires
   - Ajouter des logs pertinents (`logger.info`, `logger.debug`)
4. **Respecter le style de code existant** (conventions, naming)
5. **Ne jamais supprimer de code sans raison** - commenter si uncertain
6. **Utiliser les exemples du plan** comme référence

#### Phase 4: Tests (30-60 min)
1. Écrire les tests unitaires listés dans "Critères d'acceptation"
2. Écrire au moins 1 test d'intégration si applicable
3. **Lancer les tests:** `pytest backend/tests/`
4. Corriger les erreurs jusqu'à ce que tous les tests passent
5. Vérifier coverage: `pytest --cov=app`

#### Phase 5: Validation (15 min)
1. Relire les "Critères d'acceptation" du plan
2. Cocher chaque critère comme satisfait
3. Vérifier que le code existant n'est pas cassé
4. Documenter les changements (si API modifiée)
5. Commit avec message clair: `feat(coherence): implement Priority X.Y - [description]`

### 3. Ordre d'Implémentation STRICT

**NE PAS implémenter dans le désordre.** Suivez cet ordre:

```
Sprint 1-2: Priority 0.1 + 0.2
  ├─ 0.1.1: Enrichir schéma extraction (memory_service.py)
  ├─ 0.1.2: Réécrire build_context_block() (memory_service.py)
  ├─ 0.1.3: Injecter contexte enrichi dans prompts (writing_pipeline.py)
  ├─ 0.1.4: Tests extraction enrichie
  ├─ 0.2.1: Créer validate_continuity() (writing_pipeline.py)
  ├─ 0.2.2: Modifier _build_graph() pour ajouter node
  ├─ 0.2.3: Modifier _quality_gate() pour bloquer
  ├─ 0.2.4: Tests validation
  └─ CHECKPOINT: Valider Priority 0.1 + 0.2 complètes

Sprint 3: Priority 0.3 + 0.4
  ├─ 0.3.1: Auto-update RAG dans approve_chapter()
  ├─ 0.3.2: Hook update dans documents.py endpoint
  ├─ 0.3.3: Créer aupdate_document() dans rag_service.py
  ├─ 0.3.4: Endpoint /coherence-health
  ├─ 0.4.1: Tests mémoire enrichie
  ├─ 0.4.2: Tests validation cohérence
  ├─ 0.4.3: Tests auto-update
  └─ CHECKPOINT: Valider Priority 0 COMPLÈTE

Sprint 4: Priority 1.1
  ├─ 1.1.1: Créer schemas/story_bible.py
  ├─ 1.1.2: Endpoints CRUD bible (projects.py)
  ├─ 1.1.3: Modifier context_service.py
  ├─ 1.1.4: Créer _build_bible_context_block()
  ├─ 1.1.5: Injecter dans prompts
  └─ CHECKPOINT: Valider Priority 1.1

Sprint 5: Priority 1.2
  ├─ 1.2.1: Enrichir generate_plan() (novella_service.py)
  ├─ 1.2.2: Créer _validate_plot_points()
  ├─ 1.2.3: Intégrer dans validate_continuity()
  ├─ 1.2.4: Modifier quality_gate()
  └─ CHECKPOINT: Valider Priority 1.2

Sprint 6: Priority 1.3
  ├─ 1.3.1: Créer services/agents/consistency_analyst.py
  ├─ 1.3.2: Intégrer dans agent_factory.py
  ├─ 1.3.3: Endpoints API (agents.py)
  ├─ 1.3.4: Tests agent
  └─ CHECKPOINT: Valider Priority 1.3

Sprint 7: Priority 2.1 (Neo4j avancé)
Sprint 8: Priority 2.2 (Contradiction workflow)
Sprint 9: Priority 2.3 (Maintenance batch)
```

### 4. Contraintes et Règles STRICTES

#### Compatibilité
- ✅ **Backward compatibility:** Code existant doit continuer à fonctionner
- ✅ **Graceful degradation:** Si Neo4j/ChromaDB absents, système fonctionne (mode dégradé)
- ✅ **Pas de breaking changes** sur API publique sans version

#### Code Quality
- ✅ **Type hints partout:** Toutes les fonctions doivent avoir type annotations
- ✅ **Docstrings:** Format Google-style pour toutes les classes/fonctions publiques
- ✅ **Logging:** Utiliser `logger` (pas de `print()`)
- ✅ **Error handling:** Try/except avec messages clairs
- ✅ **Async/await:** Respecter async pattern existant

#### Prompts LLM
- ✅ **Tous en français** pour génération de contenu
- ✅ **Clés metadata:** snake_case ASCII (ex: `continuity_alerts` pas `continuitéAlertes`)
- ✅ **Pas de silent fallback:** Logger et surfacer les erreurs

#### Performance
- ✅ **Éviter N+1 queries:** Utiliser select avec joinedload si nécessaire
- ✅ **Caching:** Réutiliser contexte déjà chargé
- ✅ **Batch processing:** Si >10 items, traiter en batch

#### Tests
- ✅ **Minimum 80% coverage** sur nouveau code
- ✅ **Tests unitaires** pour chaque nouvelle méthode
- ✅ **Tests d'intégration** pour workflows complets
- ✅ **Fixtures réutilisables** dans conftest.py

---

## Guide d'Implémentation par Priorité

### Priority 0.1: Enrichir Mémoire et Contexte

**Objectif:** Passer d'un contexte minimal ("Alice, Bob") à un contexte riche (200+ mots avec détails).

**Checklist AVANT de coder:**
- [ ] J'ai lu `backend/app/services/memory_service.py` en entier
- [ ] J'ai compris la méthode `extract_facts()` actuelle (ligne 45-61)
- [ ] J'ai compris `build_context_block()` actuelle (ligne 86-98)
- [ ] J'ai lu le nouveau schéma JSON enrichi dans le plan
- [ ] J'ai identifié où injecter le contexte enrichi (writing_pipeline.py ligne 238)

**Étapes d'implémentation:**

1. **Modifier `extract_facts()` (memory_service.py):**
   ```python
   # Nouveau prompt avec schéma enrichi (voir plan section Priority 0.1)
   # Augmenter window: 6000 → 10000 chars
   # Si > 10000, extraire en 2 passes (début + fin) et merger
   ```

2. **Modifier `merge_facts()` pour gérer nouveaux champs:**
   ```python
   # Ajouter merge de: motivations, traits, goals, arc_stage, last_seen_chapter
   # Pour relations: start_chapter, current_state, evolution
   # Pour events: chapter_index, time_reference, impact, unresolved_threads
   ```

3. **Réécrire `build_context_block()`:**
   ```python
   # Format détaillé avec 3-5 fields par entity (voir exemple dans plan)
   # Minimum 200 mots de contexte
   # Structure: Characters (détaillé) / Locations / Relations / Events
   ```

4. **Ajouter `_merge_with_temporal_tracking()` helper:**
   ```python
   # Pour garder historique des changements (ex: status_history)
   ```

5. **Vérifier injection dans writing_pipeline.py:**
   ```python
   # Ligne 238: memory_context doit utiliser nouveau build_context_block()
   # Ajouter logs: logger.debug(f"Memory context: {memory_context[:500]}...")
   ```

6. **Tests (test_memory_service.py):**
   ```python
   async def test_extract_facts_enriched_schema()
   async def test_merge_facts_temporal_tracking()
   async def test_build_context_block_detailed()
   # Voir exemples complets dans plan section 0.4
   ```

**Critères d'acceptation (TOUS doivent être ✅):**
- [ ] Extraction JSON contient min 5 champs par character
- [ ] Context block fait min 200 mots (vs ~20 actuellement)
- [ ] Logs montrent contexte complet injecté dans prompts
- [ ] Tests unitaires passent (pytest backend/tests/test_memory_service.py)
- [ ] Coverage >= 80% sur memory_service.py

**Fichiers modifiés:**
- `backend/app/services/memory_service.py` (~150 lignes modifiées)
- `backend/tests/test_memory_service.py` (~100 lignes ajoutées)

---

### Priority 0.2: Validation Cohérence Stricte

**Objectif:** Bloquer génération si contradictions graves (ex: personnage mort qui parle).

**Checklist AVANT de coder:**
- [ ] J'ai compris le graph LangGraph actuel (writing_pipeline.py ligne 74-96)
- [ ] J'ai compris le `_quality_gate()` actuel (ligne 341-350)
- [ ] J'ai lu l'exemple de prompt de validation dans le plan
- [ ] J'ai compris comment ajouter un node LangGraph

**Étapes d'implémentation:**

1. **Créer méthode `validate_continuity()` (writing_pipeline.py):**
   ```python
   async def validate_continuity(self, state: NovelState) -> Dict[str, Any]:
       # 1. Extraire entités du draft
       # 2. Comparer avec memory (statuts cohérents?)
       # 3. Comparer avec RAG chunks (changements expliqués?)
       # 4. Comparer avec plan (plot points couverts?)
       # 5. Appeler LLM avec prompt de validation détaillé
       # 6. Parser réponse JSON
       # 7. Retourner {continuity_validation: {...}}
   ```

2. **Modifier `_build_graph()` pour ajouter node:**
   ```python
   # Ligne 75-96
   graph.add_node("validate_continuity", self.validate_continuity)
   graph.add_edge("write_chapter", "validate_continuity")
   graph.add_edge("validate_continuity", "critic")
   ```

3. **Modifier `_quality_gate()` pour bloquer:**
   ```python
   # Ligne 341-350
   # Ajouter vérification:
   validation = state.get("continuity_validation", {})
   if validation.get("blocking", False):
       return "revise"
   if validation.get("coherence_score", 0) < 7:
       return "revise"
   # ... critères existants ...
   ```

4. **Modifier `_persist_draft()` pour stocker validation:**
   ```python
   # Ligne 429-466
   metadata = {
       # ... champs existants ...
       "continuity_validation_history": [
           state.get("continuity_validation")
       ]
   }
   ```

5. **Créer schema Pydantic (schemas/writing.py):**
   ```python
   class ContinuityValidation(BaseModel):
       severe_issues: List[Dict] = []
       minor_issues: List[Dict] = []
       coherence_score: float = 0.0
       blocking: bool = False
   ```

6. **Tests (test_writing_pipeline.py):**
   ```python
   async def test_validate_continuity_detects_contradictions()
   async def test_quality_gate_blocks_on_coherence_issues()
   async def test_quality_gate_passes_with_good_coherence()
   ```

**Critères d'acceptation:**
- [ ] Contradictions sévères déclenchent révision automatique
- [ ] `blocking: true` empêche passage à "done" même si score élevé
- [ ] Validation history stockée dans metadata
- [ ] API retourne detailed continuity_alerts
- [ ] Tests passent

**Fichiers modifiés:**
- `backend/app/services/writing_pipeline.py` (~200 lignes ajoutées)
- `backend/app/schemas/writing.py` (~30 lignes ajoutées)
- `backend/tests/test_writing_pipeline.py` (~150 lignes ajoutées)

---

### Priority 0.3: Auto-Update RAG et Mémoire

**Objectif:** Mise à jour automatique lors de approve_chapter() et édition manuelle.

**Checklist AVANT de coder:**
- [ ] J'ai compris `approve_chapter()` actuelle (writing_pipeline.py ligne 375-427)
- [ ] J'ai compris endpoint `update_document()` (endpoints/documents.py)
- [ ] J'ai compris `aindex_documents()` (rag_service.py ligne 123-130)

**Étapes d'implémentation:**

1. **Modifier `approve_chapter()` (writing_pipeline.py):**
   ```python
   # Ligne 421, APRÈS storage Neo4j/ChromaDB, AJOUTER:
   await self.rag_service.aindex_documents(
       document.project_id,
       [document],
       clear_existing=False  # Incrémental
   )

   return {
       "document_id": str(document.id),
       "status": "approved",
       "summary": summary,
       "rag_updated": True  # NOUVEAU
   }
   ```

2. **Hook dans `update_document()` (endpoints/documents.py):**
   ```python
   # Après ligne de update, AJOUTER:
   if (updated_doc.document_type == DocumentType.CHAPTER and
       updated_doc.document_metadata.get("status") == "approved"):

       # Refresh continuity
       memory_service = MemoryService()
       facts = await memory_service.extract_facts(updated_doc.content or "")

       # Update project metadata
       project = await db.get(Project, updated_doc.project_id)
       if project:
           project_metadata = project.project_metadata or {}
           project_metadata = memory_service.merge_facts(project_metadata, facts)
           project.project_metadata = project_metadata
           await db.commit()

       # Update RAG
       rag_service = RagService()
       await rag_service.aindex_documents(
           updated_doc.project_id,
           [updated_doc],
           clear_existing=False
       )
   ```

3. **Ajouter `aupdate_document()` (rag_service.py):**
   ```python
   async def aupdate_document(
       self, project_id: UUID, document: Document
   ) -> int:
       """Update a single document's vectors."""
       # 1. Delete old vectors for this document_id
       # 2. Reindex just this document
       # Voir implémentation complète dans plan
   ```

4. **Endpoint `/coherence-health` (endpoints/projects.py):**
   ```python
   @router.get("/{project_id}/coherence-health")
   async def get_coherence_health(project_id: UUID, ...):
       # Retourner: last_memory_update, rag_document_count
       # Compter documents dans Qdrant
       # Retourner last_updated from metadata
   ```

5. **Tests:**
   ```python
   async def test_approve_chapter_updates_rag()
   async def test_manual_edit_updates_memory()
   ```

**Critères d'acceptation:**
- [ ] Chapitre approuvé → immédiatement searchable dans RAG
- [ ] Édition manuelle → memory et RAG mis à jour
- [ ] Suppression → vectors supprimés
- [ ] Logs montrent chaque update
- [ ] Endpoint `/coherence-health` fonctionne

**Fichiers modifiés:**
- `backend/app/services/writing_pipeline.py` (~10 lignes)
- `backend/app/api/v1/endpoints/documents.py` (~30 lignes)
- `backend/app/services/rag_service.py` (~30 lignes)
- `backend/app/api/v1/endpoints/projects.py` (~20 lignes)
- `backend/tests/test_writing_pipeline.py` (~50 lignes)

---

### Priority 1.1: Story Bible Structurée

**Objectif:** Transformer metadata JSONB non structuré en Story Bible avec schéma clair.

**Checklist AVANT de coder:**
- [ ] J'ai lu le schéma Story Bible complet dans le plan (section 1.1)
- [ ] J'ai compris comment créer endpoints CRUD FastAPI
- [ ] J'ai compris context_service.py (ligne 14-134)

**Étapes d'implémentation:**

1. **Créer `schemas/story_bible.py` (NOUVEAU fichier):**
   ```python
   # Copier schémas Pydantic du plan:
   class WorldRule(BaseModel): ...
   class TimelineEvent(BaseModel): ...
   class GlossaryTerm(BaseModel): ...
   class EstablishedFact(BaseModel): ...
   class StoryBible(BaseModel): ...
   ```

2. **Endpoints CRUD (endpoints/projects.py):**
   ```python
   @router.get("/{project_id}/story-bible")
   @router.put("/{project_id}/story-bible/world-rules")
   @router.put("/{project_id}/story-bible/timeline")
   @router.post("/{project_id}/story-bible/validate-draft")
   # Implémentations complètes dans plan
   ```

3. **Modifier `build_project_context()` (context_service.py):**
   ```python
   # Ligne 92-134, AJOUTER:
   story_bible = project_metadata.get("story_bible", {})

   return {
       "project": {...},
       "story_bible": story_bible,  # NOUVEAU
       "constraints": ...,
       # ... reste ...
   }
   ```

4. **Créer `_build_bible_context_block()` (writing_pipeline.py):**
   ```python
   def _build_bible_context_block(self, bible: Dict[str, Any]) -> str:
       # Format world_rules, timeline, established_facts
       # Retourner string de 100-300 mots
       # Voir implémentation dans plan
   ```

5. **Injecter dans prompts (write_chapter(), ligne 224):**
   ```python
   story_bible = state.get("project_context", {}).get("story_bible", {})
   bible_block = self._build_bible_context_block(story_bible)

   base_prompt = f"""
   ...
   STORY BIBLE (RÈGLES CRITIQUES):
   {bible_block}

   CONTEXTE MÉMOIRE:
   {state.get('memory_context', '')}
   ...
   """
   ```

6. **Tests:**
   - Test endpoints CRUD
   - Test injection dans contexte
   - Test validation de draft contre bible

**Critères d'acceptation:**
- [ ] GET /story-bible retourne schéma structuré
- [ ] PUT endpoints fonctionnent
- [ ] Story bible injectée dans prompts (logs)
- [ ] Validation détecte violations

**Fichiers créés/modifiés:**
- `backend/app/schemas/story_bible.py` (NOUVEAU, ~150 lignes)
- `backend/app/api/v1/endpoints/projects.py` (~100 lignes ajoutées)
- `backend/app/services/context_service.py` (~10 lignes)
- `backend/app/services/writing_pipeline.py` (~50 lignes)

---

### Priorities 1.2, 1.3, 2.1, 2.2, 2.3

**Pour ces priorités:** Suivre le même pattern:
1. Lire section détaillée dans le plan
2. Checklist de compréhension
3. Étapes d'implémentation une par une
4. Tests
5. Validation des critères d'acceptation

**Référez-vous TOUJOURS au plan pour les détails complets.**

---

## Checkpoints de Validation

Après chaque sprint, **STOP et validez TOUT** avant de continuer:

### Checkpoint Priority 0 (Fondations)
```bash
# 1. Tous les tests passent
pytest backend/tests/ -v

# 2. Coverage >= 80%
pytest --cov=app --cov-report=html

# 3. Linter passe
ruff check backend/app/
mypy backend/app/

# 4. Test manuel E2E
# - Créer projet
# - Générer concept/plan
# - Générer chapitre avec contradiction
# - Vérifier que contradiction détectée et bloque
# - Approuver chapitre corrigé
# - Vérifier RAG updated (chercher dans Qdrant)

# 5. Logs
# - Vérifier logs montrent contexte enrichi
# - Vérifier logs montrent validation cohérence
# - Vérifier logs montrent RAG updates
```

**NE PAS passer à Priority 1 tant que Priority 0 n'est pas 100% validée.**

---

## Debugging et Troubleshooting

### Si tests échouent:
1. Lire le message d'erreur COMPLET
2. Vérifier les imports
3. Vérifier les type hints
4. Vérifier async/await correctement utilisés
5. Vérifier fixtures dans conftest.py
6. Ajouter `logger.debug()` pour tracer

### Si génération échoue:
1. Vérifier logs API DeepSeek
2. Vérifier format du prompt (pas de JSON malformé)
3. Vérifier `response_format={"type": "json_object"}` si attendu
4. Vérifier temperature et max_tokens appropriés

### Si RAG ne trouve pas:
1. Vérifier collection Qdrant existe: `self.client.collection_exists()`
2. Vérifier vectors indexés: `self.client.count(collection_name)`
3. Vérifier filter project_id correct
4. Tester query directement dans Qdrant

### Si mémoire stale:
1. Vérifier hooks appelés (logs)
2. Vérifier project_metadata commit
3. Manuellement trigger `/maintenance/reconcile`

---

## Livrables Attendus

À la fin de CHAQUE priorité:

1. **Code:**
   - [ ] Tous les fichiers modifiés/créés listés
   - [ ] Pas d'erreurs de syntaxe
   - [ ] Type hints partout
   - [ ] Docstrings complètes
   - [ ] Logs appropriés

2. **Tests:**
   - [ ] Tests unitaires (>= 80% coverage)
   - [ ] Tests d'intégration (au moins 1)
   - [ ] Tous les tests passent

3. **Documentation:**
   - [ ] API changes documentées (si applicable)
   - [ ] Migration guide (si breaking change)
   - [ ] Update README si nécessaire

4. **Commit:**
   - [ ] Message clair: `feat(coherence): implement Priority X.Y - [description]`
   - [ ] Branch: `feature/coherence-priority-X-Y`
   - [ ] Pull request avec checklist

---

## Questions Fréquentes

**Q: Puis-je modifier l'ordre d'implémentation?**
**R:** NON. L'ordre est défini par dépendances. Priority 1.2 dépend de 0.2, etc.

**Q: Puis-je sauter les tests?**
**R:** NON. Tests sont critiques. Pas de merge sans tests.

**Q: Le plan dit "optionnel" pour Neo4j. Dois-je l'implémenter?**
**R:** OUI si c'est dans la priorité en cours. "Optionnel" signifie que le système doit fonctionner SANS Neo4j (graceful degradation), pas que vous pouvez sauter l'implémentation.

**Q: Combien de temps par priorité?**
**R:** Voir estimations dans plan. Priority 0.1 = ~1 jour, 0.2 = ~2 jours, etc.

**Q: Puis-je refactoriser du code existant?**
**R:** Seulement si nécessaire pour votre tâche. Pas de refactoring gratuit. Focus = implémenter le plan.

**Q: Le LLM retourne du JSON malformé dans mes tests. Que faire?**
**R:** Mock les appels LLM dans tests unitaires. Tests d'intégration peuvent utiliser vrai LLM mais avec fixtures de réponses attendues.

---

## Ressources

- **Plan complet:** `COHERENCE_IMPLEMENTATION_PLAN.md`
- **FastAPI docs:** https://fastapi.tiangolo.com/
- **LangGraph docs:** https://langchain-ai.github.io/langgraph/
- **Qdrant docs:** https://qdrant.tech/documentation/
- **Pydantic docs:** https://docs.pydantic.dev/

---

## Commencer l'Implémentation

**AVANT toute chose:**

1. ✅ Lire ce prompt EN ENTIER
2. ✅ Lire `COHERENCE_IMPLEMENTATION_PLAN.md` EN ENTIER
3. ✅ Confirmer compréhension du projet
4. ✅ Identifier votre priorité assignée (0.1, 0.2, etc.)
5. ✅ Lire les fichiers clés listés ci-dessus

**Puis:**

1. Annoncer: "Je commence Priority X.Y: [titre]"
2. Faire checklist de compréhension
3. Planifier sous-tâches
4. Implémenter méthodiquement
5. Tester exhaustivement
6. Valider critères d'acceptation
7. Commit

**GO! 🚀**

---

*Document créé pour guider l'implémentation méthodique du système de cohérence NovellaForge. Version: 1.0*
