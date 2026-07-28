#Базовые тесты для OpenRouterProvider — capability-проверки без реальных сетевых вызовов
#(модельный каталог подставляется вручную вместо ensure_model_catalog())

from app.providers.openrouter import OpenRouterProvider


def make_provider_with_fake_catalog() -> OpenRouterProvider:
    provider = OpenRouterProvider(api_key="test-key")
    provider._model_cache = {
        "vision-model": {
            "id": "vision-model",
            "pricing": {"prompt": "0.000001", "completion": "0.000002"},
            "architecture": {"input_modalities": ["text", "image"]},
        },
        "text-model": {
            "id": "text-model",
            "pricing": {"prompt": "0.0000005", "completion": "0.000001"},
            "architecture": {"input_modalities": ["text"]},
        },
    }
    provider._model_cache_ts = 0.0
    return provider


def test_supports_vision_true_for_vision_model():
    provider = make_provider_with_fake_catalog()
    assert provider.supports_vision("vision-model") is True


def test_supports_vision_false_for_text_only_model():
    provider = make_provider_with_fake_catalog()
    assert provider.supports_vision("text-model") is False


def test_supports_model_unknown_model_is_false():
    provider = make_provider_with_fake_catalog()
    assert provider.supports_model("unknown-model") is False


def test_estimate_cost_uses_max_tokens_as_worst_case():
    from app.providers.base import Message

    provider = make_provider_with_fake_catalog()
    messages = [Message(role="user", content="a" * 40)]  # ~10 токенов промпта

    estimate = provider.estimate_cost(messages, model="text-model", max_tokens=100)

    assert estimate.completion_tokens_est == 100
    assert estimate.prompt_tokens_est == 10
    assert estimate.estimated_usd > 0
