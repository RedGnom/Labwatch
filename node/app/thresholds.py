"""Оценка телеметрии по порогам из node.yaml.

Модуль ничего не делает с измерениями — только присваивает каждому
параметру уровень: OK, WARN или CRITICAL.

Два типа порогов:
  - warn / critical  — превышение (температура, ток, влажность);
  - min / max        — выход за диапазон в любую сторону
                       (напряжение, обороты вентилятора).
"""
from dataclasses import dataclass
from enum import Enum

from .sensors.base import SensorReading


class Level(str, Enum):
    OK = "ok"
    WARN = "warn"
    CRITICAL = "critical"
    UNKNOWN = "unknown"   # если для параметра нет порогов в конфиге


@dataclass
class ParamStatus:
    """Статус одного параметра."""
    name: str
    value: float
    level: Level
    threshold: float | None = None   # какой порог сработал


@dataclass
class EvaluationResult:
    """Результат оценки всего измерения."""
    statuses: dict[str, ParamStatus]

    @property
    def worst_level(self) -> Level:
        """Худший уровень среди всех параметров.

        Порядок: CRITICAL > WARN > OK > UNKNOWN.
        """
        order = {Level.CRITICAL: 3, Level.WARN: 2, Level.OK: 1, Level.UNKNOWN: 0}
        if not self.statuses:
            return Level.UNKNOWN
        return max(
            (s.level for s in self.statuses.values()),
            key=lambda lvl: order[lvl],
        )

    def changed_vs(self, previous: "EvaluationResult | None") -> list[ParamStatus]:
        """Параметры, у которых уровень изменился с прошлого раза."""
        if previous is None:
            return list(self.statuses.values())
        changed = []
        for name, cur in self.statuses.items():
            prev = previous.statuses.get(name)
            if prev is None or prev.level != cur.level:
                changed.append(cur)
        return changed


def _eval_warn_critical(name: str, value: float, cfg: dict) -> ParamStatus:
    """Пороги типа warn / critical — превышение."""
    warn = cfg.get("warn")
    critical = cfg.get("critical")

    if critical is not None and value >= critical:
        return ParamStatus(name, value, Level.CRITICAL, critical)
    if warn is not None and value >= warn:
        return ParamStatus(name, value, Level.WARN, warn)
    return ParamStatus(name, value, Level.OK)


def _eval_min_max(name: str, value: float, cfg: dict) -> ParamStatus:
    """Пороги типа min / max — выход за диапазон в любую сторону."""
    lo = cfg.get("min")
    hi = cfg.get("max")

    if lo is not None and value < lo:
        return ParamStatus(name, value, Level.WARN, lo)
    if hi is not None and value > hi:
        return ParamStatus(name, value, Level.WARN, hi)
    return ParamStatus(name, value, Level.OK)


def evaluate(reading: SensorReading, thresholds_cfg: dict) -> EvaluationResult:
    """Оценить одно измерение по порогам из node.yaml."""
    values = {
        "cpu_temp_c": reading.cpu_temp_c,
        "case_temp_c": reading.case_temp_c,
        "humidity_pct": reading.humidity_pct,
        "current_a": reading.current_a,
        "voltage_v": reading.voltage_v,
        "fan_rpm": float(reading.fan_rpm),
    }

    statuses: dict[str, ParamStatus] = {}

    for name, value in values.items():
        cfg = thresholds_cfg.get(name)
        if not cfg:
            statuses[name] = ParamStatus(name, value, Level.UNKNOWN)
            continue

        if "warn" in cfg or "critical" in cfg:
            statuses[name] = _eval_warn_critical(name, value, cfg)
        elif "min" in cfg or "max" in cfg:
            statuses[name] = _eval_min_max(name, value, cfg)
        else:
            statuses[name] = ParamStatus(name, value, Level.UNKNOWN)

    return EvaluationResult(statuses=statuses)