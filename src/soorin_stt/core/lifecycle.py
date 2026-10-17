from __future__ import annotations
import asyncio
import logging
import time
from soorin_stt.backends.registry import resolve,build_backend,ModelSpec
from soorin_stt.core.config import Settings
from soorin_stt.observability.metrics import MODEL_LOADED,MODEL_LOAD
from soorin_stt.streaming.backpressure import SessionCapacity

logger=logging.getLogger(__name__)
class ServiceState:
    def __init__(self,settings:Settings):
        self.settings=settings
        self.model:ModelSpec|None=None
        self.backend=None
        self.ready=False
        self.load_error:str|None=None
        self.inference_slots=asyncio.Semaphore(settings.app_inference_concurrency)
        self.sessions=SessionCapacity(settings.stream_max_sessions)
    async def start(self)->None:
        self.ready=False
        start=time.monotonic()
        try:
            self.model=resolve(self.settings)
            if self.model.backend != 'external_http' and self.settings.stt_require_model_pin:
                from soorin_stt.models_cli import verify
                await asyncio.to_thread(verify, self.model.name)
            self.backend=build_backend(self.settings,self.model)
            # Native runtimes are synchronous: never block the HTTP event loop.
            await asyncio.to_thread(self.backend.load)
            if self.settings.stt_warmup:
                await asyncio.to_thread(self.backend.warmup)
            self.ready=True
            MODEL_LOADED.set(1)
            logger.info('Model ready: %s (%s)',self.model.name,self.model.backend)
        except Exception as exc:
            self.load_error=f'{type(exc).__name__}: {exc}'
            logger.error('Model readiness failed: %s',self.load_error)
            MODEL_LOADED.set(0)
        finally:
            MODEL_LOAD.observe(time.monotonic()-start)
    async def stop(self):
        self.ready=False;MODEL_LOADED.set(0)
        if self.backend:
            await asyncio.to_thread(self.backend.close)
