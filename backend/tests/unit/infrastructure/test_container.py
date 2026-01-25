from app.infrastructure.di.container import Container
from app.infrastructure.di.scopes import Scope


class IService:
    pass


class ConcreteService(IService):
    pass


def test_singleton_returns_same_instance():
    container = Container()
    container.register(IService, lambda c: ConcreteService(), Scope.SINGLETON)
    instance1 = container.resolve(IService)
    instance2 = container.resolve(IService)
    assert instance1 is instance2


def test_transient_returns_new_instance():
    container = Container()
    container.register(IService, lambda c: ConcreteService(), Scope.TRANSIENT)
    instance1 = container.resolve(IService)
    instance2 = container.resolve(IService)
    assert instance1 is not instance2
