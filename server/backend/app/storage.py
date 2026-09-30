"""Хранилище телеметрии поверх PostgreSQL.

Интерфейс (save / latest / history / nodes) не изменился с InMemory-версии,
поэтому роутеры в main.py трогать не пришлось.
"""
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.telemetry import Node, Telemetry


class PostgresStorage:
    def __init__(self, session_factory=SessionLocal) -> None:
        self._session_factory = session_factory

    def _ensure_node(self, db: Session, node_id: str) -> Node:
        node = db.get(Node, node_id)
        if node is None:
            node = Node(id=node_id)
            db.add(node)
            db.flush()
        return node

    def save(self, node_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        with self._session_factory() as db:
            self._ensure_node(db, node_id)

            row = Telemetry(
                node_id=node_id,
                cpu_temp_c=payload["cpu_temp_c"],
                case_temp_c=payload["case_temp_c"],
                humidity_pct=payload["humidity_pct"],
                current_a=payload["current_a"],
                voltage_v=payload["voltage_v"],
                fan_rpm=payload["fan_rpm"],
            )
            db.add(row)
            db.commit()
            db.refresh(row)

            return {
                "node_id": row.node_id,
                "cpu_temp_c": row.cpu_temp_c,
                "case_temp_c": row.case_temp_c,
                "humidity_pct": row.humidity_pct,
                "current_a": row.current_a,
                "voltage_v": row.voltage_v,
                "fan_rpm": row.fan_rpm,
                "received_at": row.received_at.isoformat() if row.received_at else None,
            }

    def latest(self, node_id: str) -> dict[str, Any] | None:
        with self._session_factory() as db:
            stmt = (
                select(Telemetry)
                .where(Telemetry.node_id == node_id)
                .order_by(desc(Telemetry.received_at))
                .limit(1)
            )
            row = db.execute(stmt).scalar_one_or_none()
            if row is None:
                return None
            return {
                "node_id": row.node_id,
                "cpu_temp_c": row.cpu_temp_c,
                "case_temp_c": row.case_temp_c,
                "humidity_pct": row.humidity_pct,
                "current_a": row.current_a,
                "voltage_v": row.voltage_v,
                "fan_rpm": row.fan_rpm,
                "received_at": row.received_at.isoformat() if row.received_at else None,
            }

    def history(self, node_id: str, limit: int = 100) -> list[dict[str, Any]]:
        with self._session_factory() as db:
            stmt = (
                select(Telemetry)
                .where(Telemetry.node_id == node_id)
                .order_by(desc(Telemetry.received_at))
                .limit(limit)
            )
            rows = db.execute(stmt).scalars().all()
            # Возвращаем в хронологическом порядке (от старых к новым)
            return [
                {
                    "node_id": r.node_id,
                    "cpu_temp_c": r.cpu_temp_c,
                    "case_temp_c": r.case_temp_c,
                    "humidity_pct": r.humidity_pct,
                    "current_a": r.current_a,
                    "voltage_v": r.voltage_v,
                    "fan_rpm": r.fan_rpm,
                    "received_at": r.received_at.isoformat() if r.received_at else None,
                }
                for r in reversed(rows)
            ]

    def nodes(self) -> list[str]:
        with self._session_factory() as db:
            stmt = select(Node.id).order_by(Node.id)
            return list(db.execute(stmt).scalars().all())


storage = PostgresStorage()