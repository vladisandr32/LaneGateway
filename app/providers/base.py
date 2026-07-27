#BaseProvider: схема chat() / embeddings() / vision() вместо generate() / supports_vision()

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional

@dataclass
class Message:
    #Cообщение в диалоге
    role: str  # "user" | "assistant" | "system"
    content: str


@dataclass
class ImageInput:
    #Изображение в vision()
    url: Optional[str] = None          # либо URL
    base64_data: Optional[str] = None  # либо base64
    media_type: str = "image/jpeg"

@dataclass
class ChatResult:
    #Результат chat() или vision()
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    raw_response: Optional[dict] = None


@dataclass
class EmbeddingsResult:
    #Результат embeddings()
    vectors: list[list[float]]
    model: str
    prompt_tokens: int
    cost_usd: float
    raw_response: Optional[dict] = None


@dataclass
class CostEstimate:
    #Прогноз стоимости запроса
    estimated_usd: float
    prompt_tokens_est: int
    completion_tokens_est: int
    note: str = ""


class ProviderError(Exception):
    #Базовая ошибка провайдера
    pass


class UnsupportedCapabilityError(ProviderError):
    #Не поддерживает запрошенную возможность
    pass


class BaseProvider(ABC):
    
    #Абстрактный интерфейс провайдера
    #
    #Обязательные методы:
    #  - chat()          — обычный текстовый диалог
    #  - embeddings()    — векторизация текста (для Memory)
    #  - vision()        — диалог с изображениями
    #  - estimate_cost() — прогноз стоимости для Budget Manager
    #  - supports_*()     — проверки возможностей конкретной модели
    #
    #Router работает только с потребностями (need: vision/code/...), поэтому вызывающий код обычно сначала проверяет supports_vision()/supports_embeddings(), а затем вызывает соответствующий метод.

    name: str = "base"

    def __init__(self, api_key: Optional[str] = None, **config: Any):
        self.api_key = api_key
        self.config = config

    #Основные вызовы

    @abstractmethod
    async def chat(
        self,
        messages: list[Message],
        model: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> ChatResult:
        #Текстовый диалог
        raise NotImplementedError

    @abstractmethod
    async def vision(
        self,
        messages: list[Message],
        images: list[ImageInput],
        model: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> ChatResult:
        
        #Диалог с изображениями. Если модель/провайдер не поддерживает vision — должен  UnsupportedCapabilityError, а не игнорировать images
        
        raise NotImplementedError

    @abstractmethod
    async def embeddings(
        self,
        texts: list[str],
        model: str,
        **kwargs: Any,
    ) -> EmbeddingsResult:
        
        #Векторизация текста для Memory. Если провайдер не поддерживает embeddings — UnsupportedCapabilityError
        
        raise NotImplementedError

    # Прогноз стоимости и capability-проверки

    @abstractmethod
    def estimate_cost(
        self,
        messages: list[Message],
        model: str,
        max_tokens: int = 1000,
    ) -> CostEstimate:
        #Прогноз стоимости ДО вызова модели чтобы решить, можно ли себе позволить эту модель
        raise NotImplementedError

    @abstractmethod
    def supports_vision(self, model: str) -> bool:
        #Умеет ли данная модель у этого провайдера принимать изображения
        raise NotImplementedError

    @abstractmethod
    def supports_embeddings(self, model: str) -> bool:
        #Умеет ли данная модель у этого провайдера отдавать embeddings
        raise NotImplementedError

    @abstractmethod
    def supports_model(self, model: str) -> bool:
        #Знает ли провайдер такую модель
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r}>"
