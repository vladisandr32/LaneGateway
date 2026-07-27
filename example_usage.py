#Пример использования OpenRouterProvider.
#
#Запуск:
#    export OPENROUTER_API_KEY=sk-or-...
#   python example_usage.py

import asyncio
import os

from providers.base import Message
from providers.openrouter import OpenRouterProvider


async def main():
    provider = OpenRouterProvider(
        api_key=os.environ["OPENROUTER_API_KEY"],
        site_name="AI Router (dev)",
    )

    #Каталог моделей (цены, модальности) нужно подтянуть один раз при старте
    await provider.ensure_model_catalog()

    messages = [
        Message(role="user", content="Привет! Скажи одно слово: тест прошёл.")
    ]

    model = "deepseek/deepseek-chat"  # пример — замени на нужный ID из OpenRouter

    #Прогноз стоимости (для Budget Manager)
    estimate = provider.estimate_cost(messages, model=model, max_tokens=50)
    print("Прогноз стоимости:", estimate)

    if not provider.supports_model(model):
        print(f"Модель {model} не найдена в каталоге OpenRouter")
        return

    #Реальный вызов
    result = await provider.chat(messages, model=model, max_tokens=50)
    print("Ответ:", result.text)
    print("Токены:", result.prompt_tokens, "/", result.completion_tokens)
    print("Фактическая стоимость:", result.cost_usd)


if __name__ == "__main__":
    asyncio.run(main())
