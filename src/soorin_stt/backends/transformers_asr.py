from pathlib import Path
import numpy as np
from soorin_stt.backends.base import BackendFeatures, STTBackend, Recognition
from soorin_stt.core.exceptions import ModelUnavailable

class TransformersASRBackend(STTBackend):
    features = BackendFeatures(true_streaming=False, pseudo_streaming=True)
    def __init__(self, root: Path, device: str):
        self.root,self.device = root,device
        self.pipe = None
    def load(self) -> None:
        try:
            from transformers import pipeline
        except ImportError as exc:
            raise ModelUnavailable('Install pip install -e .[transformers]') from exc
        # Model code is deliberately never loaded with trust_remote_code=True.
        if not (self.root / 'config.json').is_file():
            raise ModelUnavailable(f'Missing Transformers config: {self.root}')
        self.pipe = pipeline('automatic-speech-recognition', model=str(self.root),
                             device=0 if self.device=='cuda' else -1, trust_remote_code=False)
    def transcribe(self, audio: np.ndarray, sample_rate: int) -> Recognition:
        result = self.pipe({'raw': audio, 'sampling_rate': sample_rate})
        return Recognition(str(result.get('text','')).strip())
