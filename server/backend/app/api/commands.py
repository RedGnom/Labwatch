"""API для работы с командами узлов.

Поток:
  Android  → POST /nodes/{id}/commands           (создать команду)
  Узел     → GET  /nodes/{id}/commands/pending   (забрать список)
  Узел     → POST /nodes/{id}/commands/{cmd}/ack (подтвердить)
  Android  → GET  /nodes/{id}/commands           (история)
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import desc, select

from app.config import settings
from app.db.session import SessionLocal
from app.models.command import Command
from app.models.telemetry import Node
from app.schemas.command import CommandAck, CommandCreate, CommandOut

log = logging.getLogger("labwatch.api.commands")

router = APIRouter(prefix="/nodes", tags=["commands"])


# ─── Зависимости ─────────────────────────────────────────
def verify_node_token(x_node_token: str = Header(..., alias="X-Node-Token")) -> None:
    """Проверка токена узла."""
    if x_node_token != settings.node_token:
        log.warning("rejected command request: bad node token")
        raise HTTPException(status_code=401, detail="invalid node token")


def _ensure_node_exists(node_id: str) -> None:
    """Узел должен быть в таблице nodes. Если нет — 404."""
    with SessionLocal() as db:
        node = db.get(Node, node_id)
        if node is None:
            raise HTTPException(
                status_code=404,
                detail=f"node {node_id} not found. Wait for first telemetry.",
            )


# ─── Создание команды (Android) ──────────────────────────
@router.post("/{node_id}/commands", status_code=201, response_model=CommandOut)
def create_command(node_id: str, body: CommandCreate) -> Command:
    """Создать команду. Пока без авторизации Android — добавим JWT позже."""
    _ensure_node_exists(node_id)

    with SessionLocal() as db:
        cmd = Command(
            node_id=node_id,
            type=body.type,
            payload=body.payload,
            status="pending",
        )
        db.add(cmd)
        db.commit()
        db.refresh(cmd)
        log.info("command queued: id=%d node=%s type=%s", cmd.id, node_id, cmd.type)
        return cmd


# ─── История команд (Android) ────────────────────────────
@router.get("/{node_id}/commands", response_model=list[CommandOut])
def list_commands(node_id: str, limit: int = 50) -> list[Command]:
    """Последние N команд узла (от новых к старым)."""
    with SessionLocal() as db:
        stmt = (
            select(Command)
            .where(Command.node_id == node_id)
            .order_by(desc(Command.created_at))
            .limit(limit)
        )
        return list(db.execute(stmt).scalars().all())


# ─── Забор команд узлом ──────────────────────────────────
@router.get(
    "/{node_id}/commands/pending",
    response_model=list[CommandOut],
    dependencies=[Depends(verify_node_token)],
)
def get_pending(node_id: str, limit: int = 10) -> list[Command]:
    """Узел забирает pending-команды. Помечает их как in_progress."""
    now = datetime.now(timezone.utc)

    with SessionLocal() as db:
        stmt = (
            select(Command)
            .where(Command.node_id == node_id)
            .where(Command.status == "pending")
            .order_by(Command.created_at)
            .limit(limit)
        )
        cmds = list(db.execute(stmt).scalars().all())

        for c in cmds:
            c.status = "in_progress"
            c.claimed_at = now
        db.commit()

        for c in cmds:
            db.refresh(c)

        if cmds:
            log.info(
                "node %s claimed %d commands: %s",
                node_id, len(cmds), [c.id for c in cmds],
            )
        return cmds


# ─── Подтверждение выполнения (узел) ─────────────────────
@router.post(
    "/{node_id}/commands/{cmd_id}/ack",
    response_model=CommandOut,
    dependencies=[Depends(verify_node_token)],
)
def ack_command(node_id: str, cmd_id: int, body: CommandAck) -> Command:
    """Узел сообщает результат: done или failed."""
    with SessionLocal() as db:
        cmd = db.get(Command, cmd_id)
        if cmd is None or cmd.node_id != node_id:
            raise HTTPException(status_code=404, detail="command not found")

        cmd.status = body.status
        cmd.result = body.result
        cmd.done_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(cmd)

        log.info(
            "command ack: id=%d node=%s status=%s result=%s",
            cmd.id, node_id, cmd.status, cmd.result,
        )
        return cmd