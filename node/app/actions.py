"""Действия узла в ответ на данные.

Сейчас — управление вентилятором с гистерезисом:
  CPU >= fan_on_at_cpu_temp_c   и вентилятор выключен  -> включить
  CPU <= fan_off_at_cpu_temp_c  и вентилятор включён   -> выключить
  между порогами — состояние не меняется.

Гистерезис нужен, чтобы вентилятор не дёргался каждые 5 секунд
при температуре, колеблющейся вокруг одного порога.
"""
import logging
from dataclasses import dataclass

from .sensors.base import SensorReading, SensorSource

log = logging.getLogger(__name__)


@dataclass
class FanDecision:
    """Результат проверки: меняем ли состояние вентилятора."""
    changed: bool
    fan_on: bool          # состояние после проверки
    reason: str           # человекочитаемая причина


class Actions:
    def __init__(
        self,
        sensor: SensorSource,
        fan_on_at: float,
        fan_off_at: float,
    ) -> None:
        if fan_off_at >= fan_on_at:
            raise ValueError(
                f"fan_off_at ({fan_off_at}) must be < fan_on_at ({fan_on_at}). "
                "Иначе гистерезис не имеет смысла."
            )
        self._sensor = sensor
        self._fan_on_at = fan_on_at
        self._fan_off_at = fan_off_at
        # Начальное состояние — считаем, что вентилятор выключен.
        # Симулятор так и стартует.
        self._fan_state: bool = False

    @property
    def fan_state(self) -> bool:
        return self._fan_state

    def apply(self, reading: SensorReading) -> FanDecision:
        """Проверить температуру и, если нужно, переключить вентилятор."""
        cpu = reading.cpu_temp_c

        # Случай 1: температура высокая, вентилятор выключен → включаем.
        if cpu >= self._fan_on_at and not self._fan_state:
            self._sensor.set_fan(True)
            self._fan_state = True
            reason = f"cpu {cpu:.2f}°C >= {self._fan_on_at}°C → fan ON"
            log.warning("action: %s", reason)
            return FanDecision(changed=True, fan_on=True, reason=reason)

        # Случай 2: температура низкая, вентилятор включён → выключаем.
        if cpu <= self._fan_off_at and self._fan_state:
            self._sensor.set_fan(False)
            self._fan_state = False
            reason = f"cpu {cpu:.2f}°C <= {self._fan_off_at}°C → fan OFF"
            log.warning("action: %s", reason)
            return FanDecision(changed=True, fan_on=False, reason=reason)

        # Случай 3: между порогами или состояние совпадает — ничего не делаем.
        return FanDecision(changed=False, fan_on=self._fan_state, reason="")