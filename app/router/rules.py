#Конфигурация роутера и простые правила принятия решений.
#
#Сейчас это Python-объект с дефолтами (плюс возможность передать свои
#значения). Именно эта конфигурация в будущем станет тем, что можно
#редактировать через GUI, не трогая код — поэтому она сознательно вынесена
#в отдельный плоский dataclass, а не размазана по коду роутера.

import re
from dataclasses import dataclass, field


@dataclass
class RouterConfig:
    #Модель-анализатор — дешёвая/быстрая, отвечает за классификацию запроса
    analyzer_model: str = "deepseek/deepseek-chat"

    #Модель-исполнитель по умолчанию — используется, если ничего особого не требуется
    default_executor_model: str = "deepseek/deepseek-chat"

    #Модель-исполнитель для "сложных" запросов
    complex_executor_model: str = "anthropic/claude-sonnet-4"

    #Модель-исполнитель для запросов с изображением
    vision_executor_model: str = "google/gemini-2.5-flash"

    #Порог длины сообщения (в символах), после которого запрос считается "сложным"
    #— грубая эвристика для MVP, до появления настоящей классификации через analyzer_model
    complexity_length_threshold: int = 600

    #Ключевые слова, намекающие на необходимость свежих данных из интернета
    search_keywords: list[str] = field(
        default_factory=lambda: [
            "сегодня", "сейчас", "последн", "новост", "актуальн", "202",
            "today", "latest", "current", "news",
        ]
    )

    #Включён ли модуль веб-поиска вообще (глобальный переключатель — в GUI это будет тумблер)
    search_enabled: bool = True

    #Максимальный бюджет на один запрос в долларах — выше него роутер обязан
    #откатиться на самую дешёвую модель независимо от сложности
    max_cost_per_request_usd: float = 0.05


def looks_complex(text: str, config: RouterConfig) -> bool:
    #Грубая эвристика сложности для MVP: длина сообщения.
    #Позже сюда встанет вызов analyzer_model вместо чистой эвристики.
    return len(text) >= config.complexity_length_threshold


def needs_search(text: str, config: RouterConfig) -> bool:
    if not config.search_enabled:
        return False
    lowered = text.lower()
    return any(re.search(re.escape(kw), lowered) for kw in config.search_keywords)
