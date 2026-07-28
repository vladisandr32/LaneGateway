#Pydantic-схема для эндпоинта истории решений — бэкенд для будущего GUI Decision Replay

from pydantic import BaseModel


class RouteEventOut(BaseModel):
    step: str
    detail: dict
    cost_usd: float
    ts: float


class DecisionHistoryResponse(BaseModel):
    request_id: str
    total_cost_usd: float
    events: list[RouteEventOut]
