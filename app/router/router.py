#Router — сердце двухступенчатой логики:
#
#   запрос -> анализатор (дёшево) -> нужные модули (поиск и т.д.) -> исполнитель (выбранная модель)
#
#Каждый шаг пишется в EventLog как отдельное событие с причиной и стоимостью —
#это и есть основа для Decision Replay в будущем GUI.
#
#На текущем этапе анализ "сложности" и "нужен ли поиск" — эвристики
#(app/router/rules.py), а не отдельный вызов LLM-классификатора. Это
#сознательное упрощение MVP: сама структура (analyzer step -> module step ->
#executor step, с событиями на каждом) уже правильная, и настоящий
#LLM-анализатор можно подставить в analyze() позже, не трогая остальной Router.

from dataclasses import dataclass

from app.providers.base import Message
from app.providers.registry import ProviderRegistry
from app.router.events import EventLog, RouteEvent, new_request_id
from app.router.modules.base import BaseModule
from app.router.rules import RouterConfig, looks_complex, needs_search


@dataclass
class RouteResult:
    request_id: str
    text: str
    model_used: str
    total_cost_usd: float


class Router:
    def __init__(
        self,
        registry: ProviderRegistry,
        config: RouterConfig,
        event_log: EventLog,
        modules: dict[str, BaseModule] | None = None,
    ) -> None:
        self._registry = registry
        self._config = config
        self._events = event_log
        self._modules = modules or {}

    async def route(self, messages: list[Message], provider_name: str = "openrouter") -> RouteResult:
        request_id = new_request_id()
        provider = self._registry.get(provider_name)
        if provider is None:
            raise RuntimeError(f"Провайдер {provider_name} не зарегистрирован")

        user_text = messages[-1].content if messages else ""

        self._events.log(RouteEvent(
            request_id=request_id,
            step="RequestReceived",
            detail={"provider": provider_name, "message_preview": user_text[:200]},
        ))

        #Этап 1: анализ (пока эвристика, см. rules.py)
        is_complex = looks_complex(user_text, self._config)
        should_search = needs_search(user_text, self._config)

        self._events.log(RouteEvent(
            request_id=request_id,
            step="AnalyzerCalled",
            detail={
                "analyzer_model": self._config.analyzer_model,
                "is_complex": is_complex,
                "needs_search": should_search,
                "reason": "эвристика по длине текста и ключевым словам (MVP)",
            },
        ))

        #Этап 2: модули (сейчас только поиск)
        extra_context = ""
        if should_search:
            search_module = self._modules.get("searxng")
            if search_module is None:
                self._events.log(RouteEvent(
                    request_id=request_id,
                    step="ModuleSkipped",
                    detail={"module": "searxng", "reason": "модуль не сконфигурирован"},
                ))
            else:
                result = await search_module.run(user_text)
                extra_context = result.context_text
                self._events.log(RouteEvent(
                    request_id=request_id,
                    step="ModuleCalled",
                    detail={"module": "searxng", **result.meta},
                    cost_usd=result.cost_usd,
                ))

        #Этап 3: выбор модели-исполнителя
        if is_complex:
            model = self._config.complex_executor_model
            reason = f"длина запроса >= {self._config.complexity_length_threshold} символов"
        else:
            model = self._config.default_executor_model
            reason = "запрос простой по эвристике"

        self._events.log(RouteEvent(
            request_id=request_id,
            step="ModelSelected",
            detail={"model": model, "reason": reason},
        ))

        #Собираем финальные сообщения с учётом контекста от модулей
        final_messages = list(messages)
        if extra_context:
            final_messages.insert(-1, Message(role="system", content=extra_context))

        #Проверка бюджета до отправки
        estimate = provider.estimate_cost(final_messages, model=model, max_tokens=1000)
        if estimate.estimated_usd > self._config.max_cost_per_request_usd:
            fallback_model = self._config.default_executor_model
            self._events.log(RouteEvent(
                request_id=request_id,
                step="BudgetFallback",
                detail={
                    "original_model": model,
                    "fallback_model": fallback_model,
                    "estimated_usd": estimate.estimated_usd,
                    "limit_usd": self._config.max_cost_per_request_usd,
                },
            ))
            model = fallback_model

        #Этап 4: вызов исполнителя
        result = await provider.chat(final_messages, model=model, max_tokens=1000)

        self._events.log(RouteEvent(
            request_id=request_id,
            step="ResponseGenerated",
            detail={
                "model": result.model,
                "prompt_tokens": result.prompt_tokens,
                "completion_tokens": result.completion_tokens,
            },
            cost_usd=result.cost_usd,
        ))

        total_cost = self._events.total_cost(request_id)

        return RouteResult(
            request_id=request_id,
            text=result.text,
            model_used=result.model,
            total_cost_usd=total_cost,
        )
