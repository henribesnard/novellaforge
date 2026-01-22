# Corrections des Erreurs d'Import - NovellaForge Backend

## Erreur Principale

```
ImportError: cannot import name 'get_user_from_token' from 'app.core.security'
```

**Fichier source:** `backend/app/api/v1/endpoints/writing.py` ligne 14
**Fichier cible:** `backend/app/core/security.py`

## Cause

Lors de l'implémentation de l'endpoint WebSocket pour la génération en streaming, une fonction `get_user_from_token` a été importée mais n'existe pas dans `security.py`.

L'import problématique dans `writing.py`:
```python
from app.core.security import get_current_active_user, get_user_from_token
```

## Solutions

### Solution 1: Ajouter la fonction manquante dans `security.py` (Recommandée)

Ajouter cette fonction à la fin de `backend/app/core/security.py`:

```python
async def get_user_from_token(token: str, db: AsyncSession) -> Optional[User]:
    """
    Get user from a raw JWT token string.

    This is useful for WebSocket authentication where we can't use
    the standard OAuth2 dependency injection.

    Args:
        token: JWT token string
        db: Database session

    Returns:
        User if token is valid and user exists, None otherwise
    """
    token_data = decode_token(token)
    if token_data is None or token_data.sub is None:
        return None

    user = await db.get(User, token_data.sub)
    if user is None or not user.is_active:
        return None

    return user
```

### Solution 2: Modifier l'endpoint WebSocket pour ne pas utiliser cette fonction

Modifier `backend/app/api/v1/endpoints/writing.py`:

**Avant (ligne 14):**
```python
from app.core.security import get_current_active_user, get_user_from_token
```

**Après:**
```python
from app.core.security import get_current_active_user, decode_token
from app.models.user import User
```

Et remplacer dans la fonction `websocket_generate_chapter` (vers ligne 215-225):

**Avant:**
```python
try:
    user = await get_user_from_token(token, db)
    if not user:
        await websocket.send_json({"type": "error", "message": "Invalid token"})
        await websocket.close()
        return
except Exception:
    await websocket.send_json({"type": "error", "message": "Authentication failed"})
    await websocket.close()
    return
```

**Après:**
```python
try:
    token_data = decode_token(token)
    if token_data is None or token_data.sub is None:
        await websocket.send_json({"type": "error", "message": "Invalid token"})
        await websocket.close()
        return

    user = await db.get(User, token_data.sub)
    if not user or not user.is_active:
        await websocket.send_json({"type": "error", "message": "Invalid token"})
        await websocket.close()
        return
except Exception:
    await websocket.send_json({"type": "error", "message": "Authentication failed"})
    await websocket.close()
    return
```

## Résumé des Fichiers à Modifier

| Fichier | Action |
|---------|--------|
| `backend/app/core/security.py` | Ajouter `get_user_from_token()` (Solution 1) |
| **OU** | |
| `backend/app/api/v1/endpoints/writing.py` | Modifier l'import et le code WebSocket (Solution 2) |

## Commande pour Redémarrer

Après correction:
```bash
docker-compose down
docker-compose up -d --build
```

## Notes Additionnelles

### Warnings (non-bloquants)

1. **Pydantic warning sur `model_name`:**
   - Non-bloquant, vient de LangChain/HuggingFace
   - Peut être ignoré

2. **ONNX Runtime GPU warning:**
   - Normal si pas de GPU configuré
   - Non-bloquant

Ces warnings n'empêchent pas le démarrage, seule l'erreur d'import est bloquante.
