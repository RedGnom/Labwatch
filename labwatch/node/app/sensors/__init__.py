from .base import SensorReading, SensorSource
from .simulated import SimulatedSensorSource
from .real import RealSensorSource


def create_sensor_source(config: dict) -> SensorSource:
    """Выбор источника данных по конфигу.

    Именно здесь реализована «замена одной строкой»:
    sensor_source: simulated  ->  sensor_source: real
    """
    kind = config.get("sensor_source", "simulated")

    if kind == "simulated":
        sim_cfg = config.get("simulation", {})
        return SimulatedSensorSource(seed=sim_cfg.get("seed", 42))

    if kind == "real":
        return RealSensorSource()

    raise ValueError(f"Unknown sensor_source: {kind!r}")


__all__ = [
    "SensorReading",
    "SensorSource",
    "SimulatedSensorSource",
    "RealSensorSource",
    "create_sensor_source",
]