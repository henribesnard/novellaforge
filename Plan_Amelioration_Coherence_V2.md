# Plan d'Amélioration de la Cohérence Narrative - NovellaForge v2.0

> **Analyse complète de l'architecture actuelle et recommandations basées sur les techniques modernes de génération narrative longue.**

---

## 📊 État des Lieux - Ce qui est Implémenté

### ✅ Fonctionnalités Existantes

| Composant | Implémentation | Maturité |
|-----------|----------------|----------|
| **Neo4j (Graphe de Connaissances)** | Personnages, relations, événements, fils narratifs | ⭐⭐⭐⭐ |
| **ChromaDB (Mémoire de Style)** | Stockage et récupération de style par projet | ⭐⭐⭐ |
| **ConsistencyAnalyst** | Système de gravité CRITICAL/HIGH/MEDIUM/LOW | ⭐⭐⭐⭐ |
| **Détection de Contradictions** | Résurrection de personnages, changements d'état | ⭐⭐⭐⭐ |
| **Fils Narratifs Abandonnés** | `find_orphaned_plot_threads` dans Neo4j | ⭐⭐⭐ |
| **Story Bible** | Timeline, glossaire, personnages, règles du monde | ⭐⭐⭐⭐ |
| **RAG (Qdrant)** | Récupération contextuelle documentaire | ⭐⭐⭐⭐ |
| **Validation de Continuité** | Intégrée au `WritingPipeline` avec LangGraph | ⭐⭐⭐ |
| **Cache Redis** | Performance et invalidation par projet | ⭐⭐⭐⭐ |
| **Extraction Automatique de Faits** | LLM-based dans `MemoryService` | ⭐⭐⭐ |

---

## ✅ Validation de Votre Analyse Initiale

### 1. Unification du Pipeline de Cohérence
**Statut : ✅ ANALYSE CORRECTE**

**Constat actuel :**
- Le `WritingPipeline.validate_continuity()` effectue sa propre validation inline via prompts LLM
- Le `ConsistencyAnalyst` possède un système de gravité plus sophistiqué et des suggestions de correction
- **Duplication de logique** entre les deux composants

**Recommandation validée :**
```python
# Avant (WritingPipeline)
prompt = "Analyse ce chapitre draft pour detecter les incoherences..."

# Après (déléguer au ConsistencyAnalyst)
from app.services.agents.consistency_analyst import ConsistencyAnalyst

analyst = ConsistencyAnalyst()
result = await analyst.execute({
    "action": "analyze_chapter",
    "chapter_text": chapter_text,
    "memory_context": memory_context,
    "story_bible": story_bible,
})
```

**Bénéfice :** Uniformisation du système de gravité et des suggestions de correction.

---

### 2. Implémentation de la Mémoire Récursive (Pyramide de Résumés)
**Statut : ✅ ANALYSE CORRECTE**

**Constat actuel :**
- Le système utilise les N derniers chapitres (extraits) via `previous_chapters[-5:]`
- Pas de structure hiérarchique de résumés
- Risque de perte de contexte sur des romans de 50+ chapitres

**Structure pyramidale recommandée :**
```
┌─────────────────────────────────────────────┐
│        Niveau 3 : Synopsis Global           │
│    (Mis à jour tous les 10 chapitres)       │
├─────────────────────────────────────────────┤
│      Niveau 2 : Résumés d'Arcs Narratifs    │
│   (Un résumé par arc, ~500 mots chacun)     │
├─────────────────────────────────────────────┤
│     Niveau 1 : Résumés de Chapitres         │
│   (Détail maximum, 5 derniers chapitres)    │
└─────────────────────────────────────────────┘
```

**Implémentation suggérée :**
```python
class RecursiveMemory:
    async def build_context(self, chapter_index: int) -> str:
        # Niveau 1 : Chapitres récents (détail max)
        recent = await self.get_recent_summaries(chapter_index, count=5)
        
        # Niveau 2 : Arc actuel
        arc_summary = await self.get_current_arc_summary(chapter_index)
        
        # Niveau 3 : Synopsis global compressé
        global_synopsis = await self.get_compressed_synopsis()
        
        return self.merge_levels(global_synopsis, arc_summary, recent)
```

**Priorité : HAUTE** - Impact direct sur la cohérence des romans longs.

---

