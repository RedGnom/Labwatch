"""Эмулятор датчиков.

Генерирует правдоподобные значения с медленным дрейфом, плюс
поддерживает сценарии аномалий для тестирования порогов и действий:

  normal        — обычный дрейф вокруг 45°C;
  overheat      — CPU быстро разогревается, проходит warn и critical,
                  включает вентилятор;
  current_surge — ток подскакивает выше critical на определённом такте.
"""
import random

from .base import SensorReading, SensorSource


class SimulatedSensorSource(SensorSource):
    def __init__(self, seed: int = 42, scenario: str = "normal"):
        self._rng = random.Random(seed)
        self._scenario = scenario
        self._tick = 0

        # стартовые значения
        self._cpu_temp = 45.0
        self._case_temp = 30.0
        self._humidity = 40.0
        self._current = 1.5
        self._voltage = 12.1
        self._fan_rpm = 0
        self._fan_on = False

    # ─── Основной метод ─────────────────────────────────
    def read(self) -> SensorReading:
        self._tick += 1
        self._step_cpu()
        self._step_case()
        self._step_humidity()
        self._step_current()
        self._step_voltage()
        self._clamp_all()
        self._step_fan()

        return SensorReading(
            cpu_temp_c=round(self._cpu_temp, 2),
            case_temp_c=round(self._case_temp, 2),
            humidity_pct=round(self._humidity, 2),
            current_a=round(self._current, 2),
            voltage_v=round(self._voltage, 2),
            fan_rpm=self._fan_rpm,
        )

    # ─── Дрейф параметров ───────────────────────────────
    def _step_cpu(self) -> None:
        if self._scenario == "overheat":
            # быстрый рост, но не выше 92°C
            self._cpu_temp += self._rng.uniform(1.5, 2.5)
        else:
            self._cpu_temp += self._rng.uniform(-0.8, 1.2)

    def _step_case(self) -> None:
        # корпус следует за CPU с задержкой и меньшей амплитудой
        target = self._cpu_temp * 0.6
        self._case_temp += (target - self._case_temp) * 0.1
        self._case_temp += self._rng.uniform(-0.3, 0.3)

    def _step_humidity(self) -> None:
        self._humidity += self._rng.uniform(-1.0, 1.0)

    def _step_current(self) -> None:
        if self._scenario == "current_surge" and self._tick == 6:
            # резкий скачок на 6-м такте
            self._current += 4.0
        self._current += self._rng.uniform(-0.2, 0.3)

    def _step_voltage(self) -> None:
        self._voltage += self._rng.uniform(-0.05, 0.05)

    def _clamp_all(self) -> None:
        self._cpu_temp = max(30.0, min(92.0, self._cpu_temp))
        self._case_temp = max(20.0, min(70.0, self._case_temp))
        self._humidity = max(20.0, min(95.0, self._humidity))
        self._current = max(0.1, min(6.0, self._current))
        self._voltage = max(11.0, min(13.0, self._voltage))

    def _step_fan(self) -> None:
        if self._fan_on:
            base = 800 + (self._cpu_temp - 40) * 40
            self._fan_rpm = int(max(500, min(3000, base + self._rng.uniform(-50, 50))))
        else:
            self._fan_rpm = 0

    # ─── Управление вентилятором ────────────────────────
    def set_fan(self, on: bool) -> None:
        self._fan_on = on
        if not on:
            self._fan_rpm = 0