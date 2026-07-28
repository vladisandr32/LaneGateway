#Тесты Router'а: проверяем логику выбора модели, вызов модуля поиска,
#запись событий и откат по бюджету — всё на фейковом провайдере, без сети.

import pytest

from app.providers.base import ChatResult, CostEstimate, Message
from app.providers.registry import ProviderRegistry
from app.router.events import EventLog
from app.router.modules.base import BaseModule, ModuleResult
from app.router.router import Router
from app.router.rules import RouterConfig


class FakeProvider:
    name = "openrouter"

    def __init__(self, cost_usd: float = 0.001):
        self._cost_usd = cost_usd
        self.calls = []

    def estimate_cost(self, messages, model, max_tokens):
        return CostEstimate(
            prompt_tokens_est=10,
            completion_tokens_est=max_tokens,
            estimated_usd=self._cost_usd,
        )

    async def chat(self, messages, model, max_tokens=1000, temperature=0.7):
        self.calls.append((model, messages))
        return ChatResult(
            text="ответ модели",
            model=model,
            prompt_tokens=10,
            completion_tokens=20,
            cost_usd=self._cost_usd,
        )


class FakeSearchModule(BaseModule):
    name = "searxng"

    def __init__(self):
        self.called_with = None

    async def run(self, query: str) -> ModuleResult:
        self.called_with = query
        return ModuleResult(context_text="Результаты поиска: пример", cost_usd=0.0, meta={"results_count": 1})


@pytest.fixture
def router_setup(tmp_path):
    provider = FakeProvider()
    registry = ProviderRegistry()
    registry.register(provider)
    log = EventLog(db_path=str(tmp_path / "events.db"))
    search_module = FakeSearchModule()
    router = Router(registry=registry, config=RouterConfig(), event_log=log, modules={"searxng": search_module})
    return router, provider, search_module, log


@pytest.mark.asyncio
async def test_simple_short_message_uses_default_model(router_setup):
    router, provider, search_module, log = router_setup
    messages = [Message(role="user", content="Привет!")]

    result = await router.route(messages)

    assert result.model_used == RouterConfig().default_executor_model
    assert search_module.called_with is None  # нет ключевых слов поиска


@pytest.mark.asyncio
async def test_long_message_uses_complex_model(router_setup):
    router, provider, search_module, log = router_setup
    long_text = "текст " * 200  # заведомо длиннее порога сложности
    messages = [Message(role="user", content=long_text)]

    result = await router.route(messages)

    assert result.model_used == RouterConfig().complex_executor_model


@pytest.mark.asyncio
async def test_search_keyword_triggers_module(router_setup):
    router, provider, search_module, log = router_setup
    messages = [Message(role="user", content="какие последние новости про AI")]

    await router.route(messages)

    assert search_module.called_with is not None


@pytest.mark.asyncio
async def test_events_are_logged_for_request(router_setup):
    router, provider, search_module, log = router_setup
    messages = [Message(role="user", content="Привет!")]

    result = await router.route(messages)
    events = log.get_events(result.request_id)

    steps = [e.step for e in events]
    assert "RequestReceived" in steps
    assert "AnalyzerCalled" in steps
    assert "ModelSelected" in steps
    assert "ResponseGenerated" in steps


@pytest.mark.asyncio
async def test_budget_fallback_when_estimate_too_high(tmp_path):
    provider = FakeProvider(cost_usd=10.0)  # заведомо дороже лимита
    registry = ProviderRegistry()
    registry.register(provider)
    log = EventLog(db_path=str(tmp_path / "events.db"))
    config = RouterConfig(max_cost_per_request_usd=0.05)
    router = Router(registry=registry, config=config, event_log=log, modules={})

    long_text = "текст " * 200  # чтобы сначала выбралась дорогая complex-модель
    messages = [Message(role="user", content=long_text)]

    result = await router.route(messages)
    events = log.get_events(result.request_id)

    assert any(e.step == "BudgetFallback" for e in events)
    assert result.model_used == config.default_executor_model