### 3. Promotion Automatique vers la Story Bible
**Statut : ✅ ANALYSE CORRECTE**

**Constat actuel :**
- Les faits sont extraits et stockés dans Neo4j
- Pas de mécanisme pour promouvoir les faits récurrents en "vérités du monde"
- La Story Bible est alimentée manuellement ou via génération initiale

**Implémentation recommandée :**
```python
# backend/app/tasks/promote_facts_to_bible.py
@celery.task
def promote_facts_to_bible(project_id: str):
    """
    Analyse la fréquence des faits dans MemoryService
    et promeut automatiquement les faits récurrents.
    """
    memory_service = MemoryService()
    
    # Seuils de promotion
    CHARACTER_TRAIT_THRESHOLD = 3  # Trait mentionné 3+ fois
    WORLD_RULE_THRESHOLD = 2       # Règle appliquée 2+ fois
    
    # Requête Neo4j pour faits récurrents
    frequent_traits = memory_service.query_frequent_character_traits(
        project_id, min_occurrences=CHARACTER_TRAIT_THRESHOLD
    )
    
    for trait in frequent_traits:
        story_bible_service.add_character_trait(
            project_id,
            character=trait["character"],
            trait=trait["trait"],
            source="auto_promoted",
            confidence=trait["frequency"] / 10
        )
```

**Priorité : MOYENNE** - Améliore l'auto-apprentissage du système.

---

### 4. Vérification Proactive (Anti-Plot Hole)
**Statut : ⚠️ PARTIELLEMENT IMPLÉMENTÉ**

**Ce qui existe :**
- ✅ `detect_character_contradictions()` - détecte les résurrections
- ✅ `find_orphaned_plot_threads()` - détecte les fils abandonnés
- ❌ Pas de vérification de disponibilité des **objets**
- ❌ Pas de vérification de **localisation spatiale** des personnages

**Améliorations nécessaires :**
```python
# Nouveau : Tracking des objets/artefacts
async def check_object_availability(
    self, object_name: str, chapter_index: int, project_id: str
) -> Dict[str, Any]:
    """
    Vérifie si un objet est disponible pour être utilisé.
    Exemple : Une clé perdue au chapitre 3 ne peut pas ouvrir
    une porte au chapitre 7 sans avoir été retrouvée.
    """
    query = """
    MATCH (o:Object {name: $name, project_id: $project_id})
    RETURN o.status, o.last_holder, o.lost_at_chapter, o.location
    """
    # ...

# Nouveau : Tracking de localisation spatiale
async def check_character_location(
    self, character_name: str, required_location: str, chapter_index: int
) -> Dict[str, Any]:
    """
    Vérifie si un personnage peut être à un endroit donné.
    Exemple : Un personnage à Paris au chapitre 5 ne peut pas
    être à Tokyo au chapitre 6 sans voyage explicite.
    """
```

**Priorité : HAUTE** - Les plot holes d'objets et de localisation sont très fréquents.

---

### 5. Analyse de la Constance de la "Voix"
**Statut : ⚠️ PARTIELLEMENT IMPLÉMENTÉ**

**Ce qui existe :**
- ✅ ChromaDB stocke des références de style
- ✅ `retrieve_style_memory()` récupère des exemples
- ❌ Pas de **score de constance de voix par personnage**
- ❌ Pas de **comparaison vectorielle** des dialogues

**Implémentation recommandée :**
```python
class VoiceConsistencyAnalyzer:
    async def analyze_character_voice(
        self, character_name: str, new_dialogues: List[str], project_id: str
    ) -> Dict[str, Any]:
        """
        Compare les nouveaux dialogues avec le corpus validé
        pour ce personnage via similarité cosinus.
        """
        # Récupérer les dialogues validés depuis ChromaDB
        validated_dialogues = self.chroma_client.query(
            collection_name=f"dialogues_{project_id}",
            where={"character": character_name, "validated": True},
            n_results=20
        )
        
        # Embeddings des nouveaux dialogues
        new_embeddings = self.embed(new_dialogues)
        validated_embeddings = self.embed(validated_dialogues)
        
        # Similarité cosinus moyenne
        similarity = cosine_similarity(new_embeddings, validated_embeddings).mean()
        
        return {
            "character": character_name,
            "voice_consistency_score": similarity,
            "drift_detected": similarity < 0.75,
            "outlier_dialogues": self.find_outliers(new_dialogues, validated_embeddings)
        }
```

