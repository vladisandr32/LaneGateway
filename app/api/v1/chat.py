#Chat-эндпоинт. На текущем этапе (1-2) просто вызывает провайдера напрямую по имени —
#без Router'а (Этап 3) и без Pipeline (Этап 5). Это тот самый "на данном этапе просто вызовы функций"

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_registry
from app.core.security import verify_api_key
from app.providers.base import Message
from app.providers.registry import ProviderRegistry
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(dependencies=[Depends(verify_api_key)])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    registry: ProviderRegistry = Depends(get_registry),
) -> ChatResponse:
    #Пока хардкодим единственного провайдера — openrouter.
    #Когда появится Router, выбор провайдера уедет туда
    provider = registry.get("openrouter")
    if provider is None:
        raise HTTPException(status_code=503, detail="Провайдер openrouter не настроен")

    messages = [Message(role=m.role, content=m.content) for m in body.messages]
    result = await provider.chat(
        messages=messages,
        model=body.model,
        max_tokens=body.max_tokens,
        temperature=body.temperature,
    )

    return ChatResponse(
        text=result.text,
        model=result.model,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        cost_usd=result.cost_usd,
    )
