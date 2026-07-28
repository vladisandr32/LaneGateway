#Событийный лог решений роутера — фундамент для будущего Decision Replay в GUI.
#
#Каждый шаг обработки запроса (анализ, вызов модуля, выбор модели, финальный
#ответ) пишется как отдельное событие с причиной и стоимостью. Ничего не
#перезаписывается — история накапливается, чтобы потом можно было открыть
#request_id и увидеть весь путь решения.
#
#Реализация через sqlite3 напрямую (не через SQLAlchemy-модели из db.py) —
#события не связаны с остальной доменной моделью, отдельная простая таблица
#достаточна для текущего этапа.

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class RouteEvent:
    request_id: str
    step: str  # например: RequestReceived, AnalyzerCalled, ModuleCalled, ModelSelected, ResponseGenerated
    detail: dict[str, Any] = field(default_factory=dict)
    cost_usd: float = 0.0
    ts: float = field(default_factory=time.time)


class EventLog:
    #Простое sqlite-хранилище событий. Один файл, одна таблица.

    def __init__(self, db_path: str = "./lanegateway_events.db") -> None:
        self._db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS route_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT NOT NULL,
                    step TEXT NOT NULL,
                    detail TEXT NOT NULL,
                    cost_usd REAL NOT NULL DEFAULT 0,
                    ts REAL NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_route_events_request_id ON route_events(request_id)"
            )

    def log(self, event: RouteEvent) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO route_events (request_id, step, detail, cost_usd, ts) VALUES (?, ?, ?, ?, ?)",
                (event.request_id, event.step, json.dumps(event.detail, ensure_ascii=False), event.cost_usd, event.ts),
            )

    def get_events(self, request_id: str) -> list[RouteEvent]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT request_id, step, detail, cost_usd, ts FROM route_events "
                "WHERE request_id = ? ORDER BY ts ASC",
                (request_id,),
            ).fetchall()

        return [
            RouteEvent(
                request_id=row[0],
                step=row[1],
                detail=json.loads(row[2]),
                cost_usd=row[3],
                ts=row[4],
            )
            for row in rows
        ]

    def total_cost(self, request_id: str) -> float:
        return sum(e.cost_usd for e in self.get_events(request_id))


def new_request_id() -> str:
    return str(uuid.uuid4())
