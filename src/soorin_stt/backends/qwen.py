from pathlib import Path
import numpy as np
from soorin_stt.backends.base import BackendFeatures,Recognition,STTBackend
from soorin_stt.core.exceptions import ModelUnavailable

class QwenASRBackend(STTBackend):
    """Local qwen-asr SDK implementation. Research use: high RAM; pseudo-streaming only."""
    features=BackendFeatures(true_streaming=False,pseudo_streaming=True)
    def __init__(self,root:Path,device:str):
        self.root,self.device=root,device
        self.model=None
    def load(self):
        if not self.root.joinpath('config.json').exists():
            raise ModelUnavailable('Qwen model not downloaded locally')
        try:
            import torch
            from qwen_asr import Qwen3ASRModel
        except ImportError as exc:
            raise ModelUnavailable('Install pip install -e .[qwen]') from exc
        self.model=Qwen3ASRModel.from_pretrained(str(self.root),
                         dtype=torch.float16 if self.device=='cuda' else torch.float32,
                         device_map='cuda:0' if self.device=='cuda' else 'cpu',
                         max_inference_batch_size=1,max_new_tokens=256)
    def transcribe(self,audio:np.ndarray,sample_rate:int)->Recognition:
        if self.model is None:
            raise ModelUnavailable('Qwen not loaded')
        # qwen_asr accepts (samples, sample_rate), including local in-memory audio.
        results=self.model.transcribe(audio=(np.asarray(audio,dtype=np.float32),sample_rate),language='Persian')
        return Recognition(results[0].text)
