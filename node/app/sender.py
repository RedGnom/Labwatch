"""Отправка телеметрии на сервер.

Если сервер недоступен — запись кладётся в локальный буфер (JSONL)
и досылается при восстановлении связи. Это закрывает сценарий
«потеря связи» из ТЗ.
"""
import json
import logging
from pathlib import Path

import httpx

from .sensors.base import SensorReading

log = logging.getLogger(__name__)


class Sender:
    def __init__(self, url: str, buffer_path: Path, timeout: float = 5.0) -> None:
        self._url = url.rstrip("/")
        self._buffer = Path(buffer_path)
        self._buffer.touch(exist_ok=True)
        self._timeout = timeout
        self._client = httpx.Client(timeout=timeout)

    def send(self, node_id: str, reading: SensorReading) -> bool:
        """Отправить одно измерение. True — доставлено, False — в буфер."""
        payload = {
            "node_id": node_id,
            "cpu_temp_c": reading.cpu_temp_c,
            "case_temp_c": reading.case_temp_c,
            "humidity_pct": reading.humidity_pct,
            "current_a": reading.current_a,
            "voltage_v": reading.voltage_v,
            "fan_rpm": reading.fan_rpm,
        }

        # Сначала попытаться дослать старый буфер
        self._flush()

        try:
            r = self._client.post(f"{self._url}/telemetry", json=payload)
            r.raise_for_status()
            return True
        except Exception as e:
            log.warning("send failed, buffering: %s", e)
            with self._buffer.open("a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")
            return False

    def _flush(self) -> None:
        if not self._buffer.stat().st_size:
            return

        lines = self._buffer.read_text(encoding="utf-8").splitlines()
        self._buffer.write_text("", encoding="utf-8")

        for line in lines:
            try:
                r = self._client.post(
                    f"{self._url}/telemetry",
                    content=line.encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                )
                r.raise_for_status()
                log.info("flushed buffered record")
            except Exception as e:
                log.warning("flush failed, keeping rest in buffer: %s", e)
                with self._buffer.open("a", encoding="utf-8") as f:
                    f.write(line + "\n")
                break