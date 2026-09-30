"""Загрузка конфигурации узла.

Приоритет: переменные окружения (.env) > YAML.
Так URL сервера и id узла можно менять одной строкой в .env,
не трогая YAML.
"""
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv


def load_config(base_dir: Path) -> dict:
    load_dotenv(base_dir / ".env")

    cfg_path = base_dir / "config" / "node.yaml"
    if not cfg_path.exists():
        raise FileNotFoundError(f"Config not found: {cfg_path}")

    with cfg_path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    # .env перекрывает yaml
    cfg["server"] = {
        "url": os.environ.get("LABWATCH_URL", "http://localhost:8000"),
        "send_interval_seconds": cfg.get("simulation", {}).get("interval_seconds", 5),
    }
    cfg["node"]["id"] = os.environ.get("NODE_ID", cfg["node"]["id"])

    return cfg