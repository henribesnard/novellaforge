# Implementation Plan - Coherence System (Prioritized)

Goal: ensure long-form novel coherence from start to finish by tightening context, memory,
validation, and persistence across chapters.

Scope: backend only (writing pipeline, memory, RAG, project metadata, agents).
Out of scope: frontend UI/UX changes (can be added later).

---

## État des Lieux - Analyse du Backend Actuel

### ✅ Éléments Déjà en Place

#### 1. **Memory Service** (`backend/app/services/memory_service.py`)
**Forces:**
- Système d'extraction de faits de continuité fonctionnel avec schéma JSON
- Extraction des entités: characters (name, role, status), locations (name, description), relations (from, to, type, detail), events (name, summary)
- Mécanisme de merge intelligent évitant les doublons (par nom pour entities, par clé composite pour relations)
- Bloc de contexte de continuité injectable dans les prompts via `build_context_block()`
- Support optionnel Neo4j pour graphe de relations (stockage des entités et relations avec MERGE)
- Support optionnel ChromaDB pour mémoire de style (stockage et récupération de chapitres similaires)

**Faiblesses:**
- Extraction limitée à 6000 premiers caractères seulement (`chapter_text[:6000]`)
- Schéma d'extraction basique: pas de motivations, traits psychologiques, arcs de transformation
- Pas de timeline markers ou time_reference pour les événements
- `build_context_block()` retourne juste des noms séparés par virgules - trop minimal pour maintenir cohérence
- Pas de validation que l'extraction a réussi ou de fallback robuste
- Neo4j et ChromaDB optionnels mais pas de dégradation gracieuse si absents

#### 2. **Writing Pipeline** (`backend/app/services/writing_pipeline.py`)
**Forces:**
- Pipeline structuré avec LangGraph: collect_context → retrieve_context → plan_chapter → write_chapter → critic
- Injection du memory_context dans les prompts de génération (ligne 238)
- Récupération RAG des chunks pertinents (top 3) et style chunks (ligne 241-246)
- Système de critique avec score, issues, suggestions, continuity_risks (méthode `critic()`)
- Quality gate avec révisions automatiques (max 3 révisions, ligne 341-350)
- Approbation de chapitre met à jour la mémoire:
  - Extraction des faits du chapitre approuvé (ligne 383)
  - Merge des faits dans project_metadata (ligne 388)
  - Mise à jour des recent_chapter_summaries (derniers 10, ligne 390-393)
  - Mise à jour du statut du chapitre dans le plan (ligne 395-403)
  - Stockage dans Neo4j et ChromaDB (ligne 415-421)
- Écriture par beats pour contrôler la longueur et la structure
- Condensation automatique si dépassement de word count

**Faiblesses:**
- **Pas de validation de cohérence inter-chapitres active:** le critic mentionne `continuity_risks` mais ne compare pas explicitement avec la mémoire existante
- Les `continuity_alerts` ne bloquent pas l'approbation - pas de quality gate strict sur la cohérence
- Le memory_context injecté est trop minimal (juste des noms)
- **RAG non mis à jour automatiquement lors de l'approbation** - nécessite reindex_documents=True manuel
- Pas de vérification que les required_plot_points du plan sont couverts
- Pas de détection de contradictions explicites (ex: personnage mort qui réapparaît)
- Les révisions se basent sur le score global, pas spécifiquement sur la cohérence

#### 3. **Context Service** (`backend/app/services/context_service.py`)
**Forces:**
- Collecte exhaustive du contexte projet: metadata, concept, plan, continuity, recent_chapter_summaries
- Agrégation de tous les documents (triés par order_index) avec preview (800 chars)
- Agrégation de tous les personnages avec leurs métadonnées
- Récupération des instructions utilisateur
- Résolution du chapitre à générer depuis le plan ou calcul automatique

**Faiblesses:**
- Preview de 800 caractères peut être insuffisant pour longs chapitres
- Pas de priorisation intelligente des documents (ex: chapitres récents vs anciens)
- Pas de story bible structurée - tout dans le JSONB metadata
- Pas de système de tags ou indexation pour retrouver rapidement des éléments spécifiques

#### 4. **RAG Service** (`backend/app/services/rag_service.py`)
**Forces:**
- Indexation vectorielle dans Qdrant avec embeddings HuggingFace
- Chunking intelligent avec RecursiveCharacterTextSplitter (overlap pour contexte)
- Filtrage par project_id pour isolation des projets
- Support de l'indexation incrémentale avec clear_existing option
- Métadonnées riches par chunk (document_id, title, order_index, type, chunk_index)

**Faiblesses:**
- **Pas de mise à jour automatique lors de l'approbation de chapitre**
- **Pas de hook sur modification manuelle de documents**
- Pas de stratégie de re-ranking (chunks retournés par similarité pure)
- Chunk size fixe (pas adaptatif selon le type de contenu)
- Pas de détection de duplicatas lors de réindexation partielle

#### 5. **Novella Service** (`backend/app/services/novella_service.py`)
**Forces:**
- Génération de concept structuré: title, premise, tone, tropes, emotional_orientation
- Génération de plan avec arcs narratifs et chapitres détaillés
- Chaque chapitre a: index, title, summary, emotional_stake, arc_id, cliffhanger_type, status
- Évitement des titres déjà utilisés (3 tentatives max)
- Fallbacks robustes si génération échoue
- Tracking du statut des chapitres (planned → approved)

**Faiblesses:**
- **required_plot_points générés dans le plan mais jamais validés lors de la génération**
- Pas de contraintes strictes sur la cohérence arc-to-arc
- Pas de vérification que les arcs s'enchaînent logiquement
- Statut "approved" mis à jour mais pas de workflow de validation stricte

#### 6. **Modèles de Données**
**Forces:**
- Project.project_metadata (JSONB) flexible pour stocker concept, plan, continuity, instructions
- Document.document_metadata pour chapter_index, summary, emotional_stake, status, chapter_plan
- Character.character_metadata pour relations, goals (extensible)
- Timestamps automatiques (created_at, updated_at)
- Relations CASCADE pour nettoyage automatique

**Faiblesses:**
- **Pas de modèle dédié pour Story Bible** - tout dans le JSONB non structuré
- **Pas de modèle pour tracking des contradictions/conflits**
- Pas de versioning des documents (historique des modifications)
- character_metadata sous-utilisé (role stocké mais pas de schéma fixe)

#### 7. **Agents Spécialisés**
**Forces:**
- Architecture agents modulaire avec base_agent
- NarrativeArchitect pour structure narrative globale
- Autres agents: CharacterManager, DialogueMaster, StyleExpert

**Faiblesses:**
- **Pas d'agent ConsistencyAnalyst dédié à la cohérence**
- Agents non intégrés dans le pipeline d'écriture automatique
- Pas de mécanisme de collaboration entre agents
- Pas d'agent pour validation des contraintes du plan

---

## Priority 0 (Foundations - must have)

### 1) Renforcer la Mémoire de Continuité et son Utilisation

**Problème actuel:**
- Extraction limitée à 6000 chars (`extract_facts` ligne 53)
- Schéma basique: characters n'ont que name/role/status
- `build_context_block()` retourne "Characters: Alice, Bob" au lieu d'infos détaillées
- Pas de tracking temporel des changements (ex: "Alice was injured in chapter 5")

**Améliorations:**
- **Enrichir le schéma d'extraction JSON:**
  ```json
  {
    "characters": [
      {
        "name": "...",
        "role": "protagonist/antagonist/...",
        "status": "alive/injured/missing/...",
        "current_state": "emotional and physical state",
        "motivations": ["list of current motivations"],
        "traits": ["personality traits that drive actions"],
        "goals": ["short and long-term goals"],
        "arc_stage": "where in their transformation arc",
        "last_seen_chapter": 5,
        "relationships": ["key relationships mentioned"]
      }
    ],
    "locations": [
      {
        "name": "...",
        "description": "...",
        "rules": ["world rules that apply here"],
        "timeline_markers": ["events that happened here"],
        "atmosphere": "current state/atmosphere",
        "last_mentioned_chapter": 3
      }
    ],
    "relations": [
      {
        "from": "character A",
        "to": "character B",
        "type": "ally/enemy/romantic/...",
        "detail": "specific nature of relationship",
        "start_chapter": 1,
        "current_state": "current status of relationship",
        "evolution": "how it has changed"
      }
    ],
    "events": [
      {
        "name": "...",
        "summary": "...",
        "chapter_index": 5,
        "time_reference": "before/after/during X",
        "impact": "consequences of this event",
        "unresolved_threads": ["plot threads still open"]
      }
    ]
  }
  ```

- **Augmenter la fenêtre d'extraction:**
  - Passer de 6000 à 10000 chars minimum
  - Si chapitre > 10000 chars, extraire en 2 passes (début + fin) et merger
  - Alternative: extraire par beats/scènes si disponibles dans metadata

- **Améliorer `build_context_block()` pour contexte riche:**
  ```python
  # Au lieu de: "Characters: Alice, Bob"
  # Générer:
  """
  CONTINUITY FACTS:

  Characters:
  - Alice (protagonist): Currently injured from chapter 12 fight.
    Motivation: revenge against Victor. Trait: impulsive.
    Arc stage: approaching confrontation with past.
  - Bob (ally): Supporting Alice but conflicted about methods.
    Relationship with Alice: strained since chapter 10 argument.

  Locations:
  - Dark Forest: Forbidden zone. Rule: magic doesn't work here.
    Last seen: chapter 11. Atmosphere: ominous, Alice left wounded.

  Key Relations:
  - Alice → Victor [enemy]: Alice seeks revenge for father's death (ch. 1).
    Current state: Victor unaware of Alice's proximity.

  Recent Events:
  - Battle at Dark Forest (ch. 12): Alice wounded, Bob saved her.
    Impact: Alice now weakened. Unresolved: Victor's next move.
  """
  ```

- **Injecter ce contexte enrichi dans TOUS les prompts critiques:**
  - Prompt de génération de chapitre (`write_chapter` ligne 224+)
  - Prompt de critique (`critic` ligne 313+)
  - Prompt de planification (`plan_chapter` ligne 176+)

**Fichiers impactés:**
- `backend/app/services/memory_service.py`:
  - Modifier `extract_facts()` avec nouveau prompt et schéma
  - Modifier `merge_facts()` pour gérer nouveaux champs
  - Réécrire `build_context_block()` pour format détaillé
  - Ajouter `_merge_with_temporal_tracking()` pour historique
- `backend/app/services/writing_pipeline.py`:
  - Vérifier que memory_context est bien injecté partout
  - Ajouter logs pour debug du contexte injecté

**Critères d'acceptation:**
- ✅ Extraction JSON contient minimum 5 champs par character (name, role, status, motivations, current_state)
- ✅ Context block fait minimum 200 mots (vs ~20 actuellement)
- ✅ Logs montrent contexte complet injecté dans prompts generation et critique
- ✅ Tests unitaires vérifient merge avec nouveaux champs

### 2) Implémenter des Vérifications de Cohérence Inter-Chapitres Strictes

