"""Журнал инцидентов — изменения уровней параметров.

Пишем только переходы OK→WARN→CRITICAL и обратно, а не каждую
итерацию. Иначе файл растёт бесконтрольно и теряет смысл.

Формат — JSONL (одна JSON-строка на инцидент). Удобно грепать,
парсить, отправлять на сервер и в мобильное приложение.
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from .thresholds import EvaluationResult, ParamStatus

log = logging.getLogger(__name__)


class IncidentLog:
    def __init__(self, path: Path, node_id: str) -> None:
        self._path = Path(path)
        self._path.touch(exist_ok=True)
        self._node_id = node_id
        self._lock = Lock()

    @property
    def path(self) -> Path:
        return self._path

    def record_changes(
        self,
        current: EvaluationResult,
        previous: EvaluationResult | None,
    ) -> list[ParamStatus]:
        """Записать изменения уровней. Вернуть список записанных."""
        changed = current.changed_vs(previous)
        if not changed:
            return []

        with self._lock:
            with self._path.open("a", encoding="utf-8") as f:
                for s in changed:
                    prev_level = (
                        previous.statuses[s.name].level.value
                        if previous and s.name in previous.statuses
                        else "unknown"
                    )
                    record = {
                        "ts": datetime.now(timezone.utc).isoformat(),
                        "node_id": self._node_id,
                        "param": s.name,
                        "from": prev_level,
                        "to": s.level.value,
                        "value": round(float(s.value), 3),
                        "threshold": s.threshold,
                    }
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
                    log.info(
                        "incident: %s %s→%s value=%.2f threshold=%s",
                        s.name, prev_level, s.level.value,
                        float(s.value), s.threshold,
                    )
        return changed

    def count(self) -> int:
        """Сколько всего записей в журнале."""
        if not self._path.exists():
            return 0
        with self._path.open("r", encoding="utf-8") as f:
            return sum(1 for _ in f)

    def last(self, n: int = 10) -> list[dict]:
        """Последние N инцидентов (для отладки, потом для UI)."""
        if not self._path.exists():
            return []
        with self._path.open("r", encoding="utf-8") as f:
            lines = f.readlines()
        return [json.loads(line) for line in lines[-n:]]