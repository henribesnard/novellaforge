"""Async Neo4j client wrapper."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Optional, Dict, Any, List

try:
    from neo4j import AsyncGraphDatabase
except ImportError:  # pragma: no cover
    AsyncGraphDatabase = None  # type: ignore


class AsyncNeo4jClient:
    def __init__(
        self,
        uri: str,
        user: str,
        password: str,
        database: Optional[str] = None,
    ) -> None:
        if AsyncGraphDatabase is None:
            raise RuntimeError("neo4j async driver not available")
        self._driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
        self._database = database

    @asynccontextmanager
    async def session(self):
        session = self._driver.session(database=self._database)
        try:
            yield session
        finally:
            await session.close()

    async def execute_write(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        async with self.session() as session:
            result = await session.run(query, parameters or {})
            return [record.data() async for record in result]

    async def close(self) -> None:
        await self._driver.close()