**Intégration dans le Critic :**
```python
# Dans app/services/writing_pipeline.py
async def critic(self, state: NovelState) -> Dict[str, Any]:
    # ... critique existante ...
    
    # Nouveau : Analyse de voix
    voice_analyzer = VoiceConsistencyAnalyzer()
    voice_scores = {}
    for character in self._extract_speaking_characters(text):
        voice_scores[character] = await voice_analyzer.analyze_character_voice(
            character, self._extract_dialogues(text, character), project_id
        )
    
    result["voice_analysis"] = voice_scores
```

**Priorité : MOYENNE** - Améliore significativement l'immersion narrative.

---

### 6. Gestion des Incohérences Intentionnelles
**Statut : ✅ ANALYSE CORRECTE - NON IMPLÉMENTÉ**

**Cas d'usage :**
- Un personnage ment délibérément (le lecteur ne le sait pas encore)
- Un mystère basé sur une contradiction apparente
- Un narrateur non fiable

**Implémentation recommandée :**
```python
# Nouveau modèle dans la Story Bible
class IntentionalMystery(BaseModel):
    id: str
    description: str
    contradiction_type: str  # "lie", "unreliable_narrator", "hidden_info"
    introduced_chapter: int
    resolution_planned_chapter: Optional[int]
    characters_involved: List[str]
    hints_to_drop: List[str]  # Indices à semer
    
# Endpoint API
@router.post("/{project_id}/story-bible/mysteries")
async def add_intentional_mystery(
    project_id: UUID,
    mystery: IntentionalMystery,
    ...
):
    """
    Marque une contradiction comme intentionnelle.
    Le ConsistencyAnalyst l'ignorera mais le NarrativeArchitect
    pourra l'utiliser pour planifier la résolution.
    """
```

**Modification du ConsistencyAnalyst :**
```python
async def _analyze_chapter_coherence(self, task_data, context):
    # Charger les mystères intentionnels
    intentional_mysteries = self._load_intentional_mysteries(context)
    
    # Filtrer les contradictions qui matchent un mystère
    contradictions = [c for c in raw_contradictions 
                      if not self._matches_mystery(c, intentional_mysteries)]
```

**Priorité : MOYENNE** - Essentiel pour les thrillers et mystères.

---

## 🆕 Améliorations Supplémentaires Recommandées

### 7. Tracking des "Chekhov's Guns" (Éléments à Résoudre)
**Statut : NON IMPLÉMENTÉ**

**Principe :** Tout élément significatif introduit doit être résolu ou utilisé.

```python
class ChekhlovsGunTracker:
    """
    Suit les éléments narratifs qui attendent une résolution :
    - Objets mystérieux introduits
    - Compétences de personnages mentionnées mais non utilisées
    - Menaces évoquées mais non concrétisées
    - Promesses faites par des personnages
    """
    
    async def extract_guns(self, chapter_text: str, chapter_index: int):
        prompt = """
        Identifie les éléments narratifs qui créent une attente chez le lecteur :
        - Objets significatifs (armes, clés, lettres, etc.)
        - Compétences ou secrets révélés
        - Menaces ou promesses
        - Foreshadowing explicite
        
        Retourne JSON : {"guns": [{"element": "...", "expectation": "...", "urgency": 1-10}]}
        """
        
    async def check_resolution(self, project_id: str, chapter_index: int):
        """Alerte si un élément reste non résolu trop longtemps."""
        unresolved = self.query_unresolved_guns(project_id, max_age_chapters=15)
        return [g for g in unresolved if g["urgency"] > 7]
```

**Priorité : HAUTE** - Évite les déceptions narratives majeures.

---

### 8. Validation de Point de Vue (POV)
**Statut : NON IMPLÉMENTÉ**

**Problème :** Dans un roman à POV limité, le narrateur ne devrait pas savoir ce que pensent les autres personnages.

```python
class POVValidator:
    async def validate_pov(
        self, chapter_text: str, pov_character: str, pov_type: str = "limited"
    ) -> Dict[str, Any]:
        """
        Détecte les violations de POV :
        - Pensées d'autres personnages accessibles
        - Informations que le POV ne peut pas connaître
        - Omniscience accidentelle
        """
        prompt = f"""
        POV actuel : {pov_character} ({pov_type})
        
        Analyse ce chapitre et détecte :
        1. Toute mention des pensées/émotions internes d'un personnage autre que {pov_character}
        2. Toute information que {pov_character} ne pourrait pas connaître
        3. Tout passage où le narrateur semble omniscient par accident
        
        Chapitre : {chapter_text}
        """
```

