import pytest

from app.infrastructure.cqrs import Command, CommandHandler, CommandBus, Query, QueryHandler, QueryBus, Mediator


class Ping(Command):
    pass


class PingHandler(CommandHandler[Ping, str]):
    async def handle(self, command: Ping) -> str:
        return "pong"


class Fetch(Query):
    pass


class FetchHandler(QueryHandler[Fetch, int]):
    async def handle(self, query: Fetch) -> int:
        return 42


@pytest.mark.asyncio
async def test_command_bus_dispatch():
    bus = CommandBus()
    bus.register(Ping, PingHandler())
    result = await bus.dispatch(Ping())
    assert result == "pong"


@pytest.mark.asyncio
async def test_query_bus_dispatch():
    bus = QueryBus()
    bus.register(Fetch, FetchHandler())
    result = await bus.dispatch(Fetch())
    assert result == 42


@pytest.mark.asyncio
async def test_mediator_routes_to_buses():
    command_bus = CommandBus()
    query_bus = QueryBus()
    command_bus.register(Ping, PingHandler())
    query_bus.register(Fetch, FetchHandler())
    mediator = Mediator(command_bus, query_bus)

    assert await mediator.send(Ping()) == "pong"
    assert await mediator.send(Fetch()) == 42
