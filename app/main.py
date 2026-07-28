#Точка входа: создание FastAPI-приложения, подключение роутов, инициализация
#провайдеров, событийного лога и Router'а

from fastapi import FastAPI

from app.api.deps import set_event_log, set_registry, set_router
from app.api.v1 import chat, decisions, health
from app.core.config import settings
from app.core.logging import setup_logging
from app.providers.openrouter import OpenRouterProvider
from app.providers.registry import ProviderRegistry
from app.router.events import EventLog
from app.router.modules.base import BaseModule
from app.router.modules.searxng import SearXNGModule
from app.router.router import Router
from app.router.rules import RouterConfig

setup_logging(debug=settings.debug)

app = FastAPI(title=settings.app_name)

app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
app.include_router(decisions.router, prefix="/api/v1", tags=["decisions"])


@app.on_event("startup")
async def startup() -> None:
    registry = ProviderRegistry()

    if settings.openrouter_api_key:
        openrouter = OpenRouterProvider(
            api_key=settings.openrouter_api_key,
            site_name=settings.app_name,
        )
        await openrouter.ensure_model_catalog()
        registry.register(openrouter)

    event_log = EventLog(db_path=settings.events_db_path)

    modules: dict[str, BaseModule] = {}
    if settings.searxng_url:
        modules["searxng"] = SearXNGModule(base_url=settings.searxng_url)

    lane_router = Router(
        registry=registry,
        config=RouterConfig(),
        event_log=event_log,
        modules=modules,
    )

    set_registry(registry)
    set_event_log(event_log)
    set_router(lane_router)
