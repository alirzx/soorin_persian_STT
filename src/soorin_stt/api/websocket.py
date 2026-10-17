"""Streaming contract shared by native models and bounded offline pseudo-streaming.

Clients send session.start, 16 kHz mono signed PCM16 frames, session.end.
The server emits session.ready, transcript.partial/segment/final, session.closed.
"""
from __future__ import annotations

import asyncio
import hmac
import json
import logging
import time
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from soorin_stt.audio.formats import pcm_s16le_to_float
from soorin_stt.core.exceptions import Overloaded, STTError
from soorin_stt.core.inference import run_native
from soorin_stt.observability.metrics import (
    ACTIVE, FINAL, PARTIAL, STREAM_AUDIO, STREAM_ERRORS, STREAM_INFERENCE,
    STREAM_OVERFLOW, STREAM_QUEUE_DEPTH, STREAM_RTF, STREAM_SEGMENTS, STREAM_SESSIONS,
)
from soorin_stt.schemas.requests import StreamStart
from soorin_stt.streaming.windowed import WindowedSpeech
from soorin_stt.text.persian_normalizer import normalize_text

logger = logging.getLogger(__name__)
router = APIRouter()


def _text(text: str, session: StreamStart, settings) -> tuple[str, list]:
    return normalize_text(text, session.domain, settings.text_itn) if session.normalize else (text, [])


