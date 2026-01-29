# Diagnostic : TTS et lecture de chapitre invisibles

**Date :** 29 janvier 2026
**Statut :** Constat + corrections proposees

---

## 1. Le probleme

L'utilisateur ne voit pas ou lire un chapitre et le lecteur TTS n'est visible nulle part sur l'interface.

Le code TTS est **implemente et fonctionnel** (14 fichiers, hooks, composants, persistence).
Mais l'UX le rend **invisible** : il faut 3 clics pour y acceder, il est cache derriere un toggle,
et aucun indicateur visuel ne signale sa presence.

---

## 2. Analyse du parcours utilisateur actuel

### Chemin A : Depuis le dashboard (le plus courant)

```
Dashboard
  └─ ProjectCard (collapse)
       └─ Cliquer pour deplier la card
            └─ Section "CHAPITRES"
                 └─ Selecteur dropdown "1. L'Appel de Naples"
                 └─ Bouton "Consulter le chapitre"   ← TOGGLE, pas navigation
                      └─ Le contenu du chapitre apparait inline
                      └─ Le LazyChapterAudioPlayer apparait AU-DESSUS du contenu
                           └─ Mais il est COLLAPSE par defaut (barre fine)
                           └─ L'utilisateur doit ENCORE cliquer pour le deplier
```

**Resultat :** 4 interactions pour voir le TTS, sans jamais savoir qu'il existe.

### Chemin B : Via les pages projet (inconnu de l'utilisateur)

```
Dashboard
  └─ Bouton "Consulter le concept" → /projects/[id]
       └─ Navigation "Chapitres" → /projects/[id]/chapters
            └─ Lien "Ouvrir" → /projects/[id]/chapters/[idx]
                 └─ Page dediee avec TTS + editeur TipTap
```

**Resultat :** 3 navigations de page, mais l'utilisateur ne sait pas que cette page existe.
Aucun bouton du dashboard ne pointe vers `/projects/[id]/chapters/[idx]`.

---

## 3. Problemes identifies

### P1. Aucun lien direct vers la page de lecture dediee

**Fichier :** `features/projects/project-card.tsx` (lignes 763-798)

Les boutons de la section "Chapitres" sont :
- "Generer le chapitre" → genere et affiche inline
- "Consulter le chapitre" → toggle inline (pas de navigation)
- "Telecharger le chapitre" → download fichier
- "Valider le chapitre" → approuve

**Aucun de ces boutons ne navigue vers `/projects/[id]/chapters/[idx]`**
ou il y a la page de lecture dediee avec editeur TipTap + TTS.

Le seul moyen d'atteindre la page de lecture est :
Dashboard → "Consulter le concept" → onglet "Chapitres" → clic "Ouvrir" sur un chapitre.

### P2. Le TTS est cache derriere un double toggle

**Fichier :** `features/projects/project-card.tsx` (lignes 800-808)

```tsx
{showChapter && activeChapterContent && (
  <AudioErrorBoundary>
    <LazyChapterAudioPlayer ... />
  </AudioErrorBoundary>
)}
```

Le player n'apparait que si :
1. L'utilisateur a clique "Consulter le chapitre" (`showChapter = true`)
2. Le contenu du chapitre est non-vide (`activeChapterContent` truthy)
3. Puis le player lui-meme demarre en mode collapse (ferme)

**Fichier :** `features/audio/chapter-audio-player.tsx`

Le composant `ChapterAudioPlayer` utilise un state `expanded` qui est `false` par defaut
(ou `defaultExpanded` prop, jamais passe a `true` depuis project-card.tsx).
Le player apparait donc comme une petite barre grise facilement ignoree.

### P3. Aucun indicateur visuel de la fonctionnalite TTS

Nulle part dans l'interface il n'y a :
- Une icone audio/haut-parleur visible
- Un label "Ecouter ce chapitre"
- Un badge "TTS disponible"
- Un bouton play visible dans la section chapitres

Le seul indice sont les badges "Audio 45%" dans la vue du plan (lignes 726-736),
mais ils n'apparaissent que si le plan est deplie ET que l'utilisateur a deja ecoute
un chapitre precedemment (progression sauvee en localStorage).

### P4. Le contenu du chapitre est affiche dans un espace trop restreint

**Fichier :** `features/projects/project-card.tsx` (lignes 821-831)

```tsx
{showChapter && chapterView && (
  <div className="rounded-2xl border border-stone-200 bg-white p-3">
    <div className="mt-2 whitespace-pre-wrap text-sm text-ink/80">
      {chapterView.content}
    </div>
  </div>
)}
```

Le chapitre est affiche en `text-sm` dans un div a l'interieur d'une card a l'interieur
du dashboard. Pas de pagination, pas de scroll limit, pas de mode lecture immersif.
Un chapitre de 3000+ mots s'affiche en entier dans la card, poussant tout le reste hors ecran.

### P5. La page de lecture dediee existe mais est deconnectee

**Fichier :** `app/projects/[id]/chapters/[idx]/page.tsx`

Cette page est bien implementee :
- Editeur TipTap pour le contenu
- `LazyChapterAudioPlayer` avec TTS
- Barre d'outils editeur
- Layout dedie avec navigation