**Priorité : MOYENNE** - Critique pour les romans à POV strict.

---

### 9. Détection de Dérive de Personnalité (Character Drift)
**Statut : NON IMPLÉMENTÉ**

**Problème :** Sur un roman long, un personnage peut évoluer de manière incohérente sans événement justificatif.

```python
class CharacterDriftDetector:
    async def detect_drift(
        self, character_name: str, project_id: str, chapter_index: int
    ) -> Dict[str, Any]:
        """
        Compare le comportement actuel du personnage avec son arc établi.
        Détecte les changements non justifiés par des événements.
        """
        # Récupérer l'arc du personnage depuis Neo4j
        arc_data = self.memory_service.query_character_evolution(character_name, project_id)
        
        # Analyser les changements de comportement
        prompt = f"""
        Personnage : {character_name}
        Arc établi : {arc_data}
        
        Le comportement actuel est-il cohérent avec l'arc ?
        Si non, y a-t-il un événement justificatif dans les chapitres récents ?
        
        Retourne JSON : {{
            "drift_detected": bool,
            "drift_type": "personality/motivation/values",
            "severity": 1-10,
            "justification_found": bool,
            "suggested_justification": "..."
        }}
        """
```

**Priorité : HAUTE** - Les dérives de personnalité brisent l'immersion.

---

### 10. Gestion des Flashbacks et Chronologie Non-Linéaire
**Statut : NON IMPLÉMENTÉ**

**Problème :** Les flashbacks peuvent créer des paradoxes temporels difficiles à détecter.

```python
class NonLinearTimelineManager:
    """
    Gère les récits non-linéaires :
    - Flashbacks
    - Prologues dans le futur
    - Chapitres alternés entre époques
    """
    
    def register_flashback(
        self, chapter_index: int, flashback_time: str, characters_present: List[str]
    ):
        """
        Enregistre un flashback et vérifie :
        - Les personnages étaient-ils vivants à cette époque ?
        - Les événements du flashback ne contredisent-ils pas le présent ?
        - Les objets/lieux existaient-ils ?
        """
        
    def validate_timeline_consistency(self, project_id: str) -> List[Dict]:
        """
        Valide la cohérence globale de la timeline,
        y compris les segments non-linéaires.
        """
```

**Priorité : MOYENNE** - Essentiel pour les thrillers et sagas familiales.

---

### 11. Suivi des Arcs Émotionnels
**Statut : NON IMPLÉMENTÉ**

**Objectif :** Garantir que l'arc émotionnel du roman suit une courbe cohérente.

```python
class EmotionalArcTracker:
    async def analyze_emotional_progression(
        self, project_id: str, chapter_index: int
    ) -> Dict[str, Any]:
        """
        Analyse la progression émotionnelle :
        - Tension narrative (monte-t-elle vers le climax ?)
        - Variation (évite la monotonie)
        - Pic émotionnel au bon moment
        """
        chapters = await self.get_all_chapters(project_id)
        
        emotions_per_chapter = []
        for chapter in chapters:
            score = await self.extract_emotional_intensity(chapter)
            emotions_per_chapter.append(score)
        
        return {
            "emotional_curve": emotions_per_chapter,
            "tension_trend": self.analyze_trend(emotions_per_chapter),
            "flat_sections": self.detect_flat_sections(emotions_per_chapter),
            "premature_climax": self.detect_premature_climax(emotions_per_chapter),
            "recommendations": self.suggest_adjustments(emotions_per_chapter)
        }
```

**Priorité : MOYENNE** - Améliore le pacing global.

---

### 12. Validation Sémantique par Embeddings
**Statut : NON IMPLÉMENTÉ**

**Problème :** Certaines contradictions sont subtiles et échappent à l'analyse LLM.

