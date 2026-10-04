"""Точка входа агента узла."""
import logging
import time
from pathlib import Path

from .actions import Actions
from .config import load_config
from .incidents import IncidentLog
from .sender import Sender
from .sensors import create_sensor_source
from .thresholds import EvaluationResult, evaluate

logging.Formatter.converter = time.gmtime
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
    thresholds_cfg = cfg.get("thresholds", {})
    actions_cfg = cfg.get("actions", {})

    sensor = create_sensor_source(cfg)
    sender = Sender(
        url=server_url,
        buffer_path=base_dir / "telemetry_buffer.jsonl",
    )
    incidents = IncidentLog(
        path=base_dir / "incidents.jsonl",
        node_id=node_id,
    )
    actions = Actions(
        sensor=sensor,
        fan_on_at=actions_cfg.get("fan_on_at_cpu_temp_c", 75),
        fan_off_at=actions_cfg.get("fan_off_at_cpu_temp_c", 60),
    )

    log.info("node id=%s source=%s", node_id, source_kind)
    log.info("server url=%s", server_url)
    log.info("sending every %ss. Ctrl+C to stop.", interval)
    log.info("incidents log: %s (%d records)", incidents.path, incidents.count())
    log.info(
        "fan policy: ON at >= %.1f°C, OFF at <= %.1f°C",
        actions._fan_on_at, actions._fan_off_at,
    )

    prev_result: EvaluationResult | None = None

    try:
        while True:
            reading = sensor.read()

            # ─── Оценка по порогам ───────────────────
            result = evaluate(reading, thresholds_cfg)
            incidents.record_changes(result, prev_result)
            prev_result = result

            # ─── Действия (вентилятор) ───────────────
            decision = actions.apply(reading)

            # ─── Отправка на сервер ──────────────────
            ok = sender.send(node_id, reading)
            status = "→ sent" if ok else "→ buffered (server unreachable)"
            fan_marker = " [FAN CHANGED]" if decision.changed else ""
            log.info(
                "CPU=%5.2f°C CASE=%5.2f°C HUM=%5.2f%% I=%4.2fA U=%5.2fV FAN=%4drpm  %s%s",
                reading.cpu_temp_c, reading.case_temp_c, reading.humidity_pct,
                reading.current_a, reading.voltage_v, reading.fan_rpm,
                status, fan_marker,
            )
            time.sleep(interval)
    except KeyboardInterrupt:
        log.info(
            "stopped. total incidents: %d, fan state: %s",
            incidents.count(), "ON" if actions.fan_state else "OFF",
        )


if __name__ == "__main__":
    main()