import numpy as np
from soorin_stt.core.exceptions import InvalidAudio

def pcm_s16le_to_float(payload: bytes) -> np.ndarray:
    if len(payload) < 2 or len(payload) % 2:
        raise InvalidAudio('PCM frame must contain an even, nonzero number of bytes')
    return np.frombuffer(payload, dtype='<i2').astype(np.float32) / 32768.0

def float_to_pcm_s16le(samples: np.ndarray) -> bytes:
    return (np.clip(samples,-1,1)*32767).astype('<i2').tobytes()
