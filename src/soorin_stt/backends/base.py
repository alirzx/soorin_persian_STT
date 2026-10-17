from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import numpy as np

@dataclass(frozen=True)
class BackendFeatures:
    true_streaming: bool = False
    pseudo_streaming: bool = True
    timestamps: bool = False
    device: str = "cpu"

@dataclass
class Recognition:
    text: str
    segments: list[dict] = field(default_factory=list)

class Stream(ABC):
    @abstractmethod
    def accept(self, samples: np.ndarray) -> str: ...
    @abstractmethod
    def finish(self) -> str: ...
    def close(self) -> None: pass

class STTBackend(ABC):
    features: BackendFeatures = BackendFeatures()
    @abstractmethod
    def load(self) -> None: ...
    @abstractmethod
    def transcribe(self, audio: np.ndarray, sample_rate: int) -> Recognition: ...
    def warmup(self) -> None:
        # Warm-up does real inference to catch mismatched artifact/runtime before readiness.
        self.transcribe(np.zeros(16000, dtype=np.float32), 16000)
    def open_stream(self, sample_rate: int) -> Stream:
        return BufferedStream(self, sample_rate)
    def close(self) -> None: pass

class BufferedStream(Stream):
    """Explicit pseudo-streaming fallback for batch-only models, bounded by WS session caps."""
    def __init__(self, backend: STTBackend, sample_rate: int):
        self.backend = backend
        self.sample_rate = sample_rate
        self.frames: list[np.ndarray] = []
        self.length = 0
        self.last_text = ''
    def accept(self, samples: np.ndarray) -> str:
        self.frames.append(samples.copy())
        self.length += len(samples)
        # Do not repeatedly decode each tiny frame. WS session requests a partial on explicit interval.
        return self.last_text
    def partial(self) -> str:
        if self.length < int(self.sample_rate * 0.6):
            return self.last_text
        audio = np.concatenate(self.frames)
        self.last_text = self.backend.transcribe(audio, self.sample_rate).text
        return self.last_text
    def finish(self) -> str:
        if not self.frames:
            return ''
        self.last_text = self.backend.transcribe(np.concatenate(self.frames), self.sample_rate).text
        return self.last_text
    def close(self) -> None:
        self.frames.clear()
        self.length = 0
