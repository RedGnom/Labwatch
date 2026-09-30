from .base import SensorReading, SensorSource


class RealSensorSource(SensorSource):
    """Реальные датчики на Raspberry Pi (DS18B20, INA219 и т.д.).

    Здесь будет код работы с GPIO / I2C / 1-Wire.
    Сейчас заглушка — включается сменой sensor_source в конфиге.
    """

    def __init__(self, **kwargs):
        raise NotImplementedError(
            "Real sensors not wired up yet. "
            "Set sensor_source: simulated in node.yaml."
        )

    def read(self) -> SensorReading:
        raise NotImplementedError

    def set_fan(self, on: bool) -> None:
        raise NotImplementedError