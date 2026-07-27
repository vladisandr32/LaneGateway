#OpenRouterProvider - BaseProvider поверх OpenRouter API chat()/vision()/embeddings() Документация: https://openrouter.ai/docs

import time
from typing import Any, Optional

import httpx

from .base import (
    BaseProvider,
    ChatResult,
    CostEstimate,
    EmbeddingsResult,
    ImageInput,
    Message,
    ProviderError,
    UnsupportedCapabilityError,
)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterProvider(BaseProvider):
    name = "openrouter"

    def __init__(
        self,
        api_key: str,
        site_url: str = "",
        site_name: str = "AI Gateway",
        timeout: float = 60.0,
        **config: Any,
    ):
        super().__init__(api_key=api_key, **config)
        self.site_url = site_url
        self.site_name = site_name
        self.timeout = timeout

        #Кэш каталога моделей /models на каждый запрос. Обновляется раз в CACHE_TTL секунд
        self._model_cache: dict[str, dict] = {}
        self._model_cache_ts: float = 0.0
        self._CACHE_TTL = 60 * 30  # 30 минут

    #HTTP-заголовки и работа с каталогом моделей

    def _headers(self) -> dict:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.site_url:
            headers["HTTP-Referer"] = self.site_url
        if self.site_name:
            headers["X-Title"] = self.site_name
        return headers

    async def ensure_model_catalog(self, force: bool = False) -> None:

        #Подтягивает /models с OpenRouter, если кэш устарел или пуст. Публичный метод — вызывать один раз при старте приложения (каталог не должен грузиться неявно перед каждым запросом)

        if (
            not force
            and self._model_cache
            and (time.time() - self._model_cache_ts) < self._CACHE_TTL
        ):
            return

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                f"{OPENROUTER_BASE_URL}/models", headers=self._headers()
            )
        if resp.status_code != 200:
            raise ProviderError(
                f"OpenRouter: не удалось получить список моделей "
                f"({resp.status_code}): {resp.text[:200]}"
            )

        data = resp.json().get("data", [])
        self._model_cache = {m["id"]: m for m in data}
        self._model_cache_ts = time.time()

    def _get_model_info(self, model: str) -> Optional[dict]:
        return self._model_cache.get(model)

    def _pricing(self, model: str) -> tuple[float, float]:
        """Возвращает (цена за prompt-токен, цена за completion-токен) в $."""
        info = self._get_model_info(model)
        if info is None:
            return 0.0, 0.0
        pricing = info.get("pricing", {})
        return (
            float(pricing.get("prompt", 0) or 0),
            float(pricing.get("completion", 0) or 0),
        )

    #chat()

    async def chat(
        self,
        messages: list[Message],
        model: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> ChatResult:
        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "max_tokens": max_tokens,
            "temperature": temperature,
            **kwargs,
        }
        return await self._call_chat_completions(payload, model)

    #vision()

    async def vision(
        self,
        messages: list[Message],
        images: list[ImageInput],
        model: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> ChatResult:
        if not self.supports_vision(model):
            raise UnsupportedCapabilityError(
                f"Модель {model} не поддерживает изображения (OpenRouter)"
            )

        #Формат OpenAI-style multimodal content: список частей text/image_url
        content_parts: list[dict] = []
        for m in messages:
            if m.content:
                content_parts.append({"type": "text", "text": m.content})

        image_parts = []
        for img in images:
            if img.url:
                image_parts.append(
                    {"type": "image_url", "image_url": {"url": img.url}}
                )
            elif img.base64_data:
                image_parts.append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{img.media_type};base64,{img.base64_data}"
                        },
                    }
                )

        #Последнее user-сообщение получает и текст, и картинки в одном content
        user_content = content_parts + image_parts

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": user_content}],
            "max_tokens": max_tokens,
            "temperature": temperature,
            **kwargs,
        }
        return await self._call_chat_completions(payload, model)

    #embeddings()

    async def embeddings(
        self,
        texts: list[str],
        model: str,
        **kwargs: Any,
    ) -> EmbeddingsResult:
        #OpenRouter на момент написания не имеет отдельного /embeddings эндпоинта для всех моделей — поддержка зависит от конкретной модели в каталоге. Проверяем через supports_embeddings()
        if not self.supports_embeddings(model):
            raise UnsupportedCapabilityError(
                f"Модель {model} не поддерживает embeddings через OpenRouter. "
                f"Для Memory (Этап 6) рассмотри отдельного embeddings-провайдера."
            )

        payload = {"model": model, "input": texts, **kwargs}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{OPENROUTER_BASE_URL}/embeddings",
                headers=self._headers(),
                json=payload,
            )
        if resp.status_code != 200:
            raise ProviderError(
                f"OpenRouter: ошибка embeddings ({resp.status_code}): {resp.text[:300]}"
            )

        data = resp.json()
        vectors = [item["embedding"] for item in data.get("data", [])]
        usage = data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        price_prompt, _ = self._pricing(model)
        cost_usd = round(prompt_tokens * price_prompt, 6)

        return EmbeddingsResult(
            vectors=vectors,
            model=model,
            prompt_tokens=prompt_tokens,
            cost_usd=cost_usd,
            raw_response=data,
        )

    #Вызов chat/completions (используется chat() и vision())

    async def _call_chat_completions(self, payload: dict, model: str) -> ChatResult:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers=self._headers(),
                json=payload,
            )

        if resp.status_code != 200:
            raise ProviderError(
                f"OpenRouter: ошибка запроса ({resp.status_code}): {resp.text[:300]}"
            )

        data = resp.json()
        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise ProviderError(f"OpenRouter: неожиданный формат ответа: {data}") from e

        usage = data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        price_prompt, price_completion = self._pricing(model)
        cost_usd = round(
            prompt_tokens * price_prompt + completion_tokens * price_completion, 6
        )

        return ChatResult(
            text=text,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost_usd,
            raw_response=data,
        )

    #Прогноз стоимости и capability-проверки

    def estimate_cost(
        self,
        messages: list[Message],
        model: str,
        max_tokens: int = 1000,
    ) -> CostEstimate:
        
        #Грубая оценка ДО вызова: считаем длину промпта по символам (~4 символа на токен — приблизительно, но для форкаста Budget Manager'аточнее и не нужно), а completion_tokens берём как max_tokens (худший случай)
        
        info = self._get_model_info(model)

        prompt_chars = sum(len(m.content) for m in messages)
        prompt_tokens_est = max(1, prompt_chars // 4)
        completion_tokens_est = max_tokens

        if info is None:
            return CostEstimate(
                estimated_usd=0.0,
                prompt_tokens_est=prompt_tokens_est,
                completion_tokens_est=completion_tokens_est,
                note="Каталог моделей ещё не загружен — вызовите ensure_model_catalog() заранее",
            )

        price_prompt, price_completion = self._pricing(model)
        estimated = (
            prompt_tokens_est * price_prompt + completion_tokens_est * price_completion
        )

        return CostEstimate(
            estimated_usd=round(estimated, 6),
            prompt_tokens_est=prompt_tokens_est,
            completion_tokens_est=completion_tokens_est,
        )

    def supports_vision(self, model: str) -> bool:
        info = self._get_model_info(model)
        if info is None:
            return False
        modality = info.get("architecture", {}).get("input_modalities", [])
        return "image" in modality

    def supports_embeddings(self, model: str) -> bool:
        info = self._get_model_info(model)
        if info is None:
            return False
        # OpenRouter помечает embedding-модели в architecture.output_modalities или через отдельный флаг в каталоге — точное поле уточнить по факту ответа /models при первом реальном запуске
        modality = info.get("architecture", {}).get("output_modalities", [])
        return "embedding" in modality or info.get("id", "").endswith("embedding")

    def supports_model(self, model: str) -> bool:
        return model in self._model_cache
