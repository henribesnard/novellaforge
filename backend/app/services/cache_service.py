import json
import hashlib
import logging
from typing import Optional, List, Union

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or settings.REDIS_URL
        try:
            self.redis: Optional[aioredis.Redis] = aioredis.from_url(
                self.redis_url, decode_responses=False
            )
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis = None

    @staticmethod
    def _project_key(prefix: str, project_id: str, data: Union[dict, str]) -> str:
        """Generate a cache key scoped to a project."""
        if isinstance(data, dict):
            content = json.dumps(data, sort_keys=True)
        else:
            content = str(data)
        hash_val = hashlib.sha256(content.encode()).hexdigest()[:16]
        return f"{prefix}:{project_id}:{hash_val}"

    async def get_memory_context(self, metadata: dict) -> Optional[str]:
        """Retrieve memory context from cache."""
        if not self.redis:
            return None
        try:
            project_id = str(metadata.get("project_id", "global"))
            key = self._project_key("memory_ctx", project_id, metadata)
            cached = await self.redis.get(key)
            return cached.decode("utf-8") if cached else None
        except Exception as e:
            logger.warning(f"Redis get error: {e}")
            return None

    async def set_memory_context(self, metadata: dict, context: str, ttl: int = 1800):
        """Cache memory context (default 30 min TTL)."""
        if not self.redis:
            return
        try:
            project_id = str(metadata.get("project_id", "global"))
            key = self._project_key("memory_ctx", project_id, metadata)
            await self.redis.setex(key, ttl, context.encode("utf-8"))
        except Exception as e:
            logger.warning(f"Redis set error: {e}")

    async def get_rag_results(self, query: str, project_id: str) -> Optional[List[str]]:
        """Retrieve RAG results from cache."""
        if not self.redis:
            return None
        try:
            key = self._project_key("rag", project_id, {"query": query})
            cached = await self.redis.get(key)
            return json.loads(cached.decode("utf-8")) if cached else None
        except Exception as e:
            logger.warning(f"Redis get error: {e}")
            return None

    async def set_rag_results(
        self, query: str, project_id: str, results: List[str], ttl: int = 3600
    ):
        """Cache RAG results (default 1h TTL)."""
        if not self.redis:
            return
        try:
            key = self._project_key("rag", project_id, {"query": query})
            await self.redis.setex(key, ttl, json.dumps(results).encode("utf-8"))
        except Exception as e:
            logger.warning(f"Redis set error: {e}")

    async def invalidate_project_cache(self, project_id: str):
        """Invalidate all cache entries for a specific project only."""
        if not self.redis:
            return
        try:
            keys_deleted = 0
            for prefix in ("rag", "memory_ctx"):
                pattern = f"{prefix}:{project_id}:*"
                async for key in self.redis.scan_iter(match=pattern, count=100):
                    await self.redis.delete(key)
                    keys_deleted += 1

            if keys_deleted > 0:
                logger.info(
                    f"Invalidated {keys_deleted} cache entries for project {project_id}"
                )
        except Exception as e:
            logger.warning(f"Redis invalidation error: {e}")

    async def close(self):
        """Close the Redis connection."""
        if self.redis:
            await self.redis.aclose()
