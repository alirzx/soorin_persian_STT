from __future__ import annotations
from io import BytesIO
import numpy as np
import soundfile as sf
from soorin_stt.audio.resampler import resample
from soorin_stt.core.exceptions import InvalidAudio

def decode_audio(data: bytes, sample_rate: int = 16000, max_seconds: int = 600) -> np.ndarray:
    if not data:
        raise InvalidAudio('Empty audio payload')
    try:
        with sf.SoundFile(BytesIO(data)) as reader:
            src_rate = reader.samplerate
            if reader.frames / src_rate > max_seconds:
                raise InvalidAudio(f'Audio exceeds maximum length {max_seconds}s')
            frames = reader.read(dtype='float32', always_2d=True)
    except InvalidAudio:
        raise
    except Exception as exc:
        raise InvalidAudio(f'Audio decoder rejected input: {exc}') from exc
    if not len(frames):
        raise InvalidAudio('Audio has no samples')
    if not np.isfinite(frames).all():
        raise InvalidAudio('Audio contains non-finite samples')
    mono = np.mean(frames, axis=1).astype(np.float32)
    if src_rate != sample_rate:
        mono = resample(mono,src_rate,sample_rate)
    return mono
