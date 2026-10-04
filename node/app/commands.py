"""Забор и выполнение команд с сервера."""
import logging
from dataclasses import dataclass
from typing import Callable

import httpx

from .actions import Actions

log = logging.getLogger(__name__)


@dataclass
class CommandResult:
    ok: bool
    message: str


class CommandPoller:
    def __init__(
        self,
        url: str,
        token: str,
        node_id: str,
        actions: Actions,
        on_restart: Callable[[], None],
        on_set_thresholds: Callable[[dict], None] | None = None,
        timeout: float = 5.0,
    ) -> None:
        self._url = url.rstrip("/")
        self._node_id = node_id
        self._actions = actions
        self._on_restart = on_restart
        self._on_set_thresholds = on_set_thresholds
        self._headers = {
            "X-Node-Token": token,
            "Content-Type": "application/json",
        }
        self._client = httpx.Client(timeout=timeout)

    def poll_once(self) -> list[dict]:
        try:
            r = self._client.get(
                f"{self._url}/nodes/{self._node_id}/commands/pending",
                headers=self._headers,
            )
            r.raise_for_status()
        except Exception as e:
            log.debug("command poll failed: %s", e)
            return []

        commands = r.json()
        if not commands:
            return []

        log.info("received %d command(s) from server", len(commands))
        executed: list[dict] = []
        for cmd in commands:
            result = self._execute(cmd)
            self._ack(cmd["id"], result)
            executed.append({"id": cmd["id"], "type": cmd["type"], "ok": result.ok})
        return executed

    def _execute(self, cmd: dict) -> CommandResult:
        ctype = cmd.get("type")
        payload = cmd.get("payload") or {}
        log.warning("executing command id=%s type=%s", cmd["id"], ctype)

        try:
            if ctype == "fan_on":
                d = self._actions.force_fan(True)
                return CommandResult(True, d.reason)
            if ctype == "fan_off":
                d = self._actions.force_fan(False)
                return CommandResult(True, d.reason)
            if ctype == "restart":
                self._on_restart()
                return CommandResult(True, "restart requested")
            if ctype == "set_mode":
                mode = payload.get("mode")
                if mode not in ("auto", "manual"):
                    return CommandResult(False, f"invalid mode: {mode!r}")
                self._actions.set_mode(mode)
                return CommandResult(True, f"mode set to {mode}")
            if ctype == "set_thresholds":
                if self._on_set_thresholds is None:
                    return CommandResult(False, "set_thresholds not supported")
                self._on_set_thresholds(payload)
                return CommandResult(True, "thresholds applied")
            return CommandResult(False, f"unknown command type: {ctype!r}")
        except Exception as e:
            log.exception("command execution failed: %s", e)
            return CommandResult(False, f"error: {e}")

    def _ack(self, cmd_id: int, result: CommandResult) -> None:
        try:
            r = self._client.post(
                f"{self._url}/nodes/{self._node_id}/commands/{cmd_id}/ack",
                headers=self._headers,
                json={
                    "status": "done" if result.ok else "failed",
                    "result": result.message,
                },
            )
            r.raise_for_status()
            log.info("command %s ack: %s", cmd_id, result.message)
        except Exception as e:
            log.warning("command %s ack failed: %s", cmd_id, e)