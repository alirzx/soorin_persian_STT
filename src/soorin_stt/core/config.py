from __future__ import annotations
from functools import lru_cache
from pathlib import Path
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8080
    app_api_key: str = ""
    app_cors_origins: str = "http://localhost:5173"
    app_max_upload_mb: int = Field(default=30, ge=1, le=1000)
    app_inference_concurrency: int = Field(default=2, ge=1, le=32)
    app_request_timeout_seconds: int = Field(default=120, ge=1)
    app_slot_wait_seconds: float = Field(default=10, ge=0.1, le=120)
    stt_model: str = "shenava-koochik"
    stt_backend: str = ""
    stt_model_id: str = ""
    stt_model_revision: str = ""
    stt_model_dir: Path = Path("./models/downloads")
    stt_catalog_dir: Path = Path("./configs/models")
    stt_device: str = "cpu"
    stt_compute_type: str = "auto"
    stt_cpu_threads: int = Field(default=4, ge=1, le=128)
    stt_offline: bool = True
    stt_require_model_pin: bool = True
    stt_verify_hashes: bool = True
    stt_warmup: bool = True
    stt_allow_noncommercial: bool = False
    stt_external_base_url: str = ""
    audio_sample_rate: int = 16000
    audio_channels: int = 1
    audio_max_seconds: int = Field(default=600, ge=1, le=3600)
    stream_max_sessions: int = Field(default=4, ge=1, le=1000)
    stream_queue_max_frames: int = Field(default=64, ge=2, le=1024)
    stream_max_frame_bytes: int = Field(default=65536, ge=1024, le=1048576)
    stream_partial_interval_ms: int = Field(default=300, ge=100)
    stream_window_max_seconds: float = Field(default=8.0, ge=2, le=30)
    stream_partial_min_audio_seconds: float = Field(default=1.2, ge=0.2, le=10)
    stream_partial_max_queued_frames: int = Field(default=8, ge=0, le=1024)
    stream_partial_decode_interval_seconds: float = Field(default=3.0, ge=0.5, le=30)
    stream_max_seconds: int = Field(default=600, ge=1)
    stream_idle_timeout_seconds: int = Field(default=60, ge=5)
    vad_enabled: bool = True
    vad_min_speech_ms: int = 180
    vad_min_silence_ms: int = 550
    vad_rms_threshold: float = Field(default=0.006, ge=0, le=1)
    text_normalize: bool = True
    text_itn: bool = False
    text_domain: str = "general"
    log_level: str = "INFO"
    log_audio: bool = False
    metrics_enabled: bool = True

    @field_validator('stt_device')
    @classmethod
    def device_supported(cls, value: str) -> str:
        if value not in {'cpu', 'cuda'}:
            raise ValueError('STT_DEVICE must be cpu or cuda')
        return value

    @model_validator(mode='after')
    def guard_production(self):
        if self.app_env == 'production' and not self.app_api_key:
            raise ValueError('APP_API_KEY is required in production')
        if self.audio_sample_rate != 16000 or self.audio_channels != 1:
            raise ValueError('Model pipeline currently supports mono 16000Hz input')
        return self

    @property
    def allowed_origins(self) -> list[str]:
        return [x.strip() for x in self.app_cors_origins.split(',') if x.strip()]

@lru_cache
def get_settings() -> Settings:
    return Settings()
