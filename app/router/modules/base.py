#Абстракция "модуля" — то, что роутер вызывает на этапе анализа, если
#анализатор решил, что это нужно (поиск, документы, и т.д. в будущем).
#Новый модуль подключается регистрацией, ничего в роутере менять не нужно —
#та же идея, что и с BaseProvider для моделей.

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ModuleResult:
    #Унифицированный результат работы любого модуля — текст для контекста плюс метаданные
    context_text: str
    cost_usd: float = 0.0
    meta: dict[str, Any] = field(default_factory=dict)


class BaseModule(ABC):
    name: str

    @abstractmethod
    async def run(self, query: str) -> ModuleResult:
        ...