@router.websocket("/v1/audio/transcriptions/stream")
async def stream(ws: WebSocket):
    service = ws.app.state.service
    settings = service.settings
    if settings.app_api_key and not hmac.compare_digest(
        ws.headers.get("x-api-key", ""), settings.app_api_key
    ):
        await ws.close(code=1008, reason="unauthorized")
        return
    if not service.ready:
        await ws.close(code=1013, reason="model not ready")
        return
    try:
        await service.sessions.enter()
    except Overloaded:
        await ws.close(code=1013, reason="max sessions reached")
        return

    await ws.accept()
    ACTIVE.inc()
    started = time.monotonic()
    q: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=settings.stream_queue_max_frames)
    worker: asyncio.Task | None = None
    native_stream = None
    samples_total = 0
    outcome = "closed"

    try:
        session = StreamStart.model_validate(
            await asyncio.wait_for(ws.receive_json(), timeout=10)
        )
        native = service.backend.features.true_streaming
        if native:
            native_stream = await run_native(
                service, service.backend.open_stream, settings.audio_sample_rate
            )
        else:
            window = WindowedSpeech(
                settings.audio_sample_rate, settings.vad_rms_threshold,
                settings.vad_min_speech_ms, settings.vad_min_silence_ms,
                settings.stream_window_max_seconds,
            )
        await ws.send_json({
            "type": "session.ready", "session_id": str(uuid.uuid4()),
            "model": service.model.name, "streaming_mode": "native" if native else "buffered",
            "sample_rate": settings.audio_sample_rate,
        })

        async def emit(event: str, seq: int, text: str, **fields):
            clean, entities = _text(text, session, settings)
            await ws.send_json({
                "type": event, "sequence": seq, "text": text,
                "normalized_text": clean, "entities": entities if event == "transcript.final" else [],
                **fields,
            })

        async def decode(audio, phase: str):
            begun = time.monotonic()
            result = await run_native(
                service, service.backend.transcribe, audio, settings.audio_sample_rate
            )
            elapsed = time.monotonic() - begun
            STREAM_INFERENCE.labels(phase=phase).observe(elapsed)
            STREAM_RTF.observe(elapsed / max(len(audio) / settings.audio_sample_rate, 0.001))
            return result.text

        async def consume():
            nonlocal samples_total
            seq = 0
            first_partial = False
            last_partial = ""
            last_decode = 0.0
            native_text = ""
            async def publish_partial(text: str):
                nonlocal seq, last_partial, first_partial
                if text and text != last_partial:
                    if not first_partial:
                        PARTIAL.observe(time.monotonic() - started)
                        first_partial = True
                    seq += 1
                    await emit("transcript.partial", seq, text)
                    last_partial = text

            async def seal():
                nonlocal seq
                if not window.window_samples:
                    return
                if window.has_speech():
                    text = await decode(window.window(), "segment")
                    full = window.seal(text)
                    STREAM_SEGMENTS.inc()
                    seq += 1
                    await emit("transcript.segment", seq, full)
                    await publish_partial(full)
                else:
                    window.seal("")

            while True:
                item = await q.get()
                try:
                    STREAM_QUEUE_DEPTH.observe(q.qsize())
                    if item is None:
                        begun = time.monotonic()
                        if native:
                            text = await run_native(service, native_stream.finish)
                            STREAM_INFERENCE.labels(phase="final").observe(time.monotonic() - begun)
                        else:
                            await seal()
                            text = window.transcript()
                        FINAL.observe(time.monotonic() - begun)
                        seq += 1
                        await emit("transcript.final", seq, text, start_ms=0,
                                   end_ms=round(samples_total * 1000 / settings.audio_sample_rate))
                        await ws.send_json({"type": "session.closed"})
                        return
                    samples = pcm_s16le_to_float(item)
                    samples_total += len(samples)
                    STREAM_AUDIO.inc(len(samples) / settings.audio_sample_rate)
                    if samples_total > settings.stream_max_seconds * settings.audio_sample_rate:
                        raise ValueError("Maximum stream audio duration exceeded")
                    if native:
                        begun = time.monotonic()
                        native_text = await run_native(service, native_stream.accept, samples)
                        STREAM_INFERENCE.labels(phase="native").observe(time.monotonic() - begun)
                        await publish_partial(native_text)
                    else:
                        ready = window.push(samples)
                        if ready:
                            await seal()
                        elif window.has_speech() and (
                            window.buffered_seconds() >= settings.stream_partial_min_audio_seconds
                            and time.monotonic() - last_decode >= settings.stream_partial_decode_interval_seconds
                        ):
                            hypothesis = await decode(window.window(), "partial")
                            await publish_partial(window.transcript(hypothesis))
                            last_decode = time.monotonic()
                finally:
                    q.task_done()

        worker = asyncio.create_task(consume())
        while True:
            receiving = asyncio.create_task(ws.receive())
            done, _ = await asyncio.wait(
                {receiving, worker}, timeout=settings.stream_idle_timeout_seconds,
                return_when=asyncio.FIRST_COMPLETED,
            )
            if worker in done:
                receiving.cancel()
                await worker
                break
            if receiving not in done:
                receiving.cancel()
                raise asyncio.TimeoutError()
            message = await receiving
            if message.get("type") == "websocket.disconnect":
                outcome = "disconnected"
                break
            if message.get("text") is not None:
                try:
                    control = json.loads(message["text"])
                except (TypeError, json.JSONDecodeError) as exc:
                    raise ValueError("Malformed control JSON") from exc
                if control.get("type") == "session.end":
                    await asyncio.wait_for(q.put(None), timeout=settings.stream_idle_timeout_seconds)
                    await worker
                    outcome = "ok"
                    break
                if control.get("type") == "session.ping":
                    await ws.send_json({"type": "session.pong"})
                    continue
                raise ValueError("Unexpected stream control message")
            frame = message.get("bytes")
            if frame is None:
                continue
            if not frame or len(frame) % 2 or len(frame) > settings.stream_max_frame_bytes:
                raise ValueError("Invalid PCM frame size")
            try:
                q.put_nowait(frame)
            except asyncio.QueueFull as exc:
                STREAM_OVERFLOW.inc()
                raise Overloaded("Input exceeded audio queue capacity") from exc
    except WebSocketDisconnect:
        outcome = "disconnected"
    except asyncio.TimeoutError:
        outcome = "timeout"
        STREAM_ERRORS.labels(code="timeout").inc()
        try:
            await ws.send_json({"type": "session.error", "code": "timeout", "message": "Stream idle timeout"})
        except Exception:
            pass
    except (ValidationError, ValueError, STTError) as exc:
        outcome = "invalid"
        STREAM_ERRORS.labels(code="invalid_session").inc()
        try:
            await ws.send_json({"type": "session.error", "code": "invalid_session", "message": str(exc)})
        except Exception:
            pass
    except Exception:
        outcome = "internal"
        STREAM_ERRORS.labels(code="internal").inc()
        logger.exception("Streaming inference error")
        try:
            await ws.send_json({"type": "session.error", "code": "internal_error", "message": "Stream processing failed"})
        except Exception:
            pass
    finally:
        if worker and not worker.done():
            worker.cancel()
            try:
                await worker
            except (asyncio.CancelledError, Exception):
                pass
        if native_stream:
            try:
                await asyncio.to_thread(native_stream.close)
            except Exception:
                pass
        ACTIVE.dec()
        STREAM_SESSIONS.labels(outcome=outcome).inc()
        await service.sessions.leave()
        try:
            await ws.close()
        except Exception:
            pass
