from .base import SensorReading, SensorSource
from .simulated import SimulatedSensorSource
from .real import RealSensorSource


def create_sensor_source(config: dict) -> SensorSource:
    """Выбор источника данных по конфигу."""
    kind = config.get("sensor_source", "simulated")

    if kind == "simulated":
        sim_cfg = config.get("simulation", {})
        return SimulatedSensorSource(
            seed=sim_cfg.get("seed", 42),
            scenario=sim_cfg.get("scenario", "normal"),
        )

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