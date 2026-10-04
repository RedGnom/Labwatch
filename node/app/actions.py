"""Действия узла в ответ на данные.

Управление вентилятором с гистерезисом и поддержкой режимов:
  auto   — вентилятор включается/выключается по температуре CPU
           с гистерезисом;
  manual — автоматика выключена, вентилятор управляется только
           командами fan_on / fan_off с сервера.

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
    fan_on: bool
    reason: str


class Actions:
    def __init__(
        self,
        sensor: SensorSource,
        fan_on_at: float,
        fan_off_at: float,
        mode: str = "auto",
    ) -> None:
        if fan_off_at >= fan_on_at:
            raise ValueError(
                f"fan_off_at ({fan_off_at}) must be < fan_on_at ({fan_on_at}). "
                "Иначе гистерезис не имеет смысла."
            )
        if mode not in ("auto", "manual"):
            raise ValueError(f"mode must be 'auto' or 'manual', got {mode!r}")

        self._sensor = sensor
        self._fan_on_at = fan_on_at
        self._fan_off_at = fan_off_at
        self._mode = mode
        # Начальное состояние — выключен. Симулятор так и стартует.
        self._fan_state: bool = False

    # ─── Состояние ──────────────────────────────────────
    @property
    def fan_state(self) -> bool:
        return self._fan_state

    @property
    def mode(self) -> str:
        return self._mode

    # ─── Настройки ──────────────────────────────────────
    def set_mode(self, mode: str) -> None:
        if mode not in ("auto", "manual"):
            raise ValueError(f"mode must be 'auto' or 'manual', got {mode!r}")
        if mode != self._mode:
            log.warning("actions: mode %s → %s", self._mode, mode)
        self._mode = mode

    def set_thresholds(self, fan_on_at: float, fan_off_at: float) -> None:
        if fan_off_at >= fan_on_at:
            raise ValueError(
                f"fan_off_at ({fan_off_at}) must be < fan_on_at ({fan_on_at})"
            )
        self._fan_on_at = fan_on_at
        self._fan_off_at = fan_off_at

    # ─── Принудительное управление (для команд) ─────────
    def force_fan(self, on: bool) -> FanDecision:
        """Принудительно включить/выключить вентилятор.

        Работает в любом режиме. Если состояние не меняется — возвращает
        changed=False, но всё равно фиксирует.
        """
        if on == self._fan_state:
            return FanDecision(changed=False, fan_on=self._fan_state,
                               reason="already in desired state")
        self._sensor.set_fan(on)
        self._fan_state = on
        reason = f"forced fan {'ON' if on else 'OFF'}"
        log.warning("action: %s", reason)
        return FanDecision(changed=True, fan_on=on, reason=reason)

    # ─── Автоматика (вызывается в цикле) ────────────────
    def apply(self, reading: SensorReading) -> FanDecision:
        """Проверить и, если нужно, переключить вентилятор.

        В режиме manual — ничего не делает, автоматика выключена.
        """
        if self._mode == "manual":
            return FanDecision(changed=False, fan_on=self._fan_state, reason="")

        cpu = reading.cpu_temp_c

        # Случай 1: высокая температура, вентилятор выключен → включаем.
        if cpu >= self._fan_on_at and not self._fan_state:
            self._sensor.set_fan(True)
            self._fan_state = True
            reason = f"cpu {cpu:.2f}°C >= {self._fan_on_at}°C → fan ON"
            log.warning("action: %s", reason)
            return FanDecision(changed=True, fan_on=True, reason=reason)

        # Случай 2: низкая температура, вентилятор включён → выключаем.
        if cpu <= self._fan_off_at and self._fan_state:
            self._sensor.set_fan(False)
            self._fan_state = False
            reason = f"cpu {cpu:.2f}°C <= {self._fan_off_at}°C → fan OFF"
            log.warning("action: %s", reason)
            return FanDecision(changed=True, fan_on=False, reason=reason)

        # Случай 3: между порогами или состояние совпадает — ничего.
        return FanDecision(changed=False, fan_on=self._fan_state, reason="")