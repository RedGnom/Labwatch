"""Pydantic-схемы для команд и конфига узла.

Валидация типов команд и полей конфига на входе API.
"""
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


# Разрешённые типы команд
CommandType = Literal[
    "fan_on",         # включить вентилятор
    "fan_off",        # выключить вентилятор
    "restart",        # перезагрузить узел (корректный выход, супервизор перезапустит)
    "set_mode",       # сменить режим: auto / manual
    "set_thresholds", # обновить пороги на узле
]


class CommandCreate(BaseModel):
    """Тело POST /nodes/{id}/commands."""
    type: CommandType
    payload: dict[str, Any] | None = Field(
        default=None,
        description="Дополнительные параметры команды",
        examples=[{"mode": "manual"}],
    )


class CommandOut(BaseModel):
    """Ответ с информацией о команде."""
    id: int
    node_id: str
    type: str
    payload: dict[str, Any] | None = None
    status: str
    result: str | None = None
    created_at: datetime
    claimed_at: datetime | None = None
    done_at: datetime | None = None

    model_config = {"from_attributes": True}


class CommandAck(BaseModel):
    """Тело POST /nodes/{id}/commands/{cmd_id}/ack."""
    status: Literal["done", "failed"]
    result: str | None = Field(
        default=None,
        description="Текст результата или ошибки",
        examples=["fan turned on"],
    )

    # ─── Конфиг узла ────────────────────────────────────────
class ThresholdRange(BaseModel):
    """Пороги warn/critical для числового параметра."""
    warn: float | None = None
    critical: float | None = None


class ThresholdBand(BaseModel):
    """Пороги min/max для параметра типа «диапазон»."""
    min: float | None = None
    max: float | None = None


class NodeConfigOut(BaseModel):
    """Ответ GET /nodes/{id}/config."""
    node_id: str
    mode: Literal["auto", "manual"] = "auto"
    thresholds: dict[str, dict[str, float]] | None = None
    fan_on_at_cpu_temp_c: float = 75.0
    fan_off_at_cpu_temp_c: float = 60.0
    config_version: int = 1
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class NodeConfigUpdate(BaseModel):
    """Тело PUT /nodes/{id}/config.

    Все поля опциональны — можно обновить только часть.
    """
    mode: Literal["auto", "manual"] | None = None
    thresholds: dict[str, dict[str, float]] | None = None
    fan_on_at_cpu_temp_c: float | None = None
    fan_off_at_cpu_temp_c: float | None = None