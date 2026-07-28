#Эндпоинт истории решений: отдаёт полный путь обработки запроса по request_id.
#Это тот самый бэкенд, который потом будет читать GUI для Decision Replay —
#"почему выбрана эта модель, какие модули вызывались, сколько это стоило".

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_event_log
from app.core.security import verify_api_key
from app.router.events import EventLog
from app.schemas.decisions import DecisionHistoryResponse, RouteEventOut

router = APIRouter(dependencies=[Depends(verify_api_key)])


@router.get("/decisions/{request_id}", response_model=DecisionHistoryResponse)
async def get_decision_history(
    request_id: str,
    event_log: EventLog = Depends(get_event_log),
) -> DecisionHistoryResponse:
    events = event_log.get_events(request_id)
    if not events:
        raise HTTPException(status_code=404, detail="Запрос с таким request_id не найден")

    return DecisionHistoryResponse(
        request_id=request_id,
        total_cost_usd=sum(e.cost_usd for e in events),
        events=[
            RouteEventOut(step=e.step, detail=e.detail, cost_usd=e.cost_usd, ts=e.ts)
            for e in events
        ],
    )