Mais elle n'est accessible que via `/projects/[id]/chapters/` (la liste des chapitres),
qui est elle-meme accessible uniquement via l'onglet "Chapitres" dans le layout projet.

### P6. Pas de page de liste de chapitres accessible depuis le dashboard

**Fichier :** `app/projects/[id]/chapters/page.tsx`

Cette page liste les chapitres avec un lien "Ouvrir" vers la page de lecture dediee.
Mais depuis le dashboard, le bouton "Consulter le concept" pointe vers `/projects/[id]`
(la vue d'ensemble), pas vers `/projects/[id]/chapters`.

---

## 4. Corrections proposees

### C1. Ajouter un bouton "Lire le chapitre" qui navigue vers la page dediee

**Fichier a modifier :** `features/projects/project-card.tsx`

Dans la section chapitres (lignes 763-798), ajouter un bouton qui navigue vers
`/projects/${project.id}/chapters/${chapterIndex}` quand un chapitre genere est selectionne.

```
Boutons actuels :     [Generer] [Consulter] [Telecharger] [Valider]
Boutons proposes :    [Generer] [Lire & Ecouter ▶] [Telecharger] [Valider]
```

Le nouveau bouton "Lire & Ecouter" :
- Navigue vers `/projects/${project.id}/chapters/${chapterIndex}`
- N'apparait que si le chapitre est genere (`selectedChapterDoc` non null)
- Remplace ou complete "Consulter le chapitre" (l'inline toggle)
- Utilise `router.push()` au lieu d'un toggle state

### C2. Rendre le TTS visible avant le clic

**Fichier a modifier :** `features/projects/project-card.tsx`

Dans la liste des chapitres du plan (lignes 710-744), ajouter une icone haut-parleur
cliquable a cote de chaque chapitre genere. Au clic, naviguer vers la page de lecture.

Alternativement, dans la section "CHAPITRES" (ligne 750), ajouter un texte
d'indication :

```
CHAPITRES
Selectionnez un chapitre pour le lire et l'ecouter avec la synthese vocale.
```

### C3. Ouvrir le player en mode expanded par defaut

**Fichier a modifier :** `features/projects/project-card.tsx` (ligne 802)

Si on garde le mode inline, passer `defaultExpanded={true}` :

```tsx
<LazyChapterAudioPlayer
  chapterId={activeChapterId}
  chapterTitle={activeChapterTitle}
  content={activeChapterContent}
  defaultExpanded={true}        // ← ajouter
  className="mb-3"
/>
```

Meme chose dans `app/projects/[id]/chapters/[idx]/page.tsx` (ligne 76).

### C4. Ajouter un lien direct "Chapitres" dans la ProjectCard

**Fichier a modifier :** `features/projects/project-card.tsx`

A cote du bouton "Consulter le concept" (ligne 588-591), ajouter un bouton
"Voir les chapitres" qui navigue vers `/projects/${project.id}/chapters`.

```tsx
<Button
  variant="outline"
  size="sm"
  onClick={() => router.push(`/projects/${project.id}/chapters`)}
  disabled={documents.length === 0}
>
  Voir les chapitres
</Button>
```

### C5. Supprimer ou releguer l'affichage inline du chapitre

L'affichage inline du contenu complet du chapitre dans la project card est
problematique :
- Ca rend la card enorme (3000+ mots inseres dans le dashboard)
- Le TTS inline n'est pas une experience de lecture
- La page dediee fait mieux avec l'editeur TipTap

**Option recommandee :** Remplacer "Consulter le chapitre" par un apercu court
(200 premiers mots) avec un lien "Lire la suite" vers la page dediee.

### C6. Ajouter une icone audio dans la liste du plan

**Fichier a modifier :** `features/projects/project-card.tsx` (lignes 722-741)

Ajouter une icone haut-parleur (SVG ou Lucide) a cote du badge de progression audio
pour les chapitres generes. L'icone serait toujours visible (pas conditionnelle
a la progression) pour signaler que la fonctionnalite TTS existe.

---

## 5. Resume des fichiers concernes

| Fichier | Modification |
|---------|-------------|
| `features/projects/project-card.tsx` | Bouton navigation, icone audio, expanded par defaut, apercu court |
| `features/audio/chapter-audio-player.tsx` | Verifier le comportement de `defaultExpanded` |
| `app/projects/[id]/chapters/[idx]/page.tsx` | `defaultExpanded={true}` |
| `app/projects/[id]/chapters/page.tsx` | Aucune modif (deja fonctionnel) |

---

## 6. Schema de navigation corrige

```
Dashboard
  └─ ProjectCard
       └─ [Consulter le concept]     → /projects/[id]
       └─ [Voir les chapitres]       → /projects/[id]/chapters      ← NOUVEAU
       └─ Section CHAPITRES
            └─ Selecteur chapitre
            └─ [Lire & Ecouter ▶]    → /projects/[id]/chapters/[idx]  ← NOUVEAU
            └─ [Telecharger]
            └─ [Generer]
            └─ [Valider]
```

Le TTS devient accessible en **1 clic** (selecteur + "Lire & Ecouter")
au lieu de 4 interactions cachees.
