#Общие FastAPI-зависимости для api/v1/*
#
#На Этапе 1 просто отдаёт единственный ProviderRegistry, собранный в main.py.
#Когда появится Router (Этап 3), сюда же добавится зависимость get_router()

from app.providers.registry import ProviderRegistry

_registry: ProviderRegistry | None = None


def set_registry(registry: ProviderRegistry) -> None:
    global _registry
    _registry = registry


def get_registry() -> ProviderRegistry:
    if _registry is None:
        raise RuntimeError("ProviderRegistry ещё не инициализирован")
    return _registry
