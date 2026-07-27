#Pydantic-схемы HTTP API — отдельно от dataclass-ов провайдера (app/providers/base.py),
#чтобы формат HTTP-запроса/ответа не был жёстко завязан на внутренний интерфейс провайдера

from pydantic import BaseModel


class ChatMessageIn(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessageIn]
    model: str
    max_tokens: int = 1000
    temperature: float = 0.7


class ChatResponse(BaseModel):
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
