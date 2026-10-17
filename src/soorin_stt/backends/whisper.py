from __future__ import annotations
from pathlib import Path
import numpy as np
from soorin_stt.backends.base import BackendFeatures, Recognition, STTBackend
from soorin_stt.core.exceptions import ModelUnavailable

class WhisperBackend(STTBackend):
    features = BackendFeatures(true_streaming=False, pseudo_streaming=True)
    def __init__(self, root: Path, threads: int, compute_type: str = 'int8', device: str = 'cpu'):
        self.root, self.threads, self.compute_type, self.device = root, threads, compute_type, device
        self.model = None
    def load(self) -> None:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise ModelUnavailable('Install pip install -e .[whisper]') from exc
        if not (self.root / 'ct2' / 'config.json').exists():
            raise ModelUnavailable('Faster-whisper requires a locally converted CTranslate2 directory (config.json). Run scripts/convert_whisper.py.')
        self.model = WhisperModel(str(self.root / "ct2"), device=self.device, compute_type=self.compute_type,
                                  cpu_threads=self.threads, local_files_only=True)
    def transcribe(self, audio: np.ndarray, sample_rate: int) -> Recognition:
        if self.model is None:
            raise ModelUnavailable('Whisper model not loaded')
        segments, _ = self.model.transcribe(audio, language='fa', beam_size=3, vad_filter=False, condition_on_previous_text=False)
        chunks = list(segments)
        return Recognition(' '.join(s.text.strip() for s in chunks).strip(),
                           [{'start_ms':int(s.start*1000),'end_ms':int(s.end*1000),'text':s.text.strip()} for s in chunks])
