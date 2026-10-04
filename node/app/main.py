"""Точка входа агента узла."""
import logging
import sys
import time
from pathlib import Path

from .actions import Actions
from .commands import CommandPoller
from .config import load_config
from .config_sync import ConfigSync
from .incidents import IncidentLog
from .sender import Sender
from .sensors import create_sensor_source
from .thresholds import EvaluationResult, evaluate
from .watchdog import Watchdog

logging.Formatter.converter = time.gmtime
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("labwatch.node")


def main() -> int:
    base_dir = Path(__file__).resolve().parent.parent
    cfg = load_config(base_dir)

    node_id = cfg["node"]["id"]
    server_url = cfg["server"]["url"]
    server_token = cfg["server"]["token"]
    interval = cfg["simulation"]["interval_seconds"]
    source_kind = cfg["sensor_source"]
    scenario = cfg.get("simulation", {}).get("scenario", "normal")
    actions_cfg = cfg.get("actions", {})
    watchdog_cfg = actions_cfg.get("watchdog", {})

    # Локальный конфиг порогов — обновляется из config_sync
    runtime_cfg = {"thresholds": cfg.get("thresholds", {})}

    sensor = create_sensor_source(cfg)
    sender = Sender(
        url=server_url,
        buffer_path=base_dir / "telemetry_buffer.jsonl",
        token=server_token,
    )
    incidents = IncidentLog(
        path=base_dir / "incidents.jsonl",
        node_id=node_id,
    )
    actions = Actions(
        sensor=sensor,
        fan_on_at=actions_cfg.get("fan_on_at_cpu_temp_c", 75),
        fan_off_at=actions_cfg.get("fan_off_at_cpu_temp_c", 60),
        mode="auto",
    )
    watchdog = Watchdog(
        enabled=watchdog_cfg.get("enabled", True),
        restart_after_failures=watchdog_cfg.get("restart_after_failures", 3),
    )

    # Флаг «пора завершиться», выставляется командой restart или watchdog.
    restart_requested = {"flag": False}

    def request_restart() -> None:
        log.warning("restart requested — will exit after current loop")
        restart_requested["flag"] = True

    def apply_thresholds(new_thresholds: dict) -> None:
        # Мержим: локальный yaml — база, серверные значения переопределяют.
        merged = {**cfg.get("thresholds", {}), **new_thresholds}
        runtime_cfg["thresholds"] = merged
        log.warning(
            "thresholds merged from server: %d param(s) updated",
            len(new_thresholds),
        )

    poller = CommandPoller(
        url=server_url,
        token=server_token,
        node_id=node_id,
        actions=actions,
        on_restart=request_restart,
        on_set_thresholds=apply_thresholds,
    )
    config_sync = ConfigSync(
        url=server_url,
        token=server_token,
        node_id=node_id,
        actions=actions,
        on_thresholds=apply_thresholds,
    )

    log.info("node id=%s source=%s", node_id, source_kind)
    log.info("scenario=%s", scenario)
    log.info("server url=%s", server_url)
    log.info("sending every %ss. Ctrl+C to stop.", interval)
    log.info("incidents log: %s (%d records)", incidents.path, incidents.count())
    log.info(
        "fan policy: ON at >= %.1f°C, OFF at <= %.1f°C",
        actions._fan_on_at, actions._fan_off_at,
    )
    log.info(
        "watchdog: enabled=%s, threshold=%d",
        watchdog_cfg.get("enabled", True),
        watchdog_cfg.get("restart_after_failures", 3),
    )
    log.info("mode: %s", actions.mode)

    prev_result: EvaluationResult | None = None

    try:
        while True:
            reading = sensor.read()

            # ─── Оценка по порогам ───────────────────
            result = evaluate(reading, runtime_cfg["thresholds"])
            incidents.record_changes(result, prev_result)
            prev_result = result

            # ─── Действия (вентилятор) ───────────────
            decision = actions.apply(reading)

            # ─── Отправка на сервер ──────────────────
            ok = sender.send(node_id, reading)
            status = "→ sent" if ok else "→ buffered (server unreachable)"
            fan_marker = " [FAN CHANGED]" if decision.changed else ""
            log.info(
                "CPU=%5.2f°C CASE=%5.2f°C HUM=%5.2f%% I=%4.2fA U=%5.2fV FAN=%4drpm  %s%s [mode=%s]",
                reading.cpu_temp_c, reading.case_temp_c, reading.humidity_pct,
                reading.current_a, reading.voltage_v, reading.fan_rpm,
                status, fan_marker, actions.mode,
            )

            # ─── Забор команд с сервера ──────────────
            poller.poll_once()

            # ─── Синхронизация конфига ───────────────
            config_sync.poll_once()

            # ─── Watchdog ────────────────────────────
            wd = watchdog.report(success=ok)
            if wd.should_restart:
                incidents.record_system(
                    kind="watchdog_triggered",
                    message=wd.reason,
                    failures=wd.consecutive_failures,
                )
                log.error("watchdog: restarting node (exit code 0)")
                return 0

            # ─── Команда restart с сервера ───────────
            if restart_requested["flag"]:
                incidents.record_system(
                    kind="remote_restart",
                    message="restart command executed",
                )
                log.error("remote restart: exiting (exit code 0)")
                return 0

            time.sleep(interval)
    except KeyboardInterrupt:
        log.info(
            "stopped by user. total incidents: %d, fan state: %s, mode: %s",
            incidents.count(),
            "ON" if actions.fan_state else "OFF",
            actions.mode,
        )
        return 0


if __name__ == "__main__":
    sys.exit(main())