**Problème actuel:**
- Le `critic()` mentionne `continuity_risks` mais ne fait pas de comparaison active
- Pas de détection de contradictions flagrantes (ex: personnage mort qui parle)
- `_quality_gate()` ne bloque pas sur continuity - seulement score >= 8 et word count
- continuity_alerts retournés mais jamais utilisés pour bloquer

**Améliorations:**

- **Ajouter une étape `validate_continuity` dans le graph:**
  ```python
  # Dans _build_graph():
  graph.add_node("validate_continuity", self.validate_continuity)
  graph.add_edge("write_chapter", "validate_continuity")
  graph.add_edge("validate_continuity", "critic")
  ```

- **Implémenter la méthode `validate_continuity()`:**
  - Extraire les entités mentionnées dans le draft
  - Comparer avec continuity memory:
    * Vérifier statuts cohérents (mort/vivant, présent/absent)
    * Vérifier relations cohérentes (ennemis qui collaborent sans explication)
    * Vérifier timeline (événements dans bon ordre)
  - Comparer avec RAG (chapitres précédents récents):
    * Détecter changements d'apparence/personnalité non expliqués
    * Vérifier que lieux/objets mentionnés existaient
  - Comparer avec plan (required_plot_points):
    * Vérifier que points d'intrigue requis sont abordés
    * Vérifier que emotional_stake du plan est respecté

- **Prompt de validation détaillé:**
  ```python
  prompt = f"""Analyse ce chapitre draft pour détecter les incohérences.

  DRAFT DU CHAPITRE:
  {chapter_text}

  MÉMOIRE DE CONTINUITÉ:
  {memory_context}

  CHAPITRES PRÉCÉDENTS PERTINENTS:
  {rag_chunks}

  CONTRAINTES DU PLAN:
  - Résumé attendu: {chapter_summary}
  - Enjeu émotionnel: {emotional_stake}
  - Points d'intrigue requis: {required_plot_points}

  Retourne JSON avec:
  {{
    "severe_issues": [
      {{"type": "contradiction", "detail": "...", "severity": "blocking"}},
      {{"type": "missing_plot_point", "detail": "...", "severity": "blocking"}}
    ],
    "minor_issues": [
      {{"type": "timeline_unclear", "detail": "...", "severity": "warning"}}
    ],
    "coherence_score": 0-10,
    "blocking": true/false
  }}

  Severity "blocking" = incohérence grave qui casse la continuité.
  """
  ```

- **Modifier `_quality_gate()` pour intégrer validation:**
  ```python
  def _quality_gate(self, state: NovelState) -> str:
      # Critères existants
      score = state.get("critique_score", 0.0)
      word_count = self._count_words(state.get("chapter_text", ""))
      min_words = state.get("min_word_count", settings.CHAPTER_MIN_WORDS)
      max_words = state.get("max_word_count", settings.CHAPTER_MAX_WORDS)

      # NOUVEAU: vérifier cohérence
      validation = state.get("continuity_validation", {})
      is_blocking = validation.get("blocking", False)
      coherence_score = validation.get("coherence_score", 0)

      # Bloquer si problèmes sévères
      if is_blocking:
          return "revise"

      # Réviser si cohérence faible même si score général OK
      if coherence_score < 7:
          return "revise"

      # Critères existants
      if score >= 8.0 and min_words <= word_count <= max_words:
          return "done"

      if state.get("revision_count", 0) >= 3:
          return "done"  # Fallback après 3 tentatives

      return "revise"
  ```

- **Persister les alertes pour traçabilité:**
  - Stocker dans document_metadata: `continuity_validation_history`
  - Inclure dans réponse API pour affichage à l'utilisateur

**Fichiers impactés:**
- `backend/app/services/writing_pipeline.py`:
  - Ajouter méthode `validate_continuity()`
  - Modifier `_build_graph()` pour ajouter le node
  - Modifier `_quality_gate()` pour vérifier blocking issues
  - Modifier `_persist_draft()` pour stocker validation history
- `backend/app/schemas/writing.py`:
  - Ajouter schéma pour continuity_validation

**Critères d'acceptation:**
- ✅ Contradictions sévères (ex: mort qui parle) déclenchent révision automatique
- ✅ Missing plot points critiques déclenchent révision
- ✅ `blocking: true` empêche passage à "done" même si score élevé
- ✅ Validation history stockée dans metadata pour debug
- ✅ API retourne detailed continuity_alerts dans réponse

### 3) Maintenir Mémoire et RAG Toujours à Jour Automatiquement

**Problème actuel:**
- `approve_chapter()` met à jour memory et Neo4j/ChromaDB mais **PAS le RAG Qdrant**
- Nécessite `reindex_documents=True` manuel avant génération (ligne 141-143)
- **Aucun hook sur modification manuelle de documents** - mémoire devient stale
- Si utilisateur édite un chapitre approuvé, continuity pas mise à jour

**Améliorations:**

- **Mise à jour automatique RAG lors de l'approbation:**
  ```python
  # Dans approve_chapter() après ligne 421:
  async def approve_chapter(self, document_id: str, user_id: UUID) -> Dict[str, Any]:
      # ... code existant jusqu'à ligne 421 ...

      # NOUVEAU: Mise à jour RAG automatique
      await self.rag_service.aindex_documents(
          document.project_id,
          [document],  # Juste le document approuvé
          clear_existing=False  # Incrémental
      )

      return {
          "document_id": str(document.id),
          "status": "approved",
          "summary": summary,
          "rag_updated": True  # Indicateur pour l'utilisateur
      }
  ```

- **Hook sur modification manuelle de documents:**

  Dans `backend/app/api/v1/endpoints/documents.py`, endpoint `update_document`:
  ```python
  @router.put("/{document_id}")
  async def update_document(
      document_id: UUID,
      document_update: DocumentUpdate,
      db: AsyncSession = Depends(get_db),
      current_user: User = Depends(get_current_user),
  ):
      service = DocumentService(db)
      updated_doc = await service.update(document_id, document_update, current_user.id)

      # NOUVEAU: Si document est de type CHAPTER et status approved
      if (updated_doc.document_type == DocumentType.CHAPTER and
          updated_doc.document_metadata.get("status") == "approved"):

          # Refresh continuity memory
          memory_service = MemoryService()
          facts = await memory_service.extract_facts(updated_doc.content or "")

          # Récupérer et mettre à jour project metadata
          project = await db.get(Project, updated_doc.project_id)
          if project:
              project_metadata = project.project_metadata or {}
              project_metadata = memory_service.merge_facts(project_metadata, facts)
              project.project_metadata = project_metadata
              await db.commit()

          # Mise à jour RAG incrémentale
          rag_service = RagService()
          await rag_service.aindex_documents(
              updated_doc.project_id,
              [updated_doc],
              clear_existing=False
          )

          # OPTIONNEL: Update Neo4j et ChromaDB
          memory_service.update_neo4j(facts)
          summary = facts.get("summary") or updated_doc.document_metadata.get("summary")
          memory_service.store_style_memory(
              str(updated_doc.project_id),
              str(updated_doc.id),
              updated_doc.content,
              summary
          )

      return updated_doc
  ```

- **Stratégie d'indexation intelligente:**
  - Approuver chapitre → index juste ce chapitre (incrémental)
  - Éditer chapitre approuvé → re-index juste ce chapitre (update in place)
  - Supprimer chapitre → supprimer ses vectors de Qdrant
  - Changement massif (>5 docs) → full reindex du projet

- **Ajouter méthode `update_single_document()` au RAG:**
  ```python
  # Dans RagService:
  async def aupdate_document(
      self,
      project_id: UUID,
      document: Document,
  ) -> int:
      """Update a single document's vectors in Qdrant."""
      # Supprimer anciens vecteurs de ce document
      doc_filter = qdrant_models.Filter(
          must=[
              qdrant_models.FieldCondition(
                  key="document_id",
                  match=qdrant_models.MatchValue(value=str(document.id)),
              )
          ]
      )
      self.client.delete(
          collection_name=self.collection_name,
          points_selector=doc_filter,
      )

      # Réindexer ce document uniquement
      return await self.aindex_documents(
          project_id,
          [document],
          clear_existing=False
      )
  ```

- **Logging et monitoring:**
  - Logger chaque mise à jour de mémoire/RAG avec timestamp
  - Ajouter métrique `last_memory_update` dans project_metadata
  - Endpoint de santé pour vérifier sync: `/projects/{id}/coherence-health`

**Fichiers impactés:**
- `backend/app/services/writing_pipeline.py`:
  - Modifier `approve_chapter()` pour appeler RAG update
- `backend/app/api/v1/endpoints/documents.py`:
  - Ajouter hook dans `update_document()`
  - Ajouter hook dans `delete_document()`
- `backend/app/services/rag_service.py`:
  - Ajouter `aupdate_document()` et `adelete_document()`
- `backend/app/api/v1/endpoints/projects.py`:
  - Ajouter endpoint `GET /projects/{id}/coherence-health`

**Critères d'acceptation:**
- ✅ Chapitre approuvé → immédiatement searchable dans RAG (test avec requête)
- ✅ Édition manuelle de chapitre approved → memory et RAG mis à jour automatiquement
- ✅ Suppression de chapitre → vectors supprimés de Qdrant
- ✅ Logs montrent chaque update avec timestamp
- ✅ Endpoint `/coherence-health` retourne `last_memory_update` et `rag_document_count`

### 4) Tests Complets pour Mémoire + Quality Gate de Cohérence

**Problème actuel:**
- Tests existants basiques (conftest.py, test_memory_service.py, test_writing_pipeline.py)
- Pas de tests pour extraction enrichie
- Pas de tests pour validation de cohérence
- Pas de tests pour hooks de mise à jour automatique

**Améliorations:**

- **Tests d'extraction enrichie (`test_memory_service.py`):**
  ```python
  async def test_extract_facts_enriched_schema():
      """Test que l'extraction retourne tous les nouveaux champs."""
      service = MemoryService()
      chapter_text = """
      Alice, désespérée depuis la mort de son père au chapitre 1,
      confronte Victor dans la forêt interdite. Elle est blessée mais déterminée.
      Bob, son allié, essaie de la raisonner mais Alice refuse d'écouter.
      """

      facts = await service.extract_facts(chapter_text)

      # Vérifier schéma enrichi
      assert "characters" in facts
      alice = next(c for c in facts["characters"] if c["name"] == "Alice")
      assert "motivations" in alice
      assert "current_state" in alice
      assert "traits" in alice
      assert alice["motivations"]  # Non vide
      assert "blessée" in alice["current_state"].lower() or "wounded" in alice["current_state"].lower()

  async def test_merge_facts_temporal_tracking():
      """Test que le merge garde l'historique temporel."""
      service = MemoryService()
      metadata = {
          "continuity": {
              "characters": [
                  {"name": "Alice", "status": "healthy", "last_seen_chapter": 1}
              ]
          }
      }
      new_facts = {
          "characters": [
              {"name": "Alice", "status": "injured", "last_seen_chapter": 5}
          ]
      }

      updated = service.merge_facts(metadata, new_facts)

      alice = updated["continuity"]["characters"][0]
      assert alice["status"] == "injured"  # Mise à jour
      assert alice["last_seen_chapter"] == 5  # Mise à jour

  async def test_build_context_block_detailed():
      """Test que le context block est riche en détails."""
      service = MemoryService()
      metadata = {
          "continuity": {
              "characters": [
                  {
                      "name": "Alice",
                      "role": "protagonist",
                      "status": "injured",
                      "current_state": "wounded but determined",
                      "motivations": ["revenge for father"]
                  }
              ],
              "events": [
                  {
                      "name": "Father's death",
                      "chapter_index": 1,
                      "impact": "Alice seeks revenge"
                  }
              ]
          }
      }

      context_block = service.build_context_block(metadata)

      # Vérifier richesse du contexte (minimum 200 mots)
      word_count = len(context_block.split())
      assert word_count >= 100, f"Context trop court: {word_count} mots"

      # Vérifier présence d'infos clés
      assert "Alice" in context_block
      assert "injured" in context_block or "wounded" in context_block
      assert "revenge" in context_block
  ```

