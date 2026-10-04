"""Синхронизация конфига узла с сервером.

Раз в N секунд узел делает GET /nodes/{id}/config. Если config_version
на сервере больше локального — применяет mode, пороги и настройки
вентилятора.

Это позволяет Android-приложению менять режим и пороги через
PUT /config, а узел подхватывает изменения автоматически.
"""
import logging

import httpx

from .actions import Actions

log = logging.getLogger(__name__)


class ConfigSync:
    def __init__(
        self,
        url: str,
        token: str,
        node_id: str,
        actions: Actions,
        on_thresholds: callable,
        timeout: float = 5.0,
    ) -> None:
        self._url = url.rstrip("/")
        self._node_id = node_id
        self._actions = actions
        self._on_thresholds = on_thresholds
        self._headers = {"X-Node-Token": token}
        self._client = httpx.Client(timeout=timeout)
        self._local_version = 0

    def poll_once(self) -> bool:
        """Забрать конфиг. Вернуть True, если что-то применилось."""
        try:
            r = self._client.get(
                f"{self._url}/nodes/{self._node_id}/config",
                headers=self._headers,
            )
            r.raise_for_status()
        except Exception as e:
            log.debug("config poll failed: %s", e)
            return False

        cfg = r.json()
        remote_version = cfg.get("config_version", 1)
        if remote_version <= self._local_version:
            return False

        self._apply(cfg, remote_version)
        return True

    def _apply(self, cfg: dict, remote_version: int) -> None:
        mode = cfg.get("mode")
        if mode:
            try:
                self._actions.set_mode(mode)
            except ValueError as e:
                log.warning("config: invalid mode %r: %s", mode, e)

        fan_on = cfg.get("fan_on_at_cpu_temp_c")
        fan_off = cfg.get("fan_off_at_cpu_temp_c")
        if fan_on is not None and fan_off is not None:
            try:
                self._actions.set_thresholds(fan_on, fan_off)
            except ValueError as e:
                log.warning("config: invalid thresholds: %s", e)

        thresholds = cfg.get("thresholds")
        if thresholds:
            try:
                self._on_thresholds(thresholds)
            except Exception as e:
                log.warning("config: thresholds apply failed: %s", e)

        self._local_version = remote_version
        log.warning(
            "config applied: version=%d mode=%s fan_on=%.1f fan_off=%.1f",
            remote_version, self._actions.mode, fan_on or 0, fan_off or 0,
        )