# Spécifications d'Améliorations - NovellaForge Pro

Cette spécification détaille les évolutions nécessaires pour passer NovellaForge d'un outil de niche à une plateforme professionnelle et "production-ready" pour la création de romans longs, gérant tous les genres littéraires, offrant un contrôle précis sur la longueur de l'œuvre, et introduisant un mode de génération "Lazy / Continu".

## 1. Ouverture à tous les genres littéraires

Actuellement, NovellaForge restreint les genres via une énumération (`Enum`) stricte dans le modèle `Project` (`app/models/project.py`) et dans le frontend (`GENRE_OPTIONS` dans `create-project-wizard.tsx`).

### Évolutions Backend :
*   **Modèle de données (`Project`) :**
    *   Le champ `genre` doit passer du type `Enum` au type libre `String(100)` ou `Text`.
    *   Alternativement, l'enum peut être conservée pour des catégories parentes, en ajoutant un champ `sub_genre` (String) pour la personnalisation totale. La solution recommandée (pour un maximum de flexibilité) est de **supprimer la contrainte stricte de l'enum sur la base de données**.
*   **Schémas de validation (Pydantic) :**
    *   Modifier `ProjectCreate` et `ProjectUpdate` pour accepter n'importe quelle chaîne de caractères pour le champ `genre` (avec une limite de caractères raisonnable, ex. max=100).
*   **Prompts LLM :**
    *   S'assurer que les prompts de génération de concept (`services/novella_service.py`) prennent en compte dynamiquement les genres textuels fournis sans s'attendre à une liste pré-établie.

### Évolutions Frontend :
*   **Wizard de Création (`CreateProjectWizard.tsx`) :**
    *   Remplacer le composant `<Select>` restreint par un composant combiné (Combobox / Select avec saisie libre).
    *   Fournir une liste de suggestions de genres courants (incluant Fantasy, Romance, etc.) mais autoriser l'utilisateur à taper "Science-Fiction cyberpunk", "Space Opera", ou tout autre genre personnalisé.

---

## 2. Flexibilité sur la Taille du Roman et des Chapitres

Le modèle actuel calcule ou limite uniquement `target_word_count`. Il manque la granularité pour choisir un nombre de chapitres ou leur taille respective.

### Évolutions Backend :
*   **Modèle de données (`Project`) :**
    Ajouter de nouveaux attributs dans `app/models/project.py` :
    *   `target_chapter_count` (Integer, nullable=True) : Nombre de chapitres souhaités pour boucler l'arc narratif.
    *   `target_chapter_length` (Integer, nullable=True) : Taille approximative désirée par chapitre (en mots).
*   **Moteur de Planification (`services/writing_pipeline.py` & `api/v1/endpoints/writing.py`) :**
    *   L'agent responsable de la structure (`pregenerate-plans`) utilisera `target_chapter_count` pour diviser l'arc narratif.
    *   Lors de la rédaction, injecter `target_chapter_length` dans les directives du prompt via la gestion de tokens (`WRITE_MAX_TOKENS`, et un encadrement LLM type "Ce chapitre doit faire environ X mots").

### Évolutions Frontend :
*   **Vue Création / Paramètres :**
    *   Ajouter des sliders virtuels ou des sélecteurs textuels simples :
        *   **Taille de l'œuvre :** Nouvelle (~15k), Roman Court (~50k), Roman Épique (~100k+).
        *   **Nombre de chapitres souhaités.**
        *   **Taille d'un chapitre :** Court (~1500 mots), Moyen (~3000 mots), Long (~5000+ mots).
    *   Ces formulaires mapperont en dur et enverront `target_chapter_length` et `target_chapter_count` pour surcharger la configuration standard.

---

## 3. Le "Lazy Mode" (Génération Récréative et Continue)

Le "Lazy Mode" est un mode immersif qui abstrait complètement l'édition du plan. L'utilisateur lance un roman avec un simple détail prompté et lit au fur et à mesure.

### Fonctionnement Utilisateur :
1. L'utilisateur indique ce qu'il a envie de lire (ex: "Je veux un roman court sur un hacker traqué à Tokyo un soir de pluie, l'atmosphère doit être angoissante").
2. L'outil gère la création en arrière-plan et propose le roman "au fur et à mesure qu'il demande le chapitre suivant".

### Évolutions Backend :
*   **Paramètres d'exécution :** Ajouter au modèle projet `generation_mode: str` (`standard`, `lazy`).
*   **Orchestration Lazy (Nouveau Endpoint) :**
    *   Au lieu du flux lourd `/pregenerate-plans` puis `/generate-chapter` (avec approbation), implémenter l'API `POST /api/v1/writing/lazy-next-chapter` ou `/api/v1/writing/lazy-generate`.
    *   Cette route s'occupe de faire un LLM-call rapide pour avancer l'histoire d'un cran ("Just-In-Time Planning"), l'écrire et l'enregistrer dans `Document` (Chapitre) immédiatement en court-circuitant l'étape d'approbation manuelle ou d'attente Celery/Redis complexes.
*   **Intégration Contexte (Mémoire) :**
    *   Le module `memory_service.py` (Neo4j/Chroma) sera interrogé avant le prompt de génération du *chapitre complet JIT* pour garder la continuité sans avoir de fichier de plan fixe.

### Évolutions Frontend :
*   **Interface de Lecture Fluide :**
    *   Contrairement à l'interface `editor/TipTap` très orientée écrivain, un nouveau composant d'UI (`ReaderMode.tsx`) est nécessaire.
    *   Bouton clair : **"Générer la suite"** (avec éventuellement une option ou zone de texte : *"Que voulez-vous qu'il se passe ensuite ?"*).
    *   La WebSocket existante `/ws/generate/{project_id}` crachera le stream directement dans l'UI de lecture et basculera au chapitre N+1 dès la fin.

---

## Plan d'Implémentation 

1. **Sprint 1 : Dé-verrouillage (Genres & Longueurs)**
   * Migration Alembic pour ajouter les champs `target_chapter_length`, `target_chapter_count`, et modifier le type `genre`.
   * Modifier `ProjectCreate` et `CreateProjectWizard.tsx`.
2. **Sprint 2 : Prompts d'Écriture**
   * Ajuster les agents LLM (`novella_service.py`, `writing_pipeline.py`) afin qu'ils respectent les limites de longueur personnalisées.
3. **Sprint 3 : Implémentation du Lazy Mode**
   * Backend : Implémenter le raccourci de génération globale sans planification pré-requise (`/lazy-generate`).
   * Frontend : Vue *Reader* centrée sur la lecture continue et la demande simple du prochain bloc avec génération masquée et streammée en temps réel.
