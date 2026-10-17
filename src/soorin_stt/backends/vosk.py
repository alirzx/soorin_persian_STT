from __future__ import annotations
from pathlib import Path
import json
import numpy as np
from soorin_stt.backends.base import BackendFeatures, Recognition, STTBackend, Stream
from soorin_stt.core.exceptions import ModelUnavailable

class VoskStream(Stream):
    def __init__(self, model, sample_rate: int):
        from vosk import KaldiRecognizer
        self.rec = KaldiRecognizer(model, sample_rate)
    def accept(self, samples: np.ndarray) -> str:
        pcm = (np.clip(samples, -1, 1) * 32767).astype('<i2').tobytes()
        self.rec.AcceptWaveform(pcm)
        data = json.loads(self.rec.PartialResult())
        return data.get('partial','')
    def finish(self) -> str:
        data = json.loads(self.rec.FinalResult())
        return data.get('text','')

class VoskBackend(STTBackend):
    features = BackendFeatures(true_streaming=True, pseudo_streaming=False)
    def __init__(self, root: Path):
        self.root = root
        self.model = None
    def load(self) -> None:
        try:
            import vosk
        except ImportError as exc:
            raise ModelUnavailable('Install pip install -e .[vosk]') from exc
        if not self.root.is_dir() or not any(self.root.iterdir()):
            raise ModelUnavailable(f'Missing Vosk model: {self.root}')
        self.model = vosk.Model(str(self.root))
    def transcribe(self, audio: np.ndarray, sample_rate: int) -> Recognition:
        stream = self.open_stream(sample_rate)
        stream.accept(audio)
        return Recognition(stream.finish())
    def open_stream(self, sample_rate: int) -> Stream:
        return VoskStream(self.model, sample_rate)
