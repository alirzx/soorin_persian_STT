from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import yaml
from soorin_stt.core.config import Settings
from soorin_stt.core.exceptions import ConfigurationError, ModelUnavailable

@dataclass(frozen=True)
class ModelSpec:
    name: str
    backend: str
    repo: str
    revision: str
    license: str
    artifacts: dict
    allow_patterns: list[str]
    description: str = ''
    streaming: str = 'none'
    status: str = 'supported'

    @classmethod
    def from_yaml(cls, path: Path) -> 'ModelSpec':
        data = yaml.safe_load(path.read_text(encoding='utf-8'))
        if not isinstance(data, dict):
            raise ConfigurationError(f'Invalid model entry {path}')
        return cls(name=data['name'], backend=data['backend'], repo=data.get('repo',''),
                   revision=str(data.get('revision') or ''), license=data.get('license','unknown'),
                   artifacts=data.get('artifacts',{}),allow_patterns=data.get('allow_patterns',[]),
                   description=data.get('description',''),streaming=data.get('streaming','none'),
                   status=data.get('status','supported'))

def catalog(catalog_dir: Path) -> dict[str, ModelSpec]:
    return {p.stem:ModelSpec.from_yaml(p) for p in sorted(catalog_dir.glob('*.yaml'))}

def resolve(settings: Settings) -> ModelSpec:
    registry = catalog(settings.stt_catalog_dir)
    if settings.stt_model not in registry:
        raise ConfigurationError(f'Unknown STT_MODEL={settings.stt_model}. Choose {list(registry)}')
    spec = registry[settings.stt_model]
    # Override model and revision only by explicit opt-in, never accidentally mixing mismatched artifacts.
    if settings.stt_model_id and settings.stt_model_id != spec.repo:
        raise ConfigurationError('STT_MODEL_ID conflicts with selected catalog entry. Add a new model YAML instead.')
    if settings.stt_backend and settings.stt_backend != spec.backend:
        raise ConfigurationError('STT_BACKEND conflicts with catalog. Select another STT_MODEL.')
    return spec

def local_dir(settings: Settings) -> Path:
    return settings.stt_model_dir / settings.stt_model

def build_backend(settings: Settings, spec: ModelSpec):
    from soorin_stt.backends.sherpa import SherpaCTCBackend, SherpaTransducerBackend
    from soorin_stt.backends.whisper import WhisperBackend
    from soorin_stt.backends.vosk import VoskBackend
    from soorin_stt.backends.transformers_asr import TransformersASRBackend
    from soorin_stt.backends.external import ExternalHTTPBackend
    from soorin_stt.backends.qwen import QwenASRBackend
    if settings.app_env == 'production' and spec.license.lower() in {'unknown', 'noncommercial', 'cc-by-nc', 'cc-by-nc-4.0'}:
        raise ConfigurationError(f'{spec.name} license has not passed production review')
    if spec.license.lower() in {'cc-by-nc-4.0','cc-by-nc','noncommercial'} and not settings.stt_allow_noncommercial:
        raise ConfigurationError(f'{spec.name} is marked noncommercial. Not enabled for Soorin production.')
    if spec.status == 'research-only':
        raise ConfigurationError(f'{spec.name} is research-only and has no verified runtime adapter')
    root=local_dir(settings)
    backend=spec.backend
    if backend=='sherpa_offline_ctc':
        return SherpaCTCBackend(root,settings.stt_cpu_threads,False,settings.stt_device,spec.artifacts.get('model','model.onnx'))
    if backend=='sherpa_online_ctc':
        return SherpaCTCBackend(root,settings.stt_cpu_threads,True,settings.stt_device,spec.artifacts.get('model','model.onnx'))
    if backend=='sherpa_online_transducer':
        return SherpaTransducerBackend(root,settings.stt_cpu_threads,settings.stt_device,spec.artifacts)
    if backend=='faster_whisper':
        return WhisperBackend(root,settings.stt_cpu_threads,
                              'int8' if settings.stt_compute_type == 'auto' else settings.stt_compute_type,settings.stt_device)
    if backend=='qwen_asr':
        return QwenASRBackend(root,settings.stt_device)
    if backend=='vosk':
        return VoskBackend(root)
    if backend=='transformers_asr':
        return TransformersASRBackend(root,settings.stt_device)
    if backend=='external_http':
        return ExternalHTTPBackend(settings.stt_external_base_url,settings.app_request_timeout_seconds)
    raise ConfigurationError(f'Unsupported backend={backend}')
