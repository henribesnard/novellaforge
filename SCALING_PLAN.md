# NovellaForge - Plan de dimensionnement et collaboration multi-comptes

Ce document liste tout ce qu'il reste a faire pour supporter:
- la generation de chapitres en parallele sur plusieurs projets,
- le travail simultane de plusieurs comptes sur un meme projet,
- la mise a l'echelle de l'infra et des services.

## Objectifs
- Rendre la generation robuste et asynchrone (jobs + suivi).
- Autoriser la collaboration multi-comptes avec roles et permissions.
- Garantir l'absence de conflits (verrous + versioning).
- Dimensionner l'infra pour la charge (API, workers, DB, queues).

## Constats (etat actuel)
- Generation synchrone dans l'API, pas de file de jobs.
- Acces projet base sur owner unique.
- Pas de verrou distribue par projet.
- Risque de collisions sur order_index en generation simultanee.
- Pas d'observabilite ni de suivi de charge.

## Backlog detaille

### 1) Jobs de generation (asynchrone)
- [ ] Creer un modele `chapter_generation_jobs` (status, payload, result_doc_id, error, timestamps).
- [ ] Exposer un endpoint `POST /writing/generate-chapter` qui cree un job et retourne un `job_id`.
- [ ] Ajouter `GET /writing/jobs/{id}` pour le suivi (status/progress/result).
- [ ] Ajouter `POST /writing/jobs/{id}/cancel` si possible.
- [ ] Migrer la logique actuelle vers une tache Celery.
- [ ] Gerer les retries, timeouts et erreurs (statuts clairs).

### 2) Concurrence par projet
- [ ] Ajouter un verrou distribue par projet (Redis lock ou pg_advisory_lock).
- [ ] Rendre l'increment de `order_index` atomique (transaction + lock).
- [ ] Ajouter une cle d'idempotence pour eviter les doubles generations.
- [ ] Interdire 2 generations actives pour un meme projet si verrou.

### 3) Collaboration multi-comptes
- [ ] Ajouter une table `project_members` (project_id, user_id, role).
- [ ] Definir les roles: owner, editor, viewer.
- [ ] Ajouter le flux d'invitation (creation, acceptation, refus).
- [ ] Mettre a jour tous les controles d'acces pour verifier membre + role.
- [ ] Ajouter un event log minimal (qui a change quoi).

### 4) Conflits d'edition
- [ ] Ajouter un champ `version` ou `updated_at` pour optimistic locking.
- [ ] Refuser les updates si la version est obsolette.
- [ ] Ajouter un "soft lock" d'edition (ex: metadonnees "editing_by").
- [ ] Etendre le versioning documents si besoin (chapitre, plan, concept).

### 5) Indexation et memoire
- [ ] Decoupler l'indexation RAG en job (queue separable).
- [ ] Eviter la reindexation simultanee sur un meme projet.
- [ ] Ajouter une strategy de reindexation partielle (only changed docs).

### 6) Observabilite et limites
- [ ] Rate limiting par user/projet (API + jobs).
- [ ] Metriques: temps moyen de generation, taux d'erreur, files d'attente.
- [ ] Logs structurees par job_id + project_id.
- [ ] Monitoring Celery (ex: Flower) + alerting.

### 7) Dimensionnement infra
- [ ] Scaler l'API horizontalement (plusieurs instances).
- [ ] Scaler les workers Celery (concurrency et nombre).
- [ ] Ajuster pool DB + max_connections (eventuellement pgbouncer).
- [ ] Isoler les queues (generation vs indexation vs nettoyage).
- [ ] Stockage uploads sur S3 ou volume partage.
- [ ] Redis HA si besoin (sentinel/cluster).

### 8) Tests et qualite
- [ ] Tests de concurrence (jobs + verrous).
- [ ] Tests de permissions multi-comptes.
- [ ] Tests de reprise apres echec (job retry, timeouts).
- [ ] Tests de migration et compatibilite.

### 9) Deploiement et rollout
- [ ] Plan de migration DB (alembic) + backfill.
- [ ] Feature flags pour activer les jobs progressivement.
- [ ] Documentation d'exploitation (runbooks).

## Questions ouvertes
- Multi-tenant: isolation stricte par organisation ou simple partage de projet?
- Politique de quotas (jobs par minute, par user, par projet)?
- Politique de retention des jobs et des logs?

## Definition of Done (MVP)
- Generation asynchrone stable avec statut consultable.
- Verrouillage par projet empchant les collisions.
- Roles multi-comptes en lecture/ecriture.
- Tests critiques passes (permissions + concurrence).
