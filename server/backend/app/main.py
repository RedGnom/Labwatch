"""LabWatch backend — приём телеметрии и API."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.config import settings
from app.db.base import Base
from app.db.session import engine
from app.storage import storage

# Импорт моделей нужен, чтобы SQLAlchemy увидел их
# до вызова Base.metadata.create_all()
from app import models  # noqa: F401


logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("labwatch.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """При старте создаём таблицы, если их нет."""
    log.info("creating DB tables if missing...")
    Base.metadata.create_all(bind=engine)
    log.info("DB ready")
    yield


app = FastAPI(
    title="LabWatch API",
    version="0.1.0",
    description="Мониторинг и управление серверной/домашней лабораторией",
    lifespan=lifespan,
)


# ─── Схемы ──────────────────────────────────────────────
class TelemetryIn(BaseModel):
    node_id: str = Field(..., examples=["node-01"])
    cpu_temp_c: float
    case_temp_c: float
    humidity_pct: float
    current_a: float
    voltage_v: float
    fan_rpm: int


# ─── Эндпоинты ──────────────────────────────────────────
@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/telemetry", status_code=201)
def post_telemetry(t: TelemetryIn) -> dict:
    record = storage.save(t.node_id, t.model_dump(exclude={"node_id"}))
    log.info(
        "telemetry from %s: cpu=%.2f case=%.2f hum=%.2f I=%.2f U=%.2f fan=%d",
        t.node_id, t.cpu_temp_c, t.case_temp_c, t.humidity_pct,
        t.current_a, t.voltage_v, t.fan_rpm,
    )
    return {"status": "stored", "record": record}


@app.get("/nodes")
def list_nodes() -> dict:
    return {"nodes": storage.nodes()}


@app.get("/nodes/{node_id}/latest")
def node_latest(node_id: str) -> dict:
    rec = storage.latest(node_id)
    if rec is None:
        raise HTTPException(status_code=404, detail=f"node {node_id} not found")
    return rec


@app.get("/nodes/{node_id}/history")
def node_history(node_id: str, limit: int = 100) -> dict:
    if node_id not in storage.nodes():
        raise HTTPException(status_code=404, detail=f"node {node_id} not found")
    return {"node_id": node_id, "items": storage.history(node_id, limit)}