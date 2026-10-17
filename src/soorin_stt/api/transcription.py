from __future__ import annotations
import asyncio
import time
import uuid
from fastapi import APIRouter,Depends,File,UploadFile,Form,HTTPException
from soorin_stt.api.dependencies import get_state
from soorin_stt.core.lifecycle import ServiceState
from soorin_stt.audio.decoder import decode_audio
from soorin_stt.text.persian_normalizer import normalize_text
from soorin_stt.schemas.responses import TranscriptResponse
from soorin_stt.observability.metrics import REQUESTS,AUDIO_SECONDS,INFERENCE,RTF
router=APIRouter()

@router.post('/v1/audio/transcriptions',response_model=TranscriptResponse)
async def transcribe(file:UploadFile=File(...),language:str=Form('fa'),
                     timestamps:bool=Form(False),normalize:bool=Form(True),domain:str=Form('general'),
                     state:ServiceState=Depends(get_state)):
    if language!='fa' or domain not in {'general','soc'}:
        raise HTTPException(status_code=422,detail='Supported language fa, domains general/soc')
    # bounded read instead of consuming an arbitrarily large upload into RAM
    cap=state.settings.app_max_upload_mb*1024*1024
    payload=await file.read(cap+1)
    if len(payload)>cap:
        raise HTTPException(status_code=413,detail='Audio upload too large')
    audio=decode_audio(payload,state.settings.audio_sample_rate,state.settings.audio_max_seconds)
    duration=len(audio)/state.settings.audio_sample_rate
    try:
        await asyncio.wait_for(state.inference_slots.acquire(),timeout=1)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=429,detail='Inference capacity reached')
    started=time.monotonic()
    try:
        result=await asyncio.wait_for(asyncio.to_thread(state.backend.transcribe,audio,state.settings.audio_sample_rate),
                                      timeout=state.settings.app_request_timeout_seconds)
    except Exception:
        REQUESTS.labels(status='error').inc()
        raise
    finally:
        state.inference_slots.release()
    processing=time.monotonic()-started
    clean,entities=normalize_text(result.text,domain,state.settings.text_itn) if normalize else (result.text,[])
    REQUESTS.labels(status='ok').inc();AUDIO_SECONDS.inc(duration)
    INFERENCE.observe(processing);RTF.observe(processing/max(duration,.001))
    return TranscriptResponse(request_id=str(uuid.uuid4()),model=state.model.name,
                              text=result.text,normalized_text=clean,
                              duration_ms=round(duration*1000),processing_ms=round(processing*1000),
                              rtf=round(processing/max(duration,.001),4),
                              segments=result.segments if timestamps else [],entities=entities,
                              streaming_mode='native' if state.backend.features.true_streaming else 'buffered')
