import asyncio
import threading
import pytest
from fastapi.testclient import TestClient
from soorin_stt.core.inference import run_native
from soorin_stt.core.exceptions import InferenceTimedOut, Overloaded
from soorin_stt.core.config import Settings
from soorin_stt.core.lifecycle import ServiceState


@pytest.mark.asyncio
async def test_timeout_keeps_capacity_until_real_worker_finishes():
    entered = threading.Event()
    release = threading.Event()
    s = ServiceState(Settings(app_request_timeout_seconds=1, app_slot_wait_seconds=.2, app_inference_concurrency=1))
    def slow():
        entered.set()
        release.wait(3)
        return 'completed'
    try:
        with pytest.raises(InferenceTimedOut):
            await run_native(s, slow, timeout=.05)
        assert entered.is_set()
        with pytest.raises(Overloaded):
            await run_native(s, lambda:'should not run')
    finally:
        release.set()
        await asyncio.sleep(.1)
    assert await run_native(s, lambda:'ok') == 'ok'
