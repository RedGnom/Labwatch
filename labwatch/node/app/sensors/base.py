from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class SensorReading:
    """Одно измерение телеметрии."""
    cpu_temp_c: float
    case_temp_c: float
    humidity_pct: float
    current_a: float
    voltage_v: float
    fan_rpm: int


class SensorSource(ABC):
    """Абстрактный источник телеметрии.

    Наследники: SimulatedSensorSource, RealSensorSource.
    Узел работает только через этот интерфейс и не знает,
    откуда реально приходят данные.
    """

    @abstractmethod
    def read(self) -> SensorReading:
        """Вернуть одно измерение."""
        raise NotImplementedError

    @abstractmethod
    def set_fan(self, on: bool) -> None:
        """Включить/выключить вентилятор (или эмулировать это)."""
        raise NotImplementedError
        