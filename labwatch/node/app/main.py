import time
from pathlib import Path

from .config import load_config
from .sensors import create_sensor_source


def main():
    base_dir = Path(__file__).resolve().parent.parent
    config = load_config(base_dir / "config" / "node.yaml")

    node_id = config["node"]["id"]
    interval = config["simulation"]["interval_seconds"]

    sensor = create_sensor_source(config)

    print(f"[node] id={node_id}, source={config['sensor_source']}")
    print(f"[node] reading every {interval}s. Ctrl+C to stop.\n")

    try:
        while True:
            reading = sensor.read()
            print(
                f"CPU={reading.cpu_temp_c:5.2f}°C  "
                f"CASE={reading.case_temp_c:5.2f}°C  "
                f"HUM={reading.humidity_pct:5.2f}%  "
                f"I={reading.current_a:4.2f}A  "
                f"U={reading.voltage_v:5.2f}V  "
                f"FAN={reading.fan_rpm:4d}rpm"
            )
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n[node] stopped.")


if __name__ == "__main__":
    main()