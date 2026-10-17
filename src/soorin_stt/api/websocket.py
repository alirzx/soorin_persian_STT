from __future__ import annotations
import asyncio
import json
import logging
import time
import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError
from soorin_stt.audio.formats import pcm_s16le_to_float
from soorin_stt.core.exceptions import STTError, Overloaded
from soorin_stt.schemas.requests import StreamStart
from soorin_stt.text.persian_normalizer import normalize_text
from soorin_stt.backends.base import BufferedStream
from soorin_stt.audio.vad import has_speech
from soorin_stt.observability.metrics import ACTIVE, PARTIAL, FINAL, STREAM_ERRORS

logger = logging.getLogger(__name__)
router = APIRouter()

async def _send(ws: WebSocket, event_type: str, sequence: int, text: str = '', **other):
    await ws.send_json({'type': event_type, 'sequence': sequence, 'text': text, **other})

@router.websocket('/v1/audio/transcriptions/stream')
async def stream(ws: WebSocket):
    service = ws.app.state.service
    settings = service.settings
    if settings.app_api_key and ws.headers.get('x-api-key') != settings.app_api_key:
        await ws.close(code=1008, reason='unauthorized')
        return
    if not service.ready:
        await ws.close(code=1013, reason='model not ready')
        return
    try:
        await service.sessions.enter()
    except Overloaded:
        await ws.close(code=1013, reason='max sessions reached')
        return
    await ws.accept()
    ACTIVE.inc()
    asr = None
    worker = None
    q = asyncio.Queue(maxsize=settings.stream_queue_max_frames)
    samples_total = 0
    last_speech = 0.0
    started = time.monotonic()
    try:
        session = StreamStart.model_validate(await asyncio.wait_for(ws.receive_json(), timeout=10))
        asr = await asyncio.to_thread(service.backend.open_stream, settings.audio_sample_rate)
        await ws.send_json({'type': 'session.ready', 'session_id': str(uuid.uuid4()),
                            'model': service.model.name,
                            'streaming_mode': 'native' if service.backend.features.true_streaming else 'buffered',
                            'sample_rate': settings.audio_sample_rate})

        async def consume():
            nonlocal samples_total, last_speech
            seq = 0
            last_partial = ''
            first_partial = False
            last_emit = 0.0
            last_decode = 0.0
            while True:
                item = await q.get()
                try:
                    if item is None:
                        t = time.monotonic()
                        async with service.inference_slots:
                            text = await asyncio.to_thread(asr.finish)
                        FINAL.observe(time.monotonic() - t)
                        clean, entities = normalize_text(text, session.domain, settings.text_itn) if session.normalize else (text, [])
                        seq += 1
                        await _send(ws, 'transcript.final', seq, text,
                                    normalized_text=clean, start_ms=0,
                                    end_ms=round(samples_total * 1000 / settings.audio_sample_rate),
                                    entities=entities)
                        await ws.send_json({'type': 'session.closed'})
                        return
                    samples = pcm_s16le_to_float(item)
                    samples_total += len(samples)
                    if samples_total > settings.stream_max_seconds * settings.audio_sample_rate:
                        raise ValueError('Maximum stream audio duration exceeded')
                    if settings.vad_enabled and has_speech(samples, settings.vad_rms_threshold):
                        last_speech = time.monotonic()
                    async with service.inference_slots:
                        partial = await asyncio.to_thread(asr.accept, samples)
                    now = time.monotonic()
                    if (now - last_emit) * 1000 >= settings.stream_partial_interval_ms:
                        if isinstance(asr, BufferedStream):
                            # The buffer is an explicitly non-native fallback, not cache-aware ASR.
                            if samples_total >= settings.audio_sample_rate and now - last_decode >= 1.5:
                                async with service.inference_slots:
                                    partial = await asyncio.to_thread(asr.partial)
                                last_decode = now
                            else:
                                partial = last_partial
                        if partial != last_partial and partial.strip():
                            if not first_partial:
                                PARTIAL.observe(now - started)
                                first_partial = True
                            seq += 1
                            clean, _ = normalize_text(partial, session.domain, settings.text_itn) if session.normalize else (partial, [])
                            await _send(ws, 'transcript.partial', seq, partial, normalized_text=clean)
                            last_partial = partial
                        last_emit = now
                finally:
                    q.task_done()

        worker = asyncio.create_task(consume())
        while True:
            # Read tasks are concurrent with inference. Queue maxsize prevents unbounded accumulation.
            receive = asyncio.create_task(ws.receive())
            finished, _ = await asyncio.wait({receive, worker}, timeout=settings.stream_idle_timeout_seconds,
                                              return_when=asyncio.FIRST_COMPLETED)
            if worker in finished:
                receive.cancel()
                await worker
                break
            if receive not in finished:
                receive.cancel()
                raise asyncio.TimeoutError()
            message = await receive
            if message.get('type') == 'websocket.disconnect':
                break
            if message.get('text') is not None:
                try:
                    control = json.loads(message['text'])
                except (json.JSONDecodeError, TypeError) as exc:
                    raise ValueError('Malformed control JSON') from exc
                if control.get('type') == 'session.end':
                    await asyncio.wait_for(q.put(None),timeout=10)
                    await worker
                    break
                if control.get('type') == 'session.ping':
                    await ws.send_json({'type': 'session.pong'})
                    continue
                raise ValueError('Unexpected stream control message')
            frame = message.get('bytes')
            if frame is None:
                continue
            if len(frame) > settings.stream_max_frame_bytes or len(frame) == 0 or len(frame) % 2:
                raise ValueError('Invalid PCM frame size')
            try:
                q.put_nowait(frame)
            except asyncio.QueueFull as exc:
                raise Overloaded('Audio input exceeds bounded stream queue') from exc
    except WebSocketDisconnect:
        pass
    except asyncio.TimeoutError:
        STREAM_ERRORS.labels(code='timeout').inc()
        try: await ws.send_json({'type':'session.error','code':'timeout','message':'Stream idle timeout'})
        except Exception: pass
    except (ValidationError, ValueError, STTError) as exc:
        STREAM_ERRORS.labels(code='invalid_session').inc()
        try: await ws.send_json({'type':'session.error','code':'invalid_session','message':str(exc)})
        except Exception: pass
    except Exception:
        STREAM_ERRORS.labels(code='internal').inc()
        logger.exception('Streaming inference error')
        try: await ws.send_json({'type':'session.error','code':'internal_error','message':'Stream processing failed'})
        except Exception: pass
    finally:
        if worker and not worker.done():
            worker.cancel()
            try: await worker
            except (asyncio.CancelledError, Exception): pass
        if asr:
            try: await asyncio.to_thread(asr.close)
            except Exception: pass
        ACTIVE.dec()
        await service.sessions.leave()
        try: await ws.close()
        except Exception: pass
