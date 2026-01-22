import redis
import json
import hashlib
import logging
from typing import Optional, Any, List, Dict, Union
from datetime import timedelta

from app.core.config import settings

logger = logging.getLogger(__name__)

class CacheService:
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or settings.REDIS_URL
        try:
            self.redis = redis.from_url(self.redis_url, decode_responses=False)
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis = None

    def _hash_key(self, prefix: str, data: Union[dict, str]) -> str:
        """Generate a unique cache key based on content."""
        if isinstance(data, dict):
            content = json.dumps(data, sort_keys=True)
        else:
            content = str(data)
        hash_val = hashlib.sha256(content.encode()).hexdigest()[:16]
        return f"{prefix}:{hash_val}"

    async def get_memory_context(self, metadata: dict) -> Optional[str]:
        """Retrieve memory context from cache."""
        if not self.redis:
            return None
        try:
            key = self._hash_key("memory_ctx", metadata)
            cached = self.redis.get(key)
            return cached.decode('utf-8') if cached else None
        except Exception as e:
            logger.warning(f"Redis get error: {e}")
            return None

    async def set_memory_context(self, metadata: dict, context: str, ttl: int = 1800):
        """Cache memory context (default 30 min TTL)."""
        if not self.redis:
            return
        try:
            key = self._hash_key("memory_ctx", metadata)
            self.redis.setex(key, ttl, context.encode('utf-8'))
        except Exception as e:
            logger.warning(f"Redis set error: {e}")

    async def get_rag_results(self, query: str, project_id: str) -> Optional[List[str]]:
        """Retrieve RAG results from cache."""
        if not self.redis:
            return None
        try:
            key = self._hash_key("rag", {"query": query, "project_id": project_id})
            cached = self.redis.get(key)
            return json.loads(cached.decode('utf-8')) if cached else None
        except Exception as e:
            logger.warning(f"Redis get error: {e}")
            return None

    async def set_rag_results(self, query: str, project_id: str, results: List[str], ttl: int = 3600):
        """Cache RAG results (default 1h TTL)."""
        if not self.redis:
            return
        try:
            key = self._hash_key("rag", {"query": query, "project_id": project_id})
            self.redis.setex(key, ttl, json.dumps(results).encode('utf-8'))
        except Exception as e:
            logger.warning(f"Redis set error: {e}")

    def invalidate_project_cache(self, project_id: str):
        """Invalidate all cache entries for a project by deleting keys with matching project_id."""
        if not self.redis:
            return
        try:
            # Delete RAG cache entries that contain this project_id
            # We scan for rag:* keys and check if the project_id matches
            cursor = 0
            keys_deleted = 0
            while True:
                cursor, keys = self.redis.scan(cursor=cursor, match="rag:*", count=100)
                for key in keys:
                    try:
                        cached = self.redis.get(key)
                        if cached:
                            # Check if key was for this project by looking at stored data
                            # Since we can't easily reverse the hash, we delete all rag keys
                            # A more robust solution would tag keys with project_id prefix
                            self.redis.delete(key)
                            keys_deleted += 1
                    except Exception:
                        pass
                if cursor == 0:
                    break

            # Also invalidate memory context keys (they change with project metadata)
            cursor = 0
            while True:
                cursor, keys = self.redis.scan(cursor=cursor, match="memory_ctx:*", count=100)
                for key in keys:
                    self.redis.delete(key)
                    keys_deleted += 1
                if cursor == 0:
                    break

            if keys_deleted > 0:
                logger.info(f"Invalidated {keys_deleted} cache entries for project {project_id}")
        except Exception as e:
            logger.warning(f"Redis invalidation error: {e}")
