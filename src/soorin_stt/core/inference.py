"""Run blocking native inference without releasing capacity on an HTTP timeout.

A Python thread cannot be safely killed. The semaphore therefore belongs to the
actual worker task and is released only once that task has exited, including when
the requester times out or disconnects. A timed-out call cannot silently allow
another concurrent invocation of the same native recognizer.
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from typing import Any

from soorin_stt.core.exceptions import Overloaded, InferenceTimedOut
from soorin_stt.observability.metrics import CAPACITY_WAIT, INFERENCE_IN_FLIGHT

logger = logging.getLogger(__name__)


async def run_native(state: Any, fn: Callable[..., Any], *args: Any, timeout: float | None = None) -> Any:
    settings = state.settings
    waited = time.monotonic()
    try:
        await asyncio.wait_for(
            state.inference_slots.acquire(), timeout=settings.app_slot_wait_seconds
        )
    except asyncio.TimeoutError as exc:
        raise Overloaded("Inference capacity is busy; retry later") from exc

    CAPACITY_WAIT.observe(time.monotonic() - waited)
    INFERENCE_IN_FLIGHT.inc()
    try:
        task = asyncio.create_task(asyncio.to_thread(fn, *args))
    except BaseException:
        state.inference_slots.release()
        INFERENCE_IN_FLIGHT.dec()
        raise

    def finished(completed: asyncio.Task) -> None:
        state.inference_slots.release()
        INFERENCE_IN_FLIGHT.dec()
        if not completed.cancelled():
            try:
                completed.result()
            except Exception:
                logger.exception("Detached native inference finished with an error")

    task.add_done_callback(finished)
    try:
        # Shield protects the underlying native call from request cancellation.
        return await asyncio.wait_for(
            asyncio.shield(task),
            timeout=settings.app_request_timeout_seconds if timeout is None else timeout,
        )
    except asyncio.TimeoutError as exc:
        logger.warning("Native inference timed out; capacity held until worker returns")
        raise InferenceTimedOut("Inference deadline exceeded") from exc