- **Tests de validation de cohérence (`test_writing_pipeline.py`):**
  ```python
  async def test_validate_continuity_detects_contradictions(db: AsyncSession):
      """Test que validate_continuity détecte les incohérences graves."""
      pipeline = WritingPipeline(db)

      state = {
          "chapter_text": "Bob, qui était mort au chapitre 3, entre dans la pièce.",
          "project_context": {
              "project": {
                  "metadata": {
                      "continuity": {
                          "characters": [
                              {"name": "Bob", "status": "dead", "last_seen_chapter": 3}
                          ]
                      }
                  }
              }
          },
          "memory_context": "Characters:\n- Bob (ally): Dead since chapter 3.",
          "retrieved_chunks": [],
      }

      result = await pipeline.validate_continuity(state)

      validation = result.get("continuity_validation", {})
      assert validation.get("blocking") == True, "Contradiction morte devrait bloquer"
      severe_issues = validation.get("severe_issues", [])
      assert len(severe_issues) > 0
      assert any("mort" in issue["detail"].lower() or "dead" in issue["detail"].lower()
                 for issue in severe_issues)

  async def test_quality_gate_blocks_on_coherence_issues(db: AsyncSession):
      """Test que quality gate bloque si problèmes de cohérence."""
      pipeline = WritingPipeline(db)

      state = {
          "critique_score": 9.0,  # Score élevé
          "chapter_text": "A" * 3000,  # Word count OK
          "min_word_count": 2000,
          "max_word_count": 5000,
          "continuity_validation": {
              "blocking": True,  # Mais problème de cohérence
              "coherence_score": 3,
              "severe_issues": [{"type": "contradiction", "detail": "..."}]
          },
          "revision_count": 0
      }

      decision = pipeline._quality_gate(state)

      assert decision == "revise", "Devrait réviser malgré bon score à cause de blocking"

  async def test_quality_gate_passes_with_good_coherence(db: AsyncSession):
      """Test que quality gate passe si tout est OK."""
      pipeline = WritingPipeline(db)

      state = {
          "critique_score": 9.0,
          "chapter_text": "A" * 3000,
          "min_word_count": 2000,
          "max_word_count": 5000,
          "continuity_validation": {
              "blocking": False,
              "coherence_score": 9,
              "severe_issues": []
          },
          "revision_count": 0
      }

      decision = pipeline._quality_gate(state)

      assert decision == "done", "Devrait passer avec bons scores et cohérence OK"
  ```

- **Tests d'auto-update RAG/mémoire:**
  ```python
  async def test_approve_chapter_updates_rag(db: AsyncSession, test_project, test_user):
      """Test que l'approbation met à jour le RAG."""
      # Créer un document draft
      doc_service = DocumentService(db)
      document = await doc_service.create(
          DocumentCreate(
              title="Test Chapter",
              content="Alice trouve l'épée magique.",
              document_type=DocumentType.CHAPTER,
              project_id=test_project.id,
              metadata={"status": "draft", "chapter_index": 5}
          ),
          user_id=test_user.id
      )

      # Approuver le chapitre
      pipeline = WritingPipeline(db)
      result = await pipeline.approve_chapter(str(document.id), test_user.id)

      # Vérifier RAG update
      assert result.get("rag_updated") == True

      # Vérifier que document est searchable
      rag_service = RagService()
      chunks = await rag_service.aretrieve(
          test_project.id,
          "épée magique",
          top_k=5
      )
      assert len(chunks) > 0
      assert any("épée" in chunk.lower() for chunk in chunks)

  async def test_manual_edit_updates_memory(db: AsyncSession, test_project, test_user):
      """Test que l'édition manuelle met à jour la mémoire."""
      # Créer et approuver un chapitre
      doc_service = DocumentService(db)
      document = await doc_service.create(
          DocumentCreate(
              title="Chapter",
              content="Alice est en bonne santé.",
              document_type=DocumentType.CHAPTER,
              project_id=test_project.id,
              metadata={"status": "approved", "chapter_index": 1}
          ),
          user_id=test_user.id
      )

      # Éditer le chapitre (simuler endpoint update)
      updated = await doc_service.update(
          document.id,
          DocumentUpdate(content="Alice est gravement blessée."),
          test_user.id
      )

      # Vérifier que memory est mise à jour
      project = await db.get(Project, test_project.id)
      continuity = project.project_metadata.get("continuity", {})
      characters = continuity.get("characters", [])
      alice = next((c for c in characters if c["name"] == "Alice"), None)

      assert alice is not None
      assert "blessée" in str(alice).lower() or "injured" in str(alice).lower()
  ```

**Fichiers impactés:**
- `backend/tests/test_memory_service.py`:
  - Ajouter tests pour schéma enrichi
  - Ajouter tests pour temporal tracking
  - Ajouter tests pour context block détaillé
- `backend/tests/test_writing_pipeline.py`:
  - Ajouter tests pour `validate_continuity()`
  - Ajouter tests pour quality gate avec cohérence
  - Ajouter tests pour approve_chapter → RAG update
- `backend/tests/test_documents.py` (nouveau):
  - Ajouter tests pour hooks d'édition manuelle
- `backend/tests/conftest.py`:
  - Ajouter fixtures pour projets avec continuity riche

**Critères d'acceptation:**
- ✅ Tous les nouveaux tests passent en local
- ✅ Coverage >= 80% sur memory_service et writing_pipeline
- ✅ Tests CI/CD passent
- ✅ Tests d'intégration E2E pour workflow complet: create → approve → edit → verify memory

## Priority 1 (Structure and traceability)

### 1) Story Bible et Timeline comme Données de Première Classe

**Problème actuel:**
- Tout stocké dans le JSONB `project_metadata` non structuré
- Pas de schéma dédié pour world rules, glossaire, timeline
- Mélangé avec concept, plan, continuity - difficile à maintenir
- Pas d'API dédiée pour gérer la bible

**Améliorations:**

- **Définir un schéma structuré pour la Story Bible:**
  ```json
  {
    "story_bible": {
      "world_rules": [
        {
          "id": "uuid",
          "category": "magic/technology/social/...",
          "rule": "La magie ne fonctionne pas dans la Forêt Noire",
          "explanation": "Raison détaillée...",
          "established_chapter": 3,
          "exceptions": ["sauf pour les elfes"],
          "importance": "critical/high/medium/low"
        }
      ],
      "timeline": [
        {
          "id": "uuid",
          "event": "Mort du père d'Alice",
          "chapter_index": 1,
          "time_reference": "before story start",
          "absolute_date": "optional ISO date",
          "duration": "instant/hours/days/...",
          "participants": ["Alice's father", "Victor"],
          "impact": "Déclenche quête de revenge d'Alice"
        }
      ],
      "glossary": {
        "terms": [
          {
            "term": "Épée de Lumière",
            "definition": "Artefact légendaire...",
            "first_mention_chapter": 5,
            "aliases": ["Lame Sacrée"],
            "related_rules": ["rule_uuid"]
          }
        ],
        "places": [
          {
            "name": "Forêt Noire",
            "description": "Zone interdite au nord...",
            "first_mention_chapter": 2,
            "rules": ["No magic rule"],
            "atmosphere": "Ominous, dark, dangerous"
          }
        ],
        "factions": [
          {
            "name": "La Garde du Roi",
            "description": "...",
            "members": ["character names"],
            "goals": ["..."],
            "relationships": {"The Rebels": "enemy"}
          }
        ]
      },
      "core_themes": [
        {
          "theme": "Revenge vs Forgiveness",
          "description": "Alice's internal conflict",
          "chapters_explored": [1, 5, 8]
        }
      ],
      "established_facts": [
        {
          "fact": "Victor killed Alice's father",
          "established_chapter": 1,
          "cannot_contradict": true,
          "related_events": ["event_uuid"]
        }
      ]
    }
  }
  ```

- **API endpoints pour gérer la bible:**
  ```python
  # Dans backend/app/api/v1/endpoints/projects.py:

  @router.get("/{project_id}/story-bible")
  async def get_story_bible(
      project_id: UUID,
      db: AsyncSession = Depends(get_db),
      current_user: User = Depends(get_current_user),
  ):
      """Récupérer la story bible complète."""
      project = await get_project_or_404(project_id, current_user.id, db)
      bible = project.project_metadata.get("story_bible", {})
      return bible

  @router.put("/{project_id}/story-bible/world-rules")
  async def update_world_rules(
      project_id: UUID,
      rules: List[WorldRule],  # Nouveau schema Pydantic
      db: AsyncSession = Depends(get_db),
      current_user: User = Depends(get_current_user),
  ):
      """Ajouter/modifier des règles du monde."""
      project = await get_project_or_404(project_id, current_user.id, db)
      metadata = project.project_metadata or {}
      bible = metadata.setdefault("story_bible", {})
      bible["world_rules"] = [rule.dict() for rule in rules]
      project.project_metadata = metadata
      await db.commit()
      return {"status": "updated", "rules_count": len(rules)}

  @router.put("/{project_id}/story-bible/timeline")
  async def update_timeline(
      project_id: UUID,
      events: List[TimelineEvent],
      db: AsyncSession = Depends(get_db),
      current_user: User = Depends(get_current_user),
  ):
      """Ajouter/modifier des événements de la timeline."""
      # Similaire à update_world_rules

  @router.post("/{project_id}/story-bible/validate-draft")
  async def validate_draft_against_bible(
      project_id: UUID,
      draft_text: str,
      db: AsyncSession = Depends(get_db),
      current_user: User = Depends(get_current_user),
  ):
      """Valider un draft contre la story bible."""
      # Utiliser LLM pour comparer draft avec bible
      # Retourner violations potentielles
  ```

