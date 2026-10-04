"""Watchdog: следит за серией неудачных отправок на сервер.

Если узел не может донести данные N раз подряд — считаем, что
«что-то сломалось», и просим main() перезапуститься.

На реальной Raspberry Pi это делал бы systemd: рестарт сервиса
labwatch-node. Здесь мы эмулируем: логируем событие и корректно
завершаем процесс. Внешний супервизор поднимет узел снова.
"""
import logging
from dataclasses import dataclass

log = logging.getLogger(__name__)


@dataclass
class WatchdogDecision:
    """Сигнал main(): продолжать работу или перезагружаться."""
    should_restart: bool
    consecutive_failures: int
    reason: str = ""


class Watchdog:
    def __init__(
        self,
        enabled: bool = True,
        restart_after_failures: int = 3,
    ) -> None:
        self._enabled = enabled
        self._threshold = max(1, int(restart_after_failures))
        self._consecutive_failures = 0

    @property
    def consecutive_failures(self) -> int:
        return self._consecutive_failures

    def report(self, success: bool) -> WatchdogDecision:
        """Сообщить результат последней попытки отправки.

        success=True   — сбрасываем счётчик.
        success=False  — увеличиваем. Если достигли порога — сигнал.
        """
        if not self._enabled:
            return WatchdogDecision(False, 0)

        if success:
            if self._consecutive_failures > 0:
                log.info(
                    "watchdog: connection restored after %d failures",
                    self._consecutive_failures,
                )
            self._consecutive_failures = 0
            return WatchdogDecision(False, 0)

        self._consecutive_failures += 1
        log.warning(
            "watchdog: failure %d/%d",
            self._consecutive_failures, self._threshold,
        )

        if self._consecutive_failures >= self._threshold:
            reason = (
                f"{self._consecutive_failures} consecutive send failures "
                f"(threshold {self._threshold})"
            )
            log.error("watchdog triggered: %s", reason)
            return WatchdogDecision(
                should_restart=True,
                consecutive_failures=self._consecutive_failures,
                reason=reason,
            )

        return WatchdogDecision(
            should_restart=False,
            consecutive_failures=self._consecutive_failures,
        )