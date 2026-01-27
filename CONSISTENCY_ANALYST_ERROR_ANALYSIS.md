# Analyse Erreur "Consistency analyst failed"

**Date:** 2026-01-27
**Erreur:**
```
18:21:45,086 - writing_pipeline - ERROR - Consistency analyst failed:
18:21:45,533 - httpx - INFO - POST https://api.deepseek.com/v1/chat/completions "HTTP/1.1 200 OK"
```

---

## Diagnostic

### L'erreur est un `asyncio.TimeoutError`

Le message apres les deux points est **vide**. C'est la signature de `asyncio.TimeoutError` qui n'a pas de representation textuelle:

```python
>>> str(asyncio.TimeoutError())
''
```

Quand `writing_pipeline.py:699` fait:
```python
logger.error("Consistency analyst failed: %s", analyst_result)
```
`analyst_result` est un `asyncio.TimeoutError()` dont `str()` = `""`.

### Le POST 200 OK est le fallback, pas l'analyste

```
18:21:45,086 - ERROR  - Consistency analyst failed:     <- timeout
18:21:45,533 - INFO   - POST deepseek 200 OK           <- fallback LLM reussit
```

**447ms** entre les deux. C'est le fallback `_validate_with_llm()` (ligne 701-712) qui prend le relais et reussit rapidement.

---

## Cause racine: Double injection de contexte

Le probleme n'est **pas** le timeout en soi, mais la **taille du prompt** envoye a DeepSeek par l'analyste.

### Chaine d'appels

```
writing_pipeline.validate_continuity()
  -> consistency_analyst.execute(task_data={...}, context=project_context)
    -> _analyze_chapter_coherence(task_data, context)
      -> prompt = chapter_text + memory_context + story_bible + previous_chapters  [DEJA COMPLET]
      -> _call_api(prompt, context=project_context)                                [RE-AJOUTE TOUT]
        -> messages = prompt + "\n\nCONTEXTE:\n" + serialize(project_context)      [DOUBLON]
```

### Le doublon

**Etape 1** - `consistency_analyst.py:114-165` construit un prompt qui contient deja:
- Le chapitre complet
- La memoire de continuite
- La story bible formatee
- Les 5 derniers chapitres

**Etape 2** - `base_agent.py:57-62` re-ajoute le `project_context` en entier:
```python
if context:
    context_str = "\n\nCONTEXTE:\n"
    for key, value in context.items():
        if value:
            context_str += f"{key}: {value}\n"
```

`project_context` contient: project metadata, documents, story_bible, recent_chapter_summaries, etc. Tout est serialise en texte brut et ajoute au prompt.

### Resultat

| Composant | Tokens estimes |
|-----------|----------------|
| Prompt analyste (chapter + memory + bible + prev) | ~6000-10000 |
| Context re-injecte (project_context serialise) | ~5000-15000 |
| **Total envoye a DeepSeek** | **~11000-25000** |

### Pourquoi le fallback reussit en 0.4s

`_validate_with_llm()` (lignes 118-144) envoie un prompt **beaucoup plus leger**:
- Pas de double injection de contexte
- Pas de serialisation brute du project_context
- Utilise `self.llm_client` (DeepSeekClient) qui est deja initialise et potentiellement avec un pool de connexions

---

## Pourquoi le log est inutile

**Fichier:** `writing_pipeline.py:699`
```python
logger.error("Consistency analyst failed: %s", analyst_result)
```

**Problemes:**
1. Pas de `exc_info=True` -> pas de stack trace
2. `str(asyncio.TimeoutError())` = `""` -> message vide
3. On ne sait pas si c'est un timeout, une erreur reseau, ou autre

---

## Corrections

### Correction 1 - Supprimer la double injection de contexte (CRITIQUE)

**Fichier:** `backend/app/services/agents/consistency_analyst.py:167`

```python
# AVANT - context passe a _call_api => re-injecte dans le prompt
response = await self._call_api(prompt, context, temperature=0.2)

# APRES - ne pas passer context car le prompt contient deja tout
response = await self._call_api(prompt, context=None, temperature=0.2)
```

**Impact:** Reduction de ~50% de la taille du prompt envoye a DeepSeek. L'API repondra beaucoup plus vite et ne devrait plus timeout.

### Correction 2 - Ameliorer le logging du timeout

**Fichier:** `backend/app/services/writing_pipeline.py:697-699`

```python
# AVANT
if isinstance(analyst_result, Exception):
    analysis_error = str(analyst_result)
    logger.error("Consistency analyst failed: %s", analyst_result)

# APRES
if isinstance(analyst_result, Exception):
    error_type = type(analyst_result).__name__
    error_msg = str(analyst_result) or "(no message)"
    analysis_error = f"{error_type}: {error_msg}"
    logger.error(
        "Consistency analyst failed [%s]: %s",
        error_type,
        error_msg,
        exc_info=True,
    )
```

**Resultat dans les logs:**
```
Consistency analyst failed [TimeoutError]: (no message)
```

### Correction 3 (optionnelle) - Tronquer le contexte dans base_agent

**Fichier:** `backend/app/services/agents/base_agent.py:57-62`

Ajouter une limite de taille pour eviter les prompts geants:

```python
context_str = ""
if context:
    context_str = "\n\nCONTEXTE:\n"
    for key, value in context.items():
        if value:
            value_str = str(value)
            if len(value_str) > 2000:
                value_str = value_str[:2000] + "... [tronque]"
            context_str += f"{key}: {value_str}\n"
```

---

## Resume des actions

| Priorite | Action | Fichier | Impact |
|----------|--------|---------|--------|
| **CRITIQUE** | Supprimer double injection contexte | `consistency_analyst.py:167` | Prompt 50% plus petit |
| **HAUTE** | Ameliorer logging timeout | `writing_pipeline.py:697-699` | Diagnostic facilite |
| **MOYENNE** | Tronquer contexte dans base_agent | `base_agent.py:57-62` | Protection contre prompts geants |

---

## Conclusion

L'erreur "Consistency analyst failed" est causee par un **`asyncio.TimeoutError`** du a un **prompt surdimensionne**. Le contexte du projet est injecte **deux fois**: une fois dans le prompt de l'analyste, et une fois par `base_agent._call_api()` qui serialise le `context` en entier.

La correction principale est de passer `context=None` dans l'appel `_call_api()` de `consistency_analyst.py`, car le prompt construit manuellement contient deja toutes les informations necessaires.

Cela devrait ramener le temps de l'analyste de **>60s (timeout)** a **~10-20s** et eliminer l'erreur.
