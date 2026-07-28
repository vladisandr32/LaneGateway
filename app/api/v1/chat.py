#Chat-эндпоинт. Теперь идёт через Router (анализатор -> модули -> исполнитель),
#а не напрямую к провайдеру — это и есть переход от "просто вызовы функций" к
#реальной маршрутизации с объяснимостью каждого решения.

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_router
from app.core.security import verify_api_key
from app.providers.base import Message
from app.router.router import Router
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(dependencies=[Depends(verify_api_key)])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    lane_router: Router = Depends(get_router),
) -> ChatResponse:
    messages = [Message(role=m.role, content=m.content) for m in body.messages]

    try:
        result = await lane_router.route(messages)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    return ChatResponse(
        request_id=result.request_id,
        text=result.text,
        model=result.model_used,
        #Точные токены не считаем на этом уровне — они видны в истории решений
        #по request_id через /api/v1/decisions/{request_id}
        prompt_tokens=0,
        completion_tokens=0,
        cost_usd=result.total_cost_usd,
    )
