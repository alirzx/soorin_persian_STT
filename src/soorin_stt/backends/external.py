from __future__ import annotations
import httpx
import numpy as np
import io
import soundfile as sf
from soorin_stt.backends.base import BackendFeatures, STTBackend, Recognition
from soorin_stt.core.exceptions import ModelUnavailable

class ExternalHTTPBackend(STTBackend):
    """Adapter for separately managed runtimes; provides batch and buffered WS fallback.

    Can integrate a licensed/configured tract inference gateway without embedding Rust in Python.
    Its remote endpoint MUST implement POST /v1/audio/transcriptions.
    """
    features = BackendFeatures(true_streaming=False, pseudo_streaming=True)
    def __init__(self, base_url: str, timeout: float = 120):
        self.base_url, self.timeout = base_url.rstrip('/'), timeout
    def load(self) -> None:
        if not self.base_url.startswith(('http://','https://')):
            raise ModelUnavailable('STT_EXTERNAL_BASE_URL required for external backend')
        try:
            r=httpx.get(self.base_url+'/health/ready',timeout=5)
            r.raise_for_status()
        except Exception as exc:
            raise ModelUnavailable(f'External inference gateway unavailable: {exc}') from exc
    def transcribe(self, audio: np.ndarray, sample_rate: int) -> Recognition:
        buf=io.BytesIO()
        sf.write(buf,audio,sample_rate,format='WAV',subtype='PCM_16')
        with httpx.Client(timeout=self.timeout) as client:
            r=client.post(self.base_url+'/v1/audio/transcriptions',files={'file':('audio.wav',buf.getvalue(),'audio/wav')},data={'language':'fa'})
            r.raise_for_status()
            data=r.json()
        return Recognition(data['text'],data.get('segments',[]))
