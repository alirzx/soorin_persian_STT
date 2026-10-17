"""Bounded pseudo-streaming for offline recognizers.

Recognition is performed only on the current utterance, not the entire call.
Silence hangover or a hard window duration seals each segment. The algorithm is
an RMS endpointing baseline; it is not a neural speech activity detector.
"""
from __future__ import annotations

from collections import deque
import numpy as np


class WindowedSpeech:
    def __init__(
        self, sample_rate: int, threshold: float, min_speech_ms: int,
        min_silence_ms: int, max_window_seconds: float,
    ) -> None:
        self.sample_rate = sample_rate
        self.threshold = threshold
        self.min_speech = round(sample_rate * min_speech_ms / 1000)
        self.min_silence = round(sample_rate * min_silence_ms / 1000)
        self.max_samples = round(sample_rate * max_window_seconds)
        self.frames: deque[np.ndarray] = deque()
        self.window_samples = 0
        self.speech_samples = 0
        self.silence_samples = 0
        self.committed: list[str] = []
        self.completed_windows = 0

    def push(self, samples: np.ndarray) -> bool:
        samples = np.asarray(samples, dtype=np.float32)
        if not len(samples):
            return False
        active = float(np.sqrt(np.mean(samples.astype(np.float64) ** 2))) >= self.threshold
        if not self.frames and not active:
            return False
        self.frames.append(samples.copy())
        self.window_samples += len(samples)
        if active:
            self.speech_samples += len(samples)
            self.silence_samples = 0
        else:
            self.silence_samples += len(samples)
        has_speech = self.speech_samples >= self.min_speech
        return bool(has_speech and (
            self.silence_samples >= self.min_silence
            or self.window_samples >= self.max_samples
        ))

    def window(self) -> np.ndarray:
        return np.concatenate(tuple(self.frames)) if self.frames else np.empty(0, np.float32)

    def has_speech(self) -> bool:
        return self.speech_samples >= self.min_speech

    def seal(self, text: str) -> str:
        value = text.strip()
        if value:
            self.committed.append(value)
        self.frames.clear()
        self.window_samples = self.speech_samples = self.silence_samples = 0
        self.completed_windows += 1
        return self.transcript()

    def transcript(self, hypothesis: str = "") -> str:
        return " ".join(piece for piece in [*self.committed, hypothesis.strip()] if piece)

    def buffered_seconds(self) -> float:
        return self.window_samples / self.sample_rate