- **Intégrer bible dans le contexte de génération:**
  ```python
  # Dans context_service.py:
  async def build_project_context(...):
      # ... code existant ...

      story_bible = project_metadata.get("story_bible", {})

      return {
          "project": {...},
          "story_bible": story_bible,  # Nouveau
          "constraints": constraints or {},
          # ... reste ...
      }

  # Dans writing_pipeline.py, write_chapter():
  story_bible = state.get("project_context", {}).get("story_bible", {})
  bible_block = self._build_bible_context_block(story_bible)

  base_prompt = f"""
  ...
  STORY BIBLE (RULES CRITIQUES):
  {bible_block}

  CONTEXTE MÉMOIRE:
  {state.get('memory_context', '')}
  ...
  """
  ```

- **Créer `_build_bible_context_block()`:**
  ```python
  def _build_bible_context_block(self, bible: Dict[str, Any]) -> str:
      parts = []

      # World rules critiques
      rules = bible.get("world_rules", [])
      critical_rules = [r for r in rules if r.get("importance") in ["critical", "high"]]
      if critical_rules:
          parts.append("RÈGLES DU MONDE (NE PAS VIOLER):")
          for rule in critical_rules[:5]:  # Top 5
              parts.append(f"- {rule['rule']}")
              if rule.get("exceptions"):
                  parts.append(f"  Exceptions: {', '.join(rule['exceptions'])}")

      # Timeline events critiques
      timeline = bible.get("timeline", [])
      if timeline:
          parts.append("\nTIMELINE ÉTABLIE:")
          for event in timeline[-10:]:  # 10 derniers événements
              ref = event.get("time_reference", "")
              parts.append(f"- Ch.{event['chapter_index']}: {event['event']} ({ref})")

      # Established facts non-contradictibles
      facts = bible.get("established_facts", [])
      cannot_contradict = [f for f in facts if f.get("cannot_contradict")]
      if cannot_contradict:
          parts.append("\nFAITS ÉTABLIS (INCONTESTABLES):")
          for fact in cannot_contradict:
              parts.append(f"- {fact['fact']} (établi ch.{fact['established_chapter']})")

      return "\n".join(parts) if parts else ""
  ```

- **Schémas Pydantic:**
  ```python
  # backend/app/schemas/story_bible.py (nouveau fichier):
  from pydantic import BaseModel, Field
  from typing import List, Optional
  from uuid import UUID, uuid4

  class WorldRule(BaseModel):
      id: UUID = Field(default_factory=uuid4)
      category: str
      rule: str
      explanation: Optional[str] = None
      established_chapter: Optional[int] = None
      exceptions: List[str] = []
      importance: str = "medium"  # critical/high/medium/low

  class TimelineEvent(BaseModel):
      id: UUID = Field(default_factory=uuid4)
      event: str
      chapter_index: int
      time_reference: Optional[str] = None
      absolute_date: Optional[str] = None
      duration: Optional[str] = None
      participants: List[str] = []
      impact: Optional[str] = None

  class GlossaryTerm(BaseModel):
      term: str
      definition: str
      first_mention_chapter: Optional[int] = None
      aliases: List[str] = []
      related_rules: List[UUID] = []

  class EstablishedFact(BaseModel):
      fact: str
      established_chapter: int
      cannot_contradict: bool = True
      related_events: List[UUID] = []

  class StoryBible(BaseModel):
      world_rules: List[WorldRule] = []
      timeline: List[TimelineEvent] = []
      glossary: Dict[str, List] = {}
      core_themes: List[Dict] = []
      established_facts: List[EstablishedFact] = []
  ```

**Fichiers impactés:**
- `backend/app/schemas/story_bible.py` (nouveau)
- `backend/app/api/v1/endpoints/projects.py`:
  - Ajouter endpoints story-bible
- `backend/app/services/context_service.py`:
  - Retourner story_bible dans contexte
- `backend/app/services/writing_pipeline.py`:
  - Ajouter `_build_bible_context_block()`
  - Injecter dans prompts
- `backend/app/services/novella_service.py`:
  - Initialiser story_bible lors de generate_plan

**Critères d'acceptation:**
- ✅ GET /story-bible retourne schéma structuré
- ✅ PUT endpoints permettent CRUD sur world_rules, timeline, glossary
- ✅ Story bible injectée dans prompts de génération (visible dans logs)
- ✅ Validation de draft contre bible détecte violations de rules
- ✅ Frontend peut afficher et éditer la bible (hors scope backend mais schéma prêt)

### 2) Enforcement des Contraintes du Plan

**Problème actuel:**
- `novella_service` génère des `required_plot_points` dans le plan (ligne 305-312)
- Ces points sont stockés dans chapter metadata mais **jamais vérifiés**
- Pipeline n'utilise pas `required_plot_points` dans validation
- Pas de mécanisme pour s'assurer que le chapitre couvre les points d'intrigue

**Améliorations:**

- **Enrichir le plan avec contraintes explicites:**
  ```python
  # Dans novella_service.py, generate_plan():
  prompt = f"""
  ...
  Chaque chapitre doit avoir:
  - required_plot_points: liste de 2-4 éléments narratifs OBLIGATOIRES
  - optional_subplots: sous-intrigues suggérées
  - arc_constraints: contraintes de l'arc narratif parent
  - forbidden_actions: ce qui ne doit PAS arriver dans ce chapitre

  Exemple pour un chapitre:
  {{
    "index": 5,
    "title": "...",
    "summary": "...",
    "required_plot_points": [
      "Alice découvre que Victor est son oncle",
      "Bob révèle avoir travaillé pour Victor",
      "L'épée de Lumière est activée pour la première fois"
    ],
    "optional_subplots": ["Tension romantique Alice-Bob"],
    "arc_constraints": ["Maintenir le mystère sur l'identité du traître"],
    "forbidden_actions": ["Ne pas révéler le plan de Victor complet"],
    "success_criteria": "Le lecteur doit être choqué par la révélation familiale"
  }}
  """
  ```

- **Validation des plot points dans validate_continuity:**
  ```python
  # Dans writing_pipeline.py:
  async def validate_continuity(self, state: NovelState) -> Dict[str, Any]:
      # ... validations existantes ...

      # NOUVEAU: Vérifier required_plot_points
      plan = state.get("current_plan") or {}
      required_points = plan.get("required_plot_points", [])
      forbidden_actions = plan.get("forbidden_actions", [])
      chapter_text = state.get("chapter_text", "")

      plot_point_issues = await self._validate_plot_points(
          chapter_text,
          required_points,
          forbidden_actions
      )

      # Merger avec autres validations
      # ...

  async def _validate_plot_points(
      self,
      chapter_text: str,
      required_points: List[str],
      forbidden_actions: List[str]
  ) -> Dict[str, Any]:
      """Vérifier que les plot points requis sont couverts."""
      if not required_points:
          return {"missing_points": [], "forbidden_violations": []}

      prompt = f"""Analyse ce chapitre pour vérifier la couverture des points d'intrigue.

  CHAPITRE:
  {chapter_text}

  POINTS D'INTRIGUE REQUIS (DOIVENT tous être présents):
  {chr(10).join(f"- {p}" for p in required_points)}

  ACTIONS INTERDITES (NE DOIVENT PAS apparaître):
  {chr(10).join(f"- {a}" for a in forbidden_actions)}

  Retourne JSON:
  {{
    "covered_points": ["list of points that ARE covered"],
    "missing_points": ["list of points that are MISSING"],
    "forbidden_violations": ["list of forbidden actions that appear"],
    "coverage_score": 0-10,
    "explanation": "brief explanation"
  }}
  """

      response = await self.llm_client.chat(
          messages=[{"role": "user", "content": prompt}],
          temperature=0.2,
          max_tokens=500,
          response_format={"type": "json_object"},
      )
      validation = self._safe_json(response)

      missing = validation.get("missing_points", [])
      violations = validation.get("forbidden_violations", [])

      # Créer issues pour quality gate
      issues = []
      for point in missing:
          issues.append({
              "type": "missing_plot_point",
              "detail": f"Point d'intrigue requis manquant: {point}",
              "severity": "blocking"
          })

      for violation in violations:
          issues.append({
              "type": "forbidden_action",
              "detail": f"Action interdite présente: {violation}",
              "severity": "blocking"
          })

      return {
          "missing_points": missing,
          "forbidden_violations": violations,
          "coverage_score": validation.get("coverage_score", 0),
          "issues": issues
      }
  ```

- **Intégrer dans quality gate:**
  ```python
  def _quality_gate(self, state: NovelState) -> str:
      # ... critères existants ...

      # Vérifier plot points
      validation = state.get("continuity_validation", {})
      plot_point_validation = validation.get("plot_point_validation", {})
      missing_points = plot_point_validation.get("missing_points", [])

      # Bloquer si points critiques manquants
      if missing_points:
          return "revise"

      # ... reste de la logique ...
  ```

- **Feedback dans révision:**
  ```python
  # Dans write_chapter(), inclure missing points dans revision notes:
  revision_notes = state.get("critique_feedback") or []
  plot_validation = state.get("continuity_validation", {}).get("plot_point_validation", {})
  missing = plot_validation.get("missing_points", [])

  if missing:
      revision_notes.append(
          f"POINTS D'INTRIGUE MANQUANTS À AJOUTER: {', '.join(missing)}"
      )

  # Ce sera injecté dans le prompt de réécriture (ligne 251-253)
  ```

- **Tracking de la couverture dans metadata:**
  ```python
  # Dans _persist_draft():
  metadata = {
      "status": "draft",
      "chapter_index": chapter_index,
      "summary": state.get("chapter_summary"),
      "emotional_stake": state.get("chapter_emotional_stake"),
      "cliffhanger_type": (result.get("current_plan") or {}).get("cliffhanger_type"),
      "chapter_plan": result.get("current_plan"),
      "plot_point_coverage": {  # NOUVEAU
          "required": (result.get("current_plan") or {}).get("required_plot_points", []),
          "covered": result.get("continuity_validation", {}).get("plot_point_validation", {}).get("covered_points", []),
          "missing": result.get("continuity_validation", {}).get("plot_point_validation", {}).get("missing_points", []),
          "coverage_score": result.get("continuity_validation", {}).get("plot_point_validation", {}).get("coverage_score", 0)
      }
  }
  ```

**Fichiers impactés:**
- `backend/app/services/novella_service.py`:
  - Enrichir prompt de génération de plan avec required_plot_points détaillés
- `backend/app/services/writing_pipeline.py`:
  - Ajouter `_validate_plot_points()`
  - Intégrer dans `validate_continuity()`
  - Modifier `_quality_gate()` pour bloquer si missing points
  - Modifier `write_chapter()` pour inclure missing points dans révision
  - Modifier `_persist_draft()` pour tracker coverage
- `backend/app/schemas/writing.py`:
  - Ajouter schéma pour plot_point_coverage

**Critères d'acceptation:**
- ✅ Chapitre généré sans required_plot_points → révision automatique
- ✅ Chapitre avec forbidden_action → révision automatique
- ✅ Document metadata contient plot_point_coverage avec scores
- ✅ API retourne coverage dans réponse pour affichage à l'utilisateur
- ✅ Tests vérifient que missing points déclenchent révision

### 3) Agent Dédié à l'Analyse de Cohérence

**Problème actuel:**
- Pas d'agent spécialisé en cohérence (narrative_architect existe mais focus structure)
- Validation de cohérence faite dans le critic générique
- Pas de mécanisme d'analyse manuelle approfondie de la cohérence globale
- Agents non intégrés dans le pipeline automatique

