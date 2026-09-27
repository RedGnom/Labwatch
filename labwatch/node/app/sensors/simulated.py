import random
import time

from .base import SensorReading, SensorSource


class SimulatedSensorSource(SensorSource):
    """Эмулятор датчиков.

    Генерирует правдоподобные значения, которые медленно дрейфуют
    (а не прыгают случайно) — так удобнее тестировать пороги
    и видеть «перегрев» на графике.
    """

    def __init__(self, seed: int = 42):
        self._rng = random.Random(seed)

        # стартовые значения
        self._cpu_temp = 45.0
        self._case_temp = 30.0
        self._humidity = 40.0
        self._current = 1.5
        self._voltage = 12.1
        self._fan_rpm = 0
        self._fan_on = False

    def read(self) -> SensorReading:
        # медленный дрейф + небольшой шум
        self._cpu_temp += self._rng.uniform(-0.8, 1.2)
        self._case_temp += self._rng.uniform(-0.5, 0.7)
        self._humidity += self._rng.uniform(-1.0, 1.0)
        self._current += self._rng.uniform(-0.2, 0.3)
        self._voltage += self._rng.uniform(-0.05, 0.05)

        # ограничиваем в правдоподобных диапазонах
        self._cpu_temp = max(30.0, min(95.0, self._cpu_temp))
        self._case_temp = max(20.0, min(70.0, self._case_temp))
        self._humidity = max(20.0, min(95.0, self._humidity))
        self._current = max(0.1, min(6.0, self._current))
        self._voltage = max(11.0, min(13.0, self._voltage))

        # если вентилятор включён — обороты зависят от температуры
        if self._fan_on:
            base = 800 + (self._cpu_temp - 40) * 40
            self._fan_rpm = int(max(500, min(3000, base + self._rng.uniform(-50, 50))))
        else:
            self._fan_rpm = 0

        return SensorReading(
            cpu_temp_c=round(self._cpu_temp, 2),
            case_temp_c=round(self._case_temp, 2),
            humidity_pct=round(self._humidity, 2),
            current_a=round(self._current, 2),
            voltage_v=round(self._voltage, 2),
            fan_rpm=self._fan_rpm,
        )

    def set_fan(self, on: bool) -> None:
        self._fan_on = on
        if not on:
            self._fan_rpm = 0