```python
class SemanticContradictionDetector:
    """
    Utilise les embeddings pour détecter des contradictions subtiles
    que l'analyse textuelle pourrait manquer.
    """
    
    async def detect_semantic_conflicts(
        self, new_facts: List[str], established_facts: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Compare sémantiquement les nouveaux faits avec les faits établis.
        Exemple : "Marie déteste le chocolat" vs "Marie savoure son gâteau au chocolat"
        """
        new_embeddings = self.embed(new_facts)
        established_embeddings = self.embed(established_facts)
        
        # Recherche de contradictions via similarité négative
        # (faits qui parlent du même sujet mais disent le contraire)
        conflicts = []
        for i, new_emb in enumerate(new_embeddings):
            similar_established = self.find_similar(new_emb, established_embeddings)
            for j, sim_score in similar_established:
                if self.are_contradictory(new_facts[i], established_facts[j]):
                    conflicts.append({
                        "new_fact": new_facts[i],
                        "established_fact": established_facts[j],
                        "similarity_score": sim_score,
                        "conflict_confidence": self.compute_conflict_score(...)
                    })
        
        return conflicts
```

**Priorité : HAUTE** - Capture les contradictions que le LLM manque.

---

## 📋 Récapitulatif des Priorités

| # | Amélioration | Priorité | Effort | Impact |
|---|--------------|----------|--------|--------|
| 1 | Unification Pipeline/ConsistencyAnalyst | 🔴 HAUTE | Moyen | ⭐⭐⭐⭐ |
| 2 | Mémoire Récursive (Pyramide) | 🔴 HAUTE | Élevé | ⭐⭐⭐⭐⭐ |
| 3 | Promotion Auto → Story Bible | 🟡 MOYENNE | Moyen | ⭐⭐⭐ |
| 4 | Tracking Objets & Localisation | 🔴 HAUTE | Moyen | ⭐⭐⭐⭐ |
| 5 | Analyse Constance de Voix | 🟡 MOYENNE | Élevé | ⭐⭐⭐⭐ |
| 6 | Incohérences Intentionnelles | 🟡 MOYENNE | Faible | ⭐⭐⭐ |
| 7 | Chekhov's Guns Tracker | 🔴 HAUTE | Moyen | ⭐⭐⭐⭐⭐ |
| 8 | Validation POV | 🟡 MOYENNE | Faible | ⭐⭐⭐ |
| 9 | Détection Character Drift | 🔴 HAUTE | Moyen | ⭐⭐⭐⭐ |
| 10 | Timeline Non-Linéaire | 🟡 MOYENNE | Élevé | ⭐⭐⭐ |
| 11 | Arcs Émotionnels | 🟡 MOYENNE | Moyen | ⭐⭐⭐ |
| 12 | Validation Sémantique Embeddings | 🔴 HAUTE | Élevé | ⭐⭐⭐⭐⭐ |

---

## 🗺️ Roadmap Suggérée

### Phase 1 : Fondations (2-3 semaines)
1. ✅ Unification Pipeline/ConsistencyAnalyst
2. ✅ Tracking Objets & Localisation (extension Neo4j)
3. ✅ Chekhov's Guns Tracker

### Phase 2 : Mémoire Avancée (3-4 semaines)
4. ✅ Mémoire Récursive (Pyramide de Résumés)
5. ✅ Validation Sémantique par Embeddings
6. ✅ Promotion Auto → Story Bible

### Phase 3 : Qualité Narrative (2-3 semaines)
7. ✅ Détection Character Drift
8. ✅ Analyse Constance de Voix
9. ✅ Incohérences Intentionnelles

### Phase 4 : Features Avancées (3-4 semaines)
10. ✅ Validation POV
11. ✅ Timeline Non-Linéaire
12. ✅ Arcs Émotionnels

---

## 📝 Conclusion

**Votre analyse initiale est correcte et bien fondée.** Les 6 points identifiés adressent des lacunes réelles du système actuel.

Les 6 améliorations supplémentaires proposées (points 7-12) complètent votre vision en couvrant des aspects critiques des récits longs modernes :
- **Chekhov's Guns** et **Character Drift** sont particulièrement importants pour les novellas de 50+ chapitres
- **La validation sémantique par embeddings** est une technique de pointe qui capture des incohérences subtiles
- **La gestion du POV** et de la **timeline non-linéaire** sont essentielles pour certains genres (thriller, mystère, saga)

L'architecture existante de NovellaForge (Neo4j, ChromaDB, LangGraph) offre une excellente base pour implémenter ces améliorations de manière incrémentale.