**Améliorations:**

- **Créer ConsistencyAnalyst Agent:**
  ```python
  # backend/app/services/agents/consistency_analyst.py (nouveau):
  """Consistency Analyst Agent - Gardien de la cohérence narrative"""
  from typing import Dict, Any, Optional, List
  from .base_agent import BaseAgent

  class ConsistencyAnalyst(BaseAgent):
      """Agent spécialisé dans l'analyse de cohérence narrative."""

      @property
      def name(self) -> str:
          return "Analyste de Cohérence"

      @property
      def description(self) -> str:
          return "Détecte et corrige les incohérences narratives, temporelles et factuelles"

      @property
      def system_prompt(self) -> str:
          return """Tu es l'Analyste de Cohérence de NovellaForge, expert en continuité narrative.

  Ton rôle est de:
  - Détecter les contradictions factuelles (personnages, lieux, événements)
  - Vérifier la cohérence temporelle (timeline, chronologie)
  - Identifier les violations de règles du monde établies
  - Repérer les incohérences de personnalité/motivation
  - Valider que les faits établis ne sont pas contredits
  - Suggérer des corrections précises et justifiées

  Tu es méticuleux, objectif et constructif. Tu hiérarchises les problèmes par gravité:
  - CRITICAL: Brise la logique fondamentale de l'histoire
  - HIGH: Contradiction majeure qui perturbe l'immersion
  - MEDIUM: Incohérence notable mais récupérable
  - LOW: Détail mineur à surveiller

  Tu fournis toujours des exemples concrets et des suggestions de correction."""

      async def execute(
          self, task_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None
      ) -> Dict[str, Any]:
          """Exécute une analyse de cohérence."""
          action = task_data.get("action", "analyze_chapter")

          if action == "analyze_chapter":
              return await self._analyze_chapter_coherence(task_data, context)
          elif action == "analyze_project":
              return await self._analyze_project_coherence(task_data, context)
          elif action == "suggest_fixes":
              return await self._suggest_coherence_fixes(task_data, context)
          else:
              return {
                  "agent": self.name,
                  "action": action,
                  "error": "Action non reconnue",
                  "success": False,
              }

      async def _analyze_chapter_coherence(
          self, task_data: Dict[str, Any], context: Optional[Dict[str, Any]]
      ) -> Dict[str, Any]:
          """Analyse la cohérence d'un chapitre."""
          chapter_text = task_data.get("chapter_text", "")
          memory_context = task_data.get("memory_context", "")
          story_bible = task_data.get("story_bible", {})
          previous_chapters = task_data.get("previous_chapters", [])

          prompt = f"""Analyse la cohérence de ce chapitre par rapport au contexte établi.

  CHAPITRE À ANALYSER:
  {chapter_text}

  MÉMOIRE DE CONTINUITÉ:
  {memory_context}

  STORY BIBLE (Règles du monde et faits établis):
  {self._format_bible(story_bible)}

  EXTRAITS DES CHAPITRES PRÉCÉDENTS:
  {chr(10).join(previous_chapters[-5:])}

  Retourne un JSON avec la structure:
  {{
    "contradictions": [
      {{
        "type": "factual/temporal/character/world_rule",
        "severity": "critical/high/medium/low",
        "description": "Description précise de la contradiction",
        "location_in_text": "Citation du passage problématique",
        "conflicts_with": "Référence à ce qui est contredit",
        "established_in_chapter": number or "story_bible",
        "suggested_fix": "Comment corriger sans casser l'histoire"
      }}
    ],
    "timeline_issues": [
      {{
        "issue": "Description du problème temporel",
        "severity": "critical/high/medium/low",
        "suggested_fix": "Correction suggérée"
      }}
    ],
    "character_inconsistencies": [
      {{
        "character": "Nom du personnage",
        "issue": "Description de l'incohérence",
        "severity": "critical/high/medium/low",
        "previous_state": "État/comportement établi",
        "current_state": "État/comportement dans ce chapitre",
        "suggested_fix": "Comment réconcilier"
      }}
    ],
    "world_rule_violations": [
      {{
        "rule": "Règle violée",
        "violation": "Comment elle est violée",
        "severity": "critical/high/medium/low",
        "suggested_fix": "Correction ou justification à ajouter"
      }}
    ],
    "overall_coherence_score": 0-10,
    "summary": "Résumé de l'analyse",
    "blocking_issues": ["Liste des problèmes qui DOIVENT être corrigés"]
  }}

  Sois exhaustif et précis dans ton analyse."""

          response = await self._call_api(prompt, context, temperature=0.2)
          analysis = self._safe_json(response)

          return {
              "agent": self.name,
              "action": action,
              "analysis": analysis,
              "success": True,
              "total_issues": self._count_issues(analysis),
              "critical_count": self._count_by_severity(analysis, "critical"),
          }

      async def _analyze_project_coherence(
          self, task_data: Dict[str, Any], context: Optional[Dict[str, Any]]
      ) -> Dict[str, Any]:
          """Analyse la cohérence globale du projet."""
          all_chapters = task_data.get("all_chapters", [])
          story_bible = task_data.get("story_bible", {})
          continuity_memory = task_data.get("continuity_memory", {})

          prompt = f"""Analyse la cohérence globale de ce roman sur tous les chapitres.

  CHAPITRES DU ROMAN ({len(all_chapters)} chapitres):
  {self._format_chapters_summary(all_chapters)}

  STORY BIBLE:
  {self._format_bible(story_bible)}

  MÉMOIRE DE CONTINUITÉ GLOBALE:
  {self._format_memory(continuity_memory)}

  Retourne un JSON avec:
  {{
    "global_contradictions": [...],  // Contradictions qui touchent plusieurs chapitres
    "timeline_coherence": {{
      "score": 0-10,
      "issues": [...],
      "gaps": [...]  // Sauts temporels non expliqués
    }},
    "character_arcs_consistency": [
      {{
        "character": "...",
        "arc_coherence_score": 0-10,
        "issues": [...],
        "evolution_summary": "..."
      }}
    ],
    "world_building_consistency": {{
      "score": 0-10,
      "rule_violations": [...],
      "unexplained_changes": [...]
    }},
    "plot_threads": [
      {{
        "thread": "...",
        "status": "resolved/ongoing/abandoned",
        "chapters": [1, 5, 8],
        "coherence_score": 0-10,
        "issues": [...]
      }}
    ],
    "overall_project_coherence_score": 0-10,
    "critical_issues_to_fix": [...],
    "recommendations": [...]
  }}"""

          response = await self._call_api(prompt, context, temperature=0.3)
          analysis = self._safe_json(response)

          return {
              "agent": self.name,
              "action": action,
              "global_analysis": analysis,
              "success": True,
          }

      async def _suggest_coherence_fixes(
          self, task_data: Dict[str, Any], context: Optional[Dict[str, Any]]
      ) -> Dict[str, Any]:
          """Suggère des corrections pour les problèmes identifiés."""
          issues = task_data.get("issues", [])
          chapter_text = task_data.get("chapter_text", "")
          context_data = task_data.get("context", "")

          prompt = f"""Propose des corrections précises pour ces problèmes de cohérence.

  TEXTE PROBLÉMATIQUE:
  {chapter_text}

  CONTEXTE:
  {context_data}

  PROBLÈMES À CORRIGER:
  {chr(10).join(f"- {issue.get('description', issue)}" for issue in issues)}

  Pour chaque problème, propose:
  1. Une correction minimale (changer le moins possible)
  2. Une correction extensive (réécrire la section)
  3. Une explication narrative pour justifier l'incohérence (si possible)

  Retourne JSON:
  {{
    "fixes": [
      {{
        "issue": "...",
        "minimal_fix": {{"type": "edit", "original": "...", "replacement": "..."}},
        "extensive_fix": {{"type": "rewrite", "section": "...", "new_text": "..."}},
        "narrative_justification": {{"type": "add_explanation", "text": "..."}},
        "recommendation": "minimal/extensive/justification"
      }}
    ]
  }}"""

          response = await self._call_api(prompt, context, temperature=0.4)
          fixes = self._safe_json(response)

          return {
              "agent": self.name,
              "action": action,
              "fixes": fixes,
              "success": True,
          }

      def _format_bible(self, bible: Dict[str, Any]) -> str:
          # Format story bible pour le prompt
          parts = []
          if bible.get("world_rules"):
              parts.append("RÈGLES DU MONDE:")
              for rule in bible["world_rules"][:10]:
                  parts.append(f"- {rule.get('rule', '')}")
          # ... etc
          return "\n".join(parts)

      def _format_chapters_summary(self, chapters: List[Dict]) -> str:
          return "\n\n".join([
              f"CHAPITRE {ch.get('index', '?')}: {ch.get('title', '')}\n{ch.get('summary', '')}"
              for ch in chapters
          ])

      def _count_issues(self, analysis: Dict) -> int:
          return sum([
              len(analysis.get("contradictions", [])),
              len(analysis.get("timeline_issues", [])),
              len(analysis.get("character_inconsistencies", [])),
              len(analysis.get("world_rule_violations", []))
          ])

      def _count_by_severity(self, analysis: Dict, severity: str) -> int:
          count = 0
          for key in ["contradictions", "timeline_issues", "character_inconsistencies", "world_rule_violations"]:
              items = analysis.get(key, [])
              count += sum(1 for item in items if item.get("severity") == severity)
          return count
  ```

- **Intégrer dans agent_factory:**
  ```python
  # Dans agent_factory.py:
  from app.services.agents.consistency_analyst import ConsistencyAnalyst

  class AgentFactory:
      @staticmethod
      def create_agent(agent_type: str) -> BaseAgent:
          agents = {
              "narrative_architect": NarrativeArchitect,
              "character_manager": CharacterManager,
              "dialogue_master": DialogueMaster,
              "style_expert": StyleExpert,
              "consistency_analyst": ConsistencyAnalyst,  # NOUVEAU
          }
          # ...
  ```

- **Endpoint API pour appel manuel:**
  ```python
  # Dans endpoints/agents.py:
  @router.post("/consistency-analyst/analyze-chapter")
  async def analyze_chapter_consistency(
      request: ConsistencyAnalysisRequest,
      db: AsyncSession = Depends(get_db),
      current_user: User = Depends(get_current_user),
  ):
      """Analyse la cohérence d'un chapitre spécifique."""
      agent = AgentFactory.create_agent("consistency_analyst")

      context = await build_agent_context(request.project_id, db, current_user.id)

      result = await agent.execute(
          task_data={
              "action": "analyze_chapter",
              "chapter_text": request.chapter_text,
              "memory_context": context.get("memory_context"),
              "story_bible": context.get("story_bible"),
              "previous_chapters": context.get("previous_chapters", []),
          },
          context=context,
      )

      return result

  @router.post("/consistency-analyst/analyze-project")
  async def analyze_project_consistency(
      project_id: UUID,
      db: AsyncSession = Depends(get_db),
      current_user: User = Depends(get_current_user),
  ):
      """Analyse la cohérence globale du projet."""
      # Similar implementation
  ```

