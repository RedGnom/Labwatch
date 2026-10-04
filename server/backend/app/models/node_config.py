"""Конфиг узла — пороги и режим работы.

Android-приложение читает и меняет эти значения через API.
Узел периодически забирает конфиг и применяет на своей стороне.

mode:
  auto   — узел сам реагирует на пороги (вентилятор, инциденты)
  manual — узел только собирает телеметрию, вентилятор управляется
           вручную командами fan_on / fan_off
"""
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NodeConfig(Base):
    __tablename__ = "node_configs"

    node_id: Mapped[str] = mapped_column(
        String(64), primary_key=True
    )
    mode: Mapped[str] = mapped_column(String(16), default="auto")
    thresholds: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    fan_on_at_cpu_temp_c: Mapped[float] = mapped_column(Float, default=75.0)
    fan_off_at_cpu_temp_c: Mapped[float] = mapped_column(Float, default=60.0)
    config_version: Mapped[int] = mapped_column(Integer, default=1)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )