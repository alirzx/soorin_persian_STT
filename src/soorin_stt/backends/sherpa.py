from __future__ import annotations
import numpy as np
from pathlib import Path
from soorin_stt.backends.base import BackendFeatures, Recognition, STTBackend, Stream
from soorin_stt.core.exceptions import ModelUnavailable, UnsupportedRuntime

class SherpaStream(Stream):
    def __init__(self, recognizer, sample_rate: int, language: str = ""):
        self.language = language
        self.recognizer = recognizer
        self.sample_rate = sample_rate
        self.stream = recognizer.create_stream()
        if self.language:
            self.stream.set_option("language", self.language)
        self.last = ''
    def accept(self, samples: np.ndarray) -> str:
        self.stream.accept_waveform(self.sample_rate, np.ascontiguousarray(samples, dtype=np.float32))
        while self.recognizer.is_ready(self.stream):
            self.recognizer.decode_stream(self.stream)
        result = self.recognizer.get_result(self.stream)
        self.last = result.text if hasattr(result, 'text') else str(result)
        return self.last
    def finish(self) -> str:
        self.stream.accept_waveform(self.sample_rate, np.zeros(int(self.sample_rate * 0.35), dtype=np.float32))
        self.stream.input_finished()
        while self.recognizer.is_ready(self.stream):
            self.recognizer.decode_stream(self.stream)
        result = self.recognizer.get_result(self.stream)
        self.last = result.text if hasattr(result, 'text') else str(result)
        return self.last

class SherpaCTCBackend(STTBackend):
    def __init__(self, artifact_dir: Path, threads: int, online: bool, device: str, filename: str = 'model.onnx'):
        self.root, self.threads, self.online, self.device = artifact_dir, threads, online, device
        self.filename = filename
        self.recognizer = None
        self.features = BackendFeatures(true_streaming=online, pseudo_streaming=not online, device=device)
    def load(self) -> None:
        try:
            import sherpa_onnx
        except ImportError as exc:
            raise ModelUnavailable('Install optional inference dependency: pip install -e .[sherpa]') from exc
        model, tokens = self.root / self.filename, self.root / 'tokens.txt'
        if not model.is_file() or not tokens.is_file():
            raise ModelUnavailable(f'Missing sherpa model files at {self.root}: {model.name}, tokens.txt')
        if self.online:
            self.recognizer = sherpa_onnx.OnlineRecognizer.from_nemo_ctc(
                tokens=str(tokens), model=str(model), num_threads=self.threads, provider=self.device,
                sample_rate=16000, feature_dim=80, enable_endpoint_detection=False)
        else:
            self.recognizer = sherpa_onnx.OfflineRecognizer.from_nemo_ctc(
                model=str(model), tokens=str(tokens), num_threads=self.threads, provider=self.device)
    def transcribe(self, audio: np.ndarray, sample_rate: int) -> Recognition:
        if self.recognizer is None:
            raise ModelUnavailable('Recognizer was not loaded')
        if self.online:
            stream = self.open_stream(sample_rate)
            # Split offline waveform to exercise the actual cache-aware streaming path.
            for offset in range(0, len(audio), 3200):
                stream.accept(audio[offset:offset + 3200])
            return Recognition(stream.finish())
        stream = self.recognizer.create_stream()
        stream.accept_waveform(sample_rate, np.ascontiguousarray(audio, dtype=np.float32))
        self.recognizer.decode_stream(stream)
        return Recognition(stream.result.text)
    def open_stream(self, sample_rate: int) -> Stream:
        if self.online:
            return SherpaStream(self.recognizer, sample_rate)
        return super().open_stream(sample_rate)

class SherpaTransducerBackend(STTBackend):
    features = BackendFeatures(true_streaming=True, pseudo_streaming=False)
    def __init__(self, root: Path, threads: int, device: str, artifacts: dict):
        self.root, self.threads, self.device, self.artifacts = root, threads, device, artifacts
        self.recognizer = None
    def load(self) -> None:
        try:
            import sherpa_onnx
        except ImportError as exc:
            raise ModelUnavailable('Install pip install -e .[sherpa]') from exc
        names = {k: str(self.root / self.artifacts.get(k, k + '.onnx')) for k in ('encoder','decoder','joiner','tokens')}
        for path in names.values():
            if not Path(path).is_file():
                raise ModelUnavailable(f'Missing transducer artifact: {path}')
        self.recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(**names,
                            num_threads=self.threads, provider=self.device, sample_rate=16000, feature_dim=128)
    def transcribe(self, audio: np.ndarray, sample_rate: int) -> Recognition:
        stream = self.open_stream(sample_rate)
        for i in range(0,len(audio),3200):
            stream.accept(audio[i:i+3200])
        return Recognition(stream.finish())
    def open_stream(self, sample_rate: int) -> Stream:
        return SherpaStream(self.recognizer, sample_rate, language="fa-IR")
