import os
from pathlib import Path
import pytest
from soorin_stt.core.config import Settings
from soorin_stt.backends.base import STTBackend,Recognition,BackendFeatures,Stream
import numpy as np

class FakeStream(Stream):
    def __init__(self): self.n=0
    def accept(self,samples): self.n+=len(samples);return 'صدای آزمایش' if self.n>1000 else ''
    def finish(self):return 'سلام دنیا'

class FakeBackend(STTBackend):
    features=BackendFeatures(true_streaming=True,pseudo_streaming=False)
    def load(self):pass
    def warmup(self):pass
    def transcribe(self,audio,sample_rate):return Recognition('سلام دنيا')
    def open_stream(self,sample_rate):return FakeStream()

@pytest.fixture
def fake_app(monkeypatch,tmp_path):
    import soorin_stt.core.lifecycle as lifecycle
    from soorin_stt.main import create_app
    from soorin_stt.backends.registry import ModelSpec
    spec=ModelSpec(name='fake',backend='test',repo='fake/fake',revision='test',license='MIT',artifacts={},allow_patterns=[])
    monkeypatch.setattr(lifecycle,'resolve',lambda settings:spec)
    monkeypatch.setattr(lifecycle,'build_backend',lambda settings,spec:FakeBackend())
    monkeypatch.setattr('soorin_stt.models_cli.verify',lambda name: {})
    settings=Settings(stt_model='fake',stt_catalog_dir=tmp_path,stt_model_dir=tmp_path,
                      stt_require_model_pin=False,stt_warmup=False)
    return create_app(settings)
