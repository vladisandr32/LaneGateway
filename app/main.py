#Точка входа: создание FastAPI-приложения, подключение роутов, инициализация провайдеров

from fastapi import FastAPI

from app.api.deps import set_registry
from app.api.v1 import chat, health
from app.core.config import settings
from app.core.logging import setup_logging
from app.providers.openrouter import OpenRouterProvider
from app.providers.registry import ProviderRegistry

setup_logging(debug=settings.debug)

app = FastAPI(title=settings.app_name)

app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])


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

    set_registry(registry)