- **Intégration optionnelle dans pipeline:**
  ```python
  # Dans writing_pipeline.py, ajouter comme étape optionnelle:
  async def deep_consistency_check(self, state: NovelState) -> Dict[str, Any]:
      """Analyse approfondie avec ConsistencyAnalyst agent."""
      if not state.get("use_consistency_analyst", False):
          return {}

      agent = AgentFactory.create_agent("consistency_analyst")
      analysis = await agent.execute(
          task_data={
              "action": "analyze_chapter",
              "chapter_text": state.get("chapter_text", ""),
              "memory_context": state.get("memory_context", ""),
              "story_bible": state.get("project_context", {}).get("story_bible", {}),
              "previous_chapters": state.get("retrieved_chunks", []),
          },
          context=state.get("project_context"),
      )

      return {"consistency_analyst_report": analysis}
  ```

**Fichiers impactés:**
- `backend/app/services/agents/consistency_analyst.py` (nouveau)
- `backend/app/services/agents/agent_factory.py`:
  - Ajouter ConsistencyAnalyst
- `backend/app/api/v1/endpoints/agents.py`:
  - Ajouter endpoints d'analyse
- `backend/app/schemas/agents.py`:
  - Ajouter ConsistencyAnalysisRequest
- `backend/app/services/writing_pipeline.py` (optionnel):
  - Ajouter `deep_consistency_check()` node

**Critères d'acceptation:**
- ✅ Agent listable via AgentFactory
- ✅ POST /agents/consistency-analyst/analyze-chapter retourne analyse structurée
- ✅ POST /agents/consistency-analyst/analyze-project retourne analyse globale
- ✅ Analyse détecte contradictions, timeline issues, character inconsistencies
- ✅ Retourne suggestions de fix concrètes
- ✅ Scores de cohérence calculés (0-10)
- ✅ Tests unitaires pour l'agent

## Priority 2 (Advanced reasoning and long-run stability)

### 1) Raisonnement de Continuité Basé sur Graphe (Neo4j)

