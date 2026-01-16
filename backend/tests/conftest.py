import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/test_db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")
os.environ.setdefault("DEEPSEEK_API_KEY", "test-key")
os.environ.setdefault("SECRET_KEY", "test-secret-key-1234567890abcdef")

try:
    import slowapi  # noqa: F401
except ModuleNotFoundError:
    import types

    slowapi_module = types.ModuleType("slowapi")

    class DummyLimiter:
        def __init__(self, *args, **kwargs):
            pass

        def limit(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator

    slowapi_module.Limiter = DummyLimiter
    sys.modules["slowapi"] = slowapi_module

    slowapi_util = types.ModuleType("slowapi.util")

    def get_remote_address(request):
        return "0.0.0.0"

    slowapi_util.get_remote_address = get_remote_address
    sys.modules["slowapi.util"] = slowapi_util
