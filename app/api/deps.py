#Общие FastAPI-зависимости для api/v1/*
#
#Хранит синглтоны, собранные в main.py на старте: ProviderRegistry, EventLog, Router.
#Когда GUI сможет менять правила "на лету", сюда же добавится способ
#пересобирать Router с новым RouterConfig без перезапуска сервера.

from app.providers.registry import ProviderRegistry
from app.router.events import EventLog
from app.router.router import Router

_registry: ProviderRegistry | None = None
_event_log: EventLog | None = None
_router: Router | None = None


def set_registry(registry: ProviderRegistry) -> None:
    global _registry
    _registry = registry


def get_registry() -> ProviderRegistry:
    if _registry is None:
        raise RuntimeError("ProviderRegistry ещё не инициализирован")
    return _registry


def set_event_log(event_log: EventLog) -> None:
    global _event_log
    _event_log = event_log


def get_event_log() -> EventLog:
    if _event_log is None:
        raise RuntimeError("EventLog ещё не инициализирован")
    return _event_log


def set_router(router: Router) -> None:
    global _router
    _router = router


def get_router() -> Router:
    if _router is None:
        raise RuntimeError("Router ещё не инициализирован")
    return _router
