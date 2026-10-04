"""API конфига узла: режим auto/manual, пороги, настройки вентилятора.

Поток:
  Android  → GET /nodes/{id}/config   (прочитать текущие настройки)
  Android  → PUT /nodes/{id}/config   (изменить режим или пороги)
  Узел     → GET /nodes/{id}/config   (периодически забирает изменения)

Каждое обновление увеличивает config_version. Узел сравнивает свою
локальную версию с серверной и, если сервер новее, перечитывает конфиг.
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select

from app.config import settings
from app.db.session import SessionLocal
from app.models.node_config import NodeConfig
from app.models.telemetry import Node
from app.schemas.command import NodeConfigOut, NodeConfigUpdate

log = logging.getLogger("labwatch.api.config")

router = APIRouter(prefix="/nodes", tags=["config"])


def verify_node_token(x_node_token: str = Header(..., alias="X-Node-Token")) -> None:
    """Проверка токена узла."""
    if x_node_token != settings.node_token:
        log.warning("rejected config request: bad node token")
        raise HTTPException(status_code=401, detail="invalid node token")


def _ensure_node_exists(node_id: str) -> None:
    with SessionLocal() as db:
        if db.get(Node, node_id) is None:
            raise HTTPException(
                status_code=404,
                detail=f"node {node_id} not found. Wait for first telemetry.",
            )


def _get_or_create_config(db, node_id: str) -> NodeConfig:
    """Получить конфиг узла. Если нет — создать с дефолтами."""
    cfg = db.get(NodeConfig, node_id)
    if cfg is None:
        cfg = NodeConfig(
            node_id=node_id,
            mode="auto",
            thresholds=None,
            fan_on_at_cpu_temp_c=75.0,
            fan_off_at_cpu_temp_c=60.0,
            config_version=1,
        )
        db.add(cfg)
        db.flush()
    return cfg


# ─── Чтение конфига ──────────────────────────────────────
@router.get("/{node_id}/config", response_model=NodeConfigOut)
def get_config(node_id: str) -> NodeConfig:
    """Текущий конфиг узла (для Android и для узла)."""
    _ensure_node_exists(node_id)
    with SessionLocal() as db:
        cfg = _get_or_create_config(db, node_id)
        db.commit()
        db.refresh(cfg)
        return cfg


# ─── Изменение конфига ───────────────────────────────────
@router.put("/{node_id}/config", response_model=NodeConfigOut)
def update_config(node_id: str, body: NodeConfigUpdate) -> NodeConfig:
    """Изменить конфиг узла (Android). Увеличивает config_version."""
    _ensure_node_exists(node_id)

    with SessionLocal() as db:
        cfg = _get_or_create_config(db, node_id)

        if body.mode is not None:
            cfg.mode = body.mode
        if body.thresholds is not None:
            cfg.thresholds = body.thresholds
        if body.fan_on_at_cpu_temp_c is not None:
            cfg.fan_on_at_cpu_temp_c = body.fan_on_at_cpu_temp_c
        if body.fan_off_at_cpu_temp_c is not None:
            cfg.fan_off_at_cpu_temp_c = body.fan_off_at_cpu_temp_c

        # Валидация: fan_off < fan_on
        if cfg.fan_off_at_cpu_temp_c >= cfg.fan_on_at_cpu_temp_c:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"fan_off_at_cpu_temp_c ({cfg.fan_off_at_cpu_temp_c}) "
                    f"must be < fan_on_at_cpu_temp_c ({cfg.fan_on_at_cpu_temp_c})"
                ),
            )

        cfg.config_version += 1
        cfg.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(cfg)

        log.info(
            "config updated: node=%s version=%d mode=%s "
            "fan_on=%.1f fan_off=%.1f thresholds=%s",
            node_id, cfg.config_version, cfg.mode,
            cfg.fan_on_at_cpu_temp_c, cfg.fan_off_at_cpu_temp_c,
            "yes" if cfg.thresholds else "no",
        )
        return cfg