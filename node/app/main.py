"""Точка входа агента узла."""
import logging
import time
from pathlib import Path

from .config import load_config
from .sender import Sender
from .sensors import create_sensor_source

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("labwatch.node")


def main() -> None:
    base_dir = Path(__file__).resolve().parent.parent
    cfg = load_config(base_dir)

    node_id = cfg["node"]["id"]
    server_url = cfg["server"]["url"]
    interval = cfg["simulation"]["interval_seconds"]
    source_kind = cfg["sensor_source"]

    sensor = create_sensor_source(cfg)
    sender = Sender(
        url=server_url,
        buffer_path=base_dir / "telemetry_buffer.jsonl",
    )

    log.info("node id=%s source=%s", node_id, source_kind)
    log.info("server url=%s", server_url)
    log.info("sending every %ss. Ctrl+C to stop.", interval)

    try:
        while True:
            reading = sensor.read()
            ok = sender.send(node_id, reading)

            status = "→ sent" if ok else "→ buffered (server unreachable)"
            log.info(
                "CPU=%5.2f°C CASE=%5.2f°C HUM=%5.2f%% I=%4.2fA U=%5.2fV FAN=%4drpm  %s",
                reading.cpu_temp_c, reading.case_temp_c, reading.humidity_pct,
                reading.current_a, reading.voltage_v, reading.fan_rpm, status,
            )
            time.sleep(interval)
    except KeyboardInterrupt:
        log.info("stopped.")


if __name__ == "__main__":
    main()