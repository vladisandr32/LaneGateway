#ProviderRegistry — новый провайдер регистрируется, а не хардкодится
#
#Использование (в будущем, при старте приложения):
#   registry = ProviderRegistry()
#   registry.register(OpenRouterProvider(api_key=...))
#   provider = registry.get("openrouter")

from typing import Optional

from app.providers.base import BaseProvider


class ProviderRegistry:
    #Реестр всех подключённых провайдеров (openrouter/openai/ollama/anthropic/gemini/...)

    def __init__(self) -> None:
        self._providers: dict[str, BaseProvider] = {}

    def register(self, provider: BaseProvider) -> None:
        self._providers[provider.name] = provider

    def get(self, name: str) -> Optional[BaseProvider]:
        return self._providers.get(name)

    def all(self) -> list[BaseProvider]:
        return list(self._providers.values())

    def names(self) -> list[str]:
        return list(self._providers.keys())
