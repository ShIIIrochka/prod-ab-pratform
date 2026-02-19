from __future__ import annotations

import asyncio
import logging

from src.application.usecases.guardrails.check_guardrails import (
    CheckGuardrailsUseCase,
)


logger = logging.getLogger(__name__)


class GuardrailCheckerWorker:
    """Фоновый воркер для периодической проверки guardrails.

    Запускает CheckGuardrailsUseCase каждые `interval_seconds` секунд.
    Если очередная проверка завершается ошибкой — логирует и продолжает.
    """

    def __init__(
        self,
        check_use_case: CheckGuardrailsUseCase,
        interval_seconds: int = 60,
    ) -> None:
        self._check_use_case = check_use_case
        self._interval_seconds = interval_seconds

    async def start(self) -> None:
        logger.info(
            "[GuardrailChecker] Worker started, interval=%ds",
            self._interval_seconds,
        )
        while True:
            try:
                await self._check_use_case.execute()
                logger.debug("[GuardrailChecker] Check cycle completed")
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception(
                    "[GuardrailChecker] Error during guardrail check cycle"
                )

            await asyncio.sleep(self._interval_seconds)