**Problème actuel:**
- Neo4j supporté mais sous-utilisé (juste MERGE d'entités, ligne 100-148 memory_service.py)
- Pas de requêtes temporelles ou d'évolution
- Pas de détection de patterns suspects dans le graphe
- Graphe non exploité pour validation

**Améliorations:**

- **Ajouter attributs temporels aux nodes et relations:**
  ```cypher
  // Au lieu de:
  MERGE (c:Character {name: $name})
  SET c.role = $role, c.status = $status

  // Faire:
  MERGE (c:Character {name: $name})
  ON CREATE SET c.created_chapter = $chapter_index, c.first_appearance = $timestamp
  SET c.role = $role,
      c.status = $status,
      c.last_seen_chapter = $chapter_index,
      c.last_updated = $timestamp,
      c.status_history = c.status_history + [{status: $status, chapter: $chapter_index, timestamp: $timestamp}]
  ```

- **Queries avancées pour validation:**
  ```python
  # Dans memory_service.py:

  def query_character_evolution(self, character_name: str) -> Dict[str, Any]:
      """Récupère l'évolution d'un personnage."""
      if not self.neo4j_driver:
          return {}

      query = """
      MATCH (c:Character {name: $name})
      RETURN c.name as name,
             c.status_history as status_history,
             c.first_appearance as first_appearance,
             c.last_seen_chapter as last_seen_chapter
      """
      with self.neo4j_driver.session() as session:
          result = session.run(query, name=character_name)
          record = result.single()
          return dict(record) if record else {}

  def detect_character_contradictions(self, character_name: str) -> List[Dict]:
      """Détecte les contradictions dans l'historique."""
      if not self.neo4j_driver:
          return []

      query = """
      MATCH (c:Character {name: $name})
      UNWIND c.status_history as history
      WITH c, history
      ORDER BY history.chapter
      WITH c, collect(history) as ordered_history
      // Détecter status "dead" suivi de "alive"
      UNWIND range(0, size(ordered_history)-2) as i
      WITH c, ordered_history[i] as current, ordered_history[i+1] as next
      WHERE current.status = 'dead' AND next.status IN ['alive', 'active', 'healthy']
      RETURN {
        character: c.name,
        contradiction: 'resurrection',
        from_chapter: current.chapter,
        from_status: current.status,
        to_chapter: next.chapter,
        to_status: next.status
      } as issue
      """
      with self.neo4j_driver.session() as session:
          result = session.run(query, name=character_name)
          return [dict(record["issue"]) for record in result]

  def query_relationship_evolution(
      self, char_a: str, char_b: str
  ) -> List[Dict]:
      """Récupère l'évolution d'une relation."""
      if not self.neo4j_driver:
          return []

      query = """
      MATCH (a:Character {name: $char_a})-[r:RELATION]->(b:Character {name: $char_b})
      RETURN r.type as type,
             r.start_chapter as start_chapter,
             r.evolution_history as evolution,
             r.current_state as current_state
      """
      with self.neo4j_driver.session() as session:
          result = session.run(query, char_a=char_a, char_b=char_b)
          return [dict(record) for record in result]

  def find_orphaned_plot_threads(self) -> List[Dict]:
      """Trouve les fils narratifs non résolus."""
      if not self.neo4j_driver:
          return []

      query = """
      MATCH (e:Event)
      WHERE e.unresolved = true
      AND e.last_mentioned_chapter < $current_chapter - 10
      RETURN e.name as event,
             e.last_mentioned_chapter as last_mentioned,
             e.summary as summary
      ORDER BY e.last_mentioned_chapter
      """
      # Trouver events pas mentionnés depuis 10+ chapitres
      # (à implémenter avec current_chapter passé en param)
  ```

- **Intégration dans validate_continuity:**
  ```python
  # Dans writing_pipeline.py:
  async def validate_continuity(self, state: NovelState) -> Dict[str, Any]:
      # ... validations existantes ...

      # NOUVEAU: Graph-based validation
      graph_issues = await self._validate_with_graph(state)

      # Merger dans résultats
      # ...

  async def _validate_with_graph(self, state: NovelState) -> Dict[str, Any]:
      """Validation basée sur le graphe Neo4j."""
      chapter_text = state.get("chapter_text", "")
      memory = self.memory_service

      # Extraire personnages mentionnés dans le draft
      mentioned_chars = await self._extract_mentioned_characters(chapter_text)

      issues = []

      for char_name in mentioned_chars:
          # Vérifier évolution
          evolution = memory.query_character_evolution(char_name)

          # Vérifier contradictions
          contradictions = memory.detect_character_contradictions(char_name)
          for contradiction in contradictions:
              issues.append({
                  "type": "graph_contradiction",
                  "severity": "critical",
                  "detail": f"{char_name}: {contradiction['contradiction']} "
                            f"entre ch.{contradiction['from_chapter']} et ch.{contradiction['to_chapter']}",
                  "source": "neo4j_graph"
              })

      # Vérifier plot threads abandonnés
      orphaned = memory.find_orphaned_plot_threads()
      for thread in orphaned:
          issues.append({
              "type": "abandoned_plot_thread",
              "severity": "medium",
              "detail": f"Fil narratif '{thread['event']}' non résolu depuis ch.{thread['last_mentioned']}",
              "source": "neo4j_graph"
          })

      return {"graph_issues": issues}
  ```

- **Visualisation du graphe (endpoint API):**
  ```python
  # Dans endpoints/projects.py:
  @router.get("/{project_id}/coherence-graph")
  async def get_coherence_graph(
      project_id: UUID,
      db: AsyncSession = Depends(get_db),
      current_user: User = Depends(get_current_user),
  ):
      """Récupère le graphe de cohérence pour visualisation."""
      memory = MemoryService()

      # Récupérer tous les nodes et relations
      graph_data = memory.export_graph_for_visualization(str(project_id))

      return {
          "nodes": graph_data["nodes"],  # {id, label, type, properties}
          "edges": graph_data["edges"],  # {source, target, type, properties}
          "stats": {
              "total_characters": len([n for n in graph_data["nodes"] if n["type"] == "Character"]),
              "total_locations": len([n for n in graph_data["nodes"] if n["type"] == "Location"]),
              "total_relations": len(graph_data["edges"]),
          }
      }
  ```

**Fichiers impactés:**
- `backend/app/services/memory_service.py`:
  - Enrichir `update_neo4j()` avec attributs temporels
  - Ajouter queries: `query_character_evolution()`, `detect_character_contradictions()`, etc.
  - Ajouter `export_graph_for_visualization()`
- `backend/app/services/writing_pipeline.py`:
  - Ajouter `_validate_with_graph()`
  - Intégrer dans `validate_continuity()`
- `backend/app/api/v1/endpoints/projects.py`:
  - Ajouter endpoint `/coherence-graph`

**Critères d'acceptation:**
- ✅ Nodes et relations ont attributs temporels (chapter_index, timestamps)
- ✅ Requêtes détectent résurrections de personnages morts
- ✅ Requêtes identifient plot threads abandonnés (>10 chapitres sans mention)
- ✅ Graph validation intégrée dans pipeline
- ✅ Endpoint retourne graphe visualisable (nodes + edges)

---

### 2) Workflow de Résolution de Conflits

**Problème actuel:**
- Contradictions détectées mais pas trackées
- Pas de système pour que l'utilisateur marque comme "résolu" ou "intentionnel"
- Pas de mise à jour de bible/memory après résolution
- Alertes répétées pour même problème résolu

**Améliorations:**

- **Modèle pour tracker contradictions:**
  ```python
  # Stocker dans project_metadata:
  {
    "tracked_contradictions": [
      {
        "id": "uuid",
        "type": "character_resurrection/timeline/world_rule/...",
        "severity": "critical/high/medium/low",
        "description": "Bob apparaît vivant ch.15 après être mort ch.12",
        "detected_in_chapter": 15,
        "detected_at": "timestamp",
        "status": "pending/acknowledged/resolved/intentional",
        "resolution": {
          "type": "retcon/explanation/ignore",
          "action_taken": "Ajouté explication résurrection magique ch.14",
          "resolved_by": "user_id",
          "resolved_at": "timestamp",
          "bible_update": "Added rule: Characters can be resurrected via Phoenix Ritual"
        },
        "affected_chapters": [12, 15],
        "auto_detected": true
      }
    ]
  }
  ```

- **Endpoints de gestion:**
  ```python
  # Dans endpoints/projects.py:

  @router.get("/{project_id}/contradictions")
  async def list_contradictions(
      project_id: UUID,
      status: Optional[str] = None,  # Filter by status
      db: AsyncSession = Depends(get_db),
      current_user: User = Depends(get_current_user),
  ):
      """Liste les contradictions détectées."""
      project = await get_project_or_404(project_id, current_user.id, db)
      contradictions = project.project_metadata.get("tracked_contradictions", [])

      if status:
          contradictions = [c for c in contradictions if c.get("status") == status]

      return {
          "contradictions": contradictions,
          "summary": {
              "total": len(contradictions),
              "pending": len([c for c in contradictions if c["status"] == "pending"]),
              "resolved": len([c for c in contradictions if c["status"] == "resolved"]),
          }
      }

  @router.post("/{project_id}/contradictions/{contradiction_id}/resolve")
  async def resolve_contradiction(
      project_id: UUID,
      contradiction_id: str,
      resolution: ContradictionResolution,
      db: AsyncSession = Depends(get_db),
      current_user: User = Depends(get_current_user),
  ):
      """Marque une contradiction comme résolue."""
      project = await get_project_or_404(project_id, current_user.id, db)
      metadata = project.project_metadata or {}
      contradictions = metadata.get("tracked_contradictions", [])

      # Trouver la contradiction
      contradiction = next((c for c in contradictions if c["id"] == contradiction_id), None)
      if not contradiction:
          raise HTTPException(404, "Contradiction not found")

      # Marquer comme résolue
      contradiction["status"] = "resolved"
      contradiction["resolution"] = {
          "type": resolution.type,  # retcon/explanation/ignore
          "action_taken": resolution.action_taken,
          "resolved_by": str(current_user.id),
          "resolved_at": datetime.utcnow().isoformat(),
          "bible_update": resolution.bible_update,
      }

      # Si bible update fourni, l'ajouter
      if resolution.bible_update:
          bible = metadata.setdefault("story_bible", {})
          # Ajouter comme established_fact ou world_rule selon le cas
          if resolution.type == "explanation":
              bible.setdefault("established_facts", []).append({
                  "fact": resolution.bible_update,
                  "established_chapter": contradiction["detected_in_chapter"],
                  "cannot_contradict": True,
                  "resolution_of_contradiction": contradiction_id,
              })

      project.project_metadata = metadata
      await db.commit()

      return {"status": "resolved", "contradiction": contradiction}

  @router.post("/{project_id}/contradictions/{contradiction_id}/mark-intentional")
  async def mark_intentional(
      project_id: UUID,
      contradiction_id: str,
      explanation: str,
      db: AsyncSession = Depends(get_db),
      current_user: User = Depends(get_current_user),
  ):
      """Marque une contradiction comme intentionnelle (pas une erreur)."""
      # Similaire à resolve mais status = "intentional"
      # Ajoute à bible comme "intentional_twist" ou similar
  ```

- **Auto-tracking lors de la validation:**
  ```python
  # Dans writing_pipeline.py:
  async def validate_continuity(self, state: NovelState) -> Dict[str, Any]:
      # ... détections ...

      # Track nouvelles contradictions
      for issue in severe_issues:
          await self._track_contradiction(
              project_id=state["project_id"],
              issue=issue,
              chapter_index=state.get("chapter_index"),
          )

  async def _track_contradiction(
      self, project_id: UUID, issue: Dict, chapter_index: int
  ) -> None:
      """Ajoute une contradiction à la liste trackée."""
      project = await self.db.get(Project, project_id)
      metadata = project.project_metadata or {}
      contradictions = metadata.setdefault("tracked_contradictions", [])

      # Vérifier si déjà trackée
      existing = next((c for c in contradictions
                      if c["description"] == issue["detail"]
                      and c["status"] != "resolved"), None)

      if not existing:
          contradictions.append({
              "id": str(uuid.uuid4()),
              "type": issue["type"],
              "severity": issue["severity"],
              "description": issue["detail"],
              "detected_in_chapter": chapter_index,
              "detected_at": datetime.utcnow().isoformat(),
              "status": "pending",
              "affected_chapters": [chapter_index],
              "auto_detected": True,
          })

          project.project_metadata = metadata
          await self.db.commit()
  ```

- **Ne pas réalerter sur contradictions résolues:**
  ```python
  # Dans validate_continuity, filtrer issues déjà résolues:
  async def validate_continuity(self, state: NovelState) -> Dict[str, Any]:
      # ... détections ...

      # Filtrer contradictions déjà résolues/intentionnelles
      project_metadata = state.get("project_context", {}).get("project", {}).get("metadata", {})
      resolved_contradictions = [
          c["description"] for c in project_metadata.get("tracked_contradictions", [])
          if c["status"] in ["resolved", "intentional"]
      ]

      severe_issues = [
          issue for issue in severe_issues
          if issue["detail"] not in resolved_contradictions
      ]
  ```

**Fichiers impactés:**
- `backend/app/models/project.py`:
  - Documenter schéma `tracked_contradictions`
- `backend/app/api/v1/endpoints/projects.py`:
  - Ajouter endpoints: list/resolve/mark-intentional contradictions
- `backend/app/schemas/project.py`:
  - Ajouter `ContradictionResolution` schema
- `backend/app/services/writing_pipeline.py`:
  - Ajouter `_track_contradiction()`
  - Filtrer contradictions résolues

**Critères d'acceptation:**
- ✅ GET /contradictions retourne toutes les contradictions trackées
- ✅ POST /contradictions/{id}/resolve marque comme résolu et update bible
- ✅ POST /contradictions/{id}/mark-intentional marque comme voulu
- ✅ Contradictions résolues ne réapparaissent pas dans validations futures
- ✅ UI peut afficher liste des contradictions avec statuts (hors scope backend mais API prête)

---

### 3) Tâches de Maintenance Batch

**Problème actuel:**
- Pas de réconciliation périodique mémoire vs documents
- Si édition manuelle massive, memory peut dévier
- Pas de rebuild automatique après changements importants
- Pas de nettoyage de vieilles données

**Améliorations:**

- **Tâche Celery de réconciliation:**
  ```python
  # backend/app/tasks/coherence_maintenance.py (nouveau):
  from celery import shared_task
  from app.db.session import async_session
  from app.services.memory_service import MemoryService
  from app.services.rag_service import RagService
  from app.models.project import Project
  from app.models.document import Document, DocumentType
  from sqlalchemy import select

  @shared_task(name="reconcile_project_memory")
  async def reconcile_project_memory(project_id: str):
      """Réconcilie mémoire avec documents approved."""
      async with async_session() as db:
          # Charger projet
          project = await db.get(Project, UUID(project_id))
          if not project:
              return {"error": "Project not found"}

          # Charger tous les chapitres approved
          result = await db.execute(
              select(Document).where(
                  Document.project_id == UUID(project_id),
                  Document.document_type == DocumentType.CHAPTER
              ).order_by(Document.order_index)
          )
          chapters = result.scalars().all()
          approved = [ch for ch in chapters
                     if ch.document_metadata.get("status") == "approved"]

          # Rebuild continuity from scratch
          memory = MemoryService()
          fresh_continuity = {
              "characters": [],
              "locations": [],
              "relations": [],
              "events": [],
          }

          for chapter in approved:
              facts = await memory.extract_facts(chapter.content or "")
              # Merge progressivement
              fresh_continuity["characters"] = memory._merge_named(
                  fresh_continuity["characters"],
                  facts.get("characters", [])
              )
              # ... same for locations, relations, events ...

          # Comparer avec mémoire actuelle
          current_continuity = project.project_metadata.get("continuity", {})
          differences = _compare_continuity(current_continuity, fresh_continuity)

          # Mettre à jour si écarts significatifs
          if differences["significant_changes"]:
              project.project_metadata["continuity"] = fresh_continuity
              project.project_metadata["last_reconciliation"] = datetime.utcnow().isoformat()
              await db.commit()

          return {
              "reconciled": True,
              "chapters_processed": len(approved),
              "differences": differences,
          }

  @shared_task(name="rebuild_project_rag")
  async def rebuild_project_rag(project_id: str):
      """Rebuild complet du RAG pour un projet."""
      async with async_session() as db:
          result = await db.execute(
              select(Document).where(Document.project_id == UUID(project_id))
          )
          documents = result.scalars().all()

          rag = RagService()
          count = await rag.aindex_documents(
              UUID(project_id),
              list(documents),
              clear_existing=True
          )

          return {"reindexed": True, "chunks_count": count}

  @shared_task(name="cleanup_old_drafts")
  async def cleanup_old_drafts(project_id: str, days_threshold: int = 30):
      """Nettoie les drafts jamais approuvés de plus de X jours."""
      async with async_session() as db:
          cutoff = datetime.utcnow() - timedelta(days=days_threshold)

          result = await db.execute(
              select(Document).where(
                  Document.project_id == UUID(project_id),
                  Document.created_at < cutoff
              )
          )
          documents = result.scalars().all()

          old_drafts = [
              doc for doc in documents
              if doc.document_metadata.get("status") == "draft"
          ]

          for draft in old_drafts:
              await db.delete(draft)

          await db.commit()

          return {"deleted_drafts": len(old_drafts)}

  def _compare_continuity(old: Dict, new: Dict) -> Dict:
      """Compare deux états de continuity."""
      # Compter différences
      changes = {
          "added_characters": [],
          "removed_characters": [],
          "status_changes": [],
          "significant_changes": False,
      }

      old_chars = {c["name"]: c for c in old.get("characters", [])}
      new_chars = {c["name"]: c for c in new.get("characters", [])}

      changes["added_characters"] = list(set(new_chars.keys()) - set(old_chars.keys()))
      changes["removed_characters"] = list(set(old_chars.keys()) - set(new_chars.keys()))

      # Détecter changements de status
      for name in set(old_chars.keys()) & set(new_chars.keys()):
          if old_chars[name].get("status") != new_chars[name].get("status"):
              changes["status_changes"].append({
                  "character": name,
                  "old_status": old_chars[name].get("status"),
                  "new_status": new_chars[name].get("status"),
              })

      # Considérer comme significant si >5 changements
      changes["significant_changes"] = (
          len(changes["added_characters"]) +
          len(changes["removed_characters"]) +
          len(changes["status_changes"])
      ) > 5

      return changes
  ```

- **Endpoints pour déclencher manuellement:**
  ```python
  # Dans endpoints/projects.py:

  @router.post("/{project_id}/maintenance/reconcile")
  async def trigger_reconciliation(
      project_id: UUID,
      background_tasks: BackgroundTasks,
      current_user: User = Depends(get_current_user),
  ):
      """Déclenche réconciliation de la mémoire."""
      background_tasks.add_task(reconcile_project_memory, str(project_id))
      return {"status": "scheduled", "task": "reconcile_memory"}

  @router.post("/{project_id}/maintenance/rebuild-rag")
  async def trigger_rag_rebuild(
      project_id: UUID,
      background_tasks: BackgroundTasks,
      current_user: User = Depends(get_current_user),
  ):
      """Déclenche rebuild du RAG."""
      background_tasks.add_task(rebuild_project_rag, str(project_id))
      return {"status": "scheduled", "task": "rebuild_rag"}
  ```

- **Scheduled tasks automatiques:**
  ```python
  # Dans app/core/celery_app.py, ajouter beat schedule:
  from celery.schedules import crontab

  app.conf.beat_schedule = {
      "weekly-memory-reconciliation": {
          "task": "reconcile_all_active_projects",
          "schedule": crontab(day_of_week=0, hour=2),  # Dimanche 2h
      },
      "monthly-rag-rebuild": {
          "task": "rebuild_all_project_rags",
          "schedule": crontab(day_of_month=1, hour=3),  # 1er du mois 3h
      },
  }
  ```

**Fichiers impactés:**
- `backend/app/tasks/coherence_maintenance.py` (nouveau)
- `backend/app/core/celery_app.py`:
  - Ajouter beat schedule
- `backend/app/api/v1/endpoints/projects.py`:
  - Ajouter endpoints maintenance
- `backend/app/services/memory_service.py`:
  - Exposer `_compare_continuity()` si besoin

**Critères d'acceptation:**
- ✅ Tâche reconcile_project_memory fonctionne et détecte écarts
- ✅ Tâche rebuild_project_rag réindexe complètement
- ✅ Tâche cleanup_old_drafts supprime drafts anciens
- ✅ Endpoints manuels déclenchent tâches en background
- ✅ Beat schedule exécute réconciliations hebdomadaires
- ✅ Logs montrent résultats de chaque maintenance task

---

## Synthèse et Recommandations

### Points Forts du Système Actuel

Le backend NovellaForge dispose déjà de **fondations solides** pour la cohérence narrative:

1. **Architecture robuste:** Pipeline LangGraph structuré avec étapes claires (context → retrieve → plan → write → critic)
2. **Mémoire de base fonctionnelle:** Extraction de faits, merge intelligent, storage Neo4j/ChromaDB optionnel
3. **RAG opérationnel:** Indexation vectorielle Qdrant avec chunking et métadonnées riches
4. **Planification détaillée:** Génération de concept, plan avec arcs et chapitres structurés
5. **Quality gate existant:** Système de critique avec révisions (max 3)
6. **Approbation workflow:** Mise à jour mémoire lors de l'approbation de chapitres

### Gaps Critiques Identifiés

Malgré ces fondations, **plusieurs éléments clés manquent** pour garantir la cohérence sur un roman long (100+ chapitres):

#### 🔴 Critiques (Priority 0)
1. **Contexte mémoire trop minimal:** `build_context_block()` retourne juste des noms → LLM manque d'infos pour maintenir cohérence
2. **Pas de validation de cohérence stricte:** Le critic mentionne `continuity_risks` mais ne compare pas activement avec mémoire/bible
3. **RAG non mis à jour automatiquement:** Nécessite flag manuel, éditions manuelles ne déclenchent pas de mise à jour
4. **Quality gate ne bloque pas sur cohérence:** Un chapitre peut passer avec score 8+ même avec contradictions graves

#### 🟠 Importantes (Priority 1)
5. **Pas de Story Bible structurée:** Règles du monde, timeline, glossaire mélangés dans JSONB non structuré
6. **Plan non enforced:** `required_plot_points` générés mais jamais vérifiés lors de la génération
7. **Pas d'agent de cohérence dédié:** Validation faite par critic générique, pas d'analyse approfondie spécialisée

#### 🟡 Avancées (Priority 2)
8. **Neo4j sous-exploité:** Juste MERGE d'entités, pas de requêtes temporelles ni détection de patterns
9. **Pas de tracking des contradictions:** Alertes éphémères, pas de résolution workflow, alertes répétées
10. **Pas de maintenance automatique:** Mémoire peut dévier avec le temps, pas de réconciliation périodique

### Impact sur la Cohérence à Long Terme

**Sans ces améliorations**, sur un roman de 100+ chapitres:

- ❌ **Chapitre 1:** "Bob est l'ennemi juré d'Alice"
- ❌ **Chapitre 47:** "Bob aide Alice sans explication" (relation incohérente non détectée)
- ❌ **Chapitre 68:** "Bob est mort"
- ❌ **Chapitre 72:** "Bob entre dans la pièce" (résurrection non détectée)
- ❌ **Chapitre 85:** "La magie fonctionne dans la Forêt Noire" (violation world rule non catchée)
- ❌ **Chapitre 92:** Plot point critique du plan jamais adressé (lecteur frustré)

**Avec les améliorations Priority 0:**

- ✅ Contexte riche injecté → LLM sait que "Bob (enemy): last seen dead ch.68"
- ✅ Validation détecte: "BLOCKING: Bob marked dead ch.68, cannot appear alive" → révision forcée
- ✅ RAG auto-update → chapitres récents toujours searchables pour contexte
- ✅ Quality gate bloque si coherence_score < 7 même si score général OK

**Avec Priority 1:**

- ✅ Story Bible explicite: "Règle: Magie interdite Forêt Noire" → validée à chaque chapitre
- ✅ Plan enforced: "Ch.92 doit révéler identité traître" → vérifié, alerte si manquant
- ✅ ConsistencyAnalyst agent → analyse approfondie détecte "Bob-Alice relationship shift unexplained ch.47"

**Avec Priority 2:**

- ✅ Neo4j graph queries: "Bob status: [alive ch.1-67] → [dead ch.68] → [alive ch.72] = CONTRADICTION"
- ✅ Contradiction trackée, utilisateur résout: "Marked intentional: Bob resurrected via Phoenix Ritual ch.70"
- ✅ Maintenance hebdomadaire: réconciliation détecte memory drift, rebuild si nécessaire

### Ordre de Déploiement Recommandé

**Phase 1 - Fondations Critiques (2-3 sprints)**
- Priority 0.1: Enrichir mémoire et contexte (schema + context_block)
- Priority 0.2: Validation cohérence stricte (validate_continuity + quality_gate)
- Priority 0.3: Auto-update RAG/mémoire (hooks sur approve + edit)
- Priority 0.4: Tests complets

**Phase 2 - Structure et Outils (2 sprints)**
- Priority 1.1: Story Bible structurée (schéma + API + injection)
- Priority 1.2: Plan enforcement (validate plot points + quality gate)
- Priority 1.3: ConsistencyAnalyst agent (création + intégration)

**Phase 3 - Optimisations Avancées (2 sprints)**
- Priority 2.1: Neo4j queries temporelles (évolution + contradictions)
- Priority 2.2: Contradiction workflow (tracking + résolution)
- Priority 2.3: Maintenance batch (réconciliation + cleanup)

### Métriques de Succès

Pour mesurer l'amélioration de la cohérence:

1. **Taux de blocage de cohérence:**
   - Avant: 0% (aucun blocage sur cohérence)
   - Objectif: 15-25% des drafts bloqués pour incohérence grave

2. **Score de cohérence moyen:**
   - Mesurer coherence_score sur 100 chapitres
   - Objectif: > 8.5/10 en moyenne

3. **Contradictions non résolues:**
   - Tracker contradictions détectées vs résolues
   - Objectif: < 5% pending après 30 jours

4. **Couverture des plot points:**
   - % de chapitres couvrant leurs required_plot_points
   - Objectif: > 95%

5. **Temps de réconciliation:**
   - Mesurer drift mémoire vs documents
   - Objectif: < 3% de différence après réconciliation hebdomadaire

6. **Feedback utilisateur:**
   - Sondage: "Le système maintient-il la cohérence?"
   - Objectif: > 80% satisfaction

### Notes d'Implémentation

- **Prompts:** Tous en français; clés metadata en ASCII normalisé (snake_case)
- **Fallbacks:** Éviter silent fallbacks - logger et surfacer missing context à l'auteur
- **Performance:** Extraction enrichie + validation peuvent ralentir génération (~15-30s extra)
  - Considérer: paralléliser extractions, caching de bible/memory, batch processing
- **Coûts LLM:** Validation enrichie = +2-3 API calls par chapitre
  - Optimiser: prompts concis, temperature basse (0.2-0.3), utiliser haiku pour validation simple
- **Neo4j optionnel:** Toutes features doivent fonctionner sans Neo4j (degraded mode avec JSONB seulement)
- **Testing:** Tester avec projet réel de 50+ chapitres pour valider robustesse
- **Backward compatibility:** Projets existants doivent fonctionner - ajouter migration pour upgrade metadata schema

---

## Rollout Order (Détaillé)

### Sprint 1-2: Priority 0.1 + 0.2
- Enrichir extraction facts (5 fields minimum par entity)
- Réécrire build_context_block() (200+ mots)
- Créer validate_continuity() avec LLM validation
- Modifier quality_gate() pour bloquer si blocking=true
- Tests unitaires pour extraction et validation

### Sprint 3: Priority 0.3 + 0.4
- Hook auto-update RAG dans approve_chapter()
- Hook auto-update memory dans documents.update()
- Endpoint /coherence-health
- Tests d'intégration complets E2E
- Documentation API

### Sprint 4: Priority 1.1
- Définir schéma StoryBible (world_rules, timeline, glossary, etc.)
- Créer endpoints CRUD pour bible
- Modifier context_service pour retourner bible
- Créer _build_bible_context_block()
- Injecter bible dans prompts génération
- Tests + documentation

### Sprint 5: Priority 1.2
- Enrichir novella_service.generate_plan() avec required_plot_points détaillés
- Créer _validate_plot_points()
- Intégrer dans validate_continuity()
- Modifier quality_gate() pour bloquer si missing points
- Tracker coverage dans metadata
- Tests

### Sprint 6: Priority 1.3
- Créer ConsistencyAnalyst agent (analyze_chapter, analyze_project, suggest_fixes)
- Intégrer dans agent_factory
- Créer endpoints /agents/consistency-analyst/*
- Tests + documentation
- (Optionnel) Intégrer dans pipeline comme deep_consistency_check()

### Sprint 7: Priority 2.1
- Enrichir update_neo4j() avec attributs temporels
- Créer queries: character_evolution, detect_contradictions, relationship_evolution
- Créer _validate_with_graph()
- Endpoint /coherence-graph pour visualisation
- Tests

### Sprint 8: Priority 2.2
- Définir schéma tracked_contradictions
- Créer endpoints: list/resolve/mark-intentional
- Auto-tracking dans validate_continuity()
- Filtrer contradictions résolues
- Tests + documentation

### Sprint 9: Priority 2.3
- Créer tasks Celery: reconcile_memory, rebuild_rag, cleanup_old_drafts
- Configurer beat schedule
- Créer endpoints maintenance manuels
- Tests + monitoring
- Documentation ops

---

## Conclusion

Le système NovellaForge a **d'excellentes fondations** mais nécessite des **améliorations ciblées** pour garantir la cohérence narrative sur romans longs.

Les **Priority 0 (Foundations)** sont **critiques** et doivent être implémentées en premier - elles transformeront le système d'un générateur de chapitres indépendants à un véritable gardien de cohérence narrative.

Les **Priority 1-2** ajoutent puissance et robustesse mais peuvent être déployées progressivement selon les besoins utilisateurs et ressources disponibles.

**Estimation totale:** 9 sprints (18 semaines) pour implémentation complète, ou 3 sprints (6 semaines) pour Priority 0 uniquement qui apportera déjà 80% des bénéfices de cohérence.

## Notes
- All prompts should remain French; store only normalized ASCII keys in metadata.
- Avoid silent fallbacks: log and surface missing context to help the author.
- Test with real 50+ chapter projects to validate robustness.
- Monitor LLM costs - validation adds 2-3 API calls per chapter.
- Ensure backward compatibility - existing projects must work without migration (graceful degradation).
