"""JWT token blacklist backed by Redis."""
import logging
from typing import Optional

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

_redis: Optional[aioredis.Redis] = None


def _get_redis() -> Optional[aioredis.Redis]:
    global _redis
    if _redis is None:
        try:
            _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        except Exception as e:
            logger.error(f"Failed to connect to Redis for token blacklist: {e}")
    return _redis


async def blacklist_token(token: str) -> None:
    """Add a token to the blacklist until it would naturally expire."""
    r = _get_redis()
    if not r:
        return
    try:
        ttl = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        await r.setex(f"token_blacklist:{token}", ttl, "1")
    except Exception as e:
        logger.warning(f"Failed to blacklist token: {e}")


async def is_token_blacklisted(token: str) -> bool:
    """Check if a token has been blacklisted."""
    r = _get_redis()
    if not r:
        return False
    try:
        return await r.exists(f"token_blacklist:{token}") > 0
    except Exception as e:
        logger.warning(f"Failed to check token blacklist: {e}")
        return False
