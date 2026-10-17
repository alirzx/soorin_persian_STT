import numpy as np
from scipy.signal import resample_poly
from math import gcd

def resample(audio: np.ndarray, from_hz: int, to_hz: int) -> np.ndarray:
    if from_hz == to_hz:
        return np.asarray(audio,dtype=np.float32)
    g = gcd(from_hz,to_hz)
    return np.asarray(resample_poly(audio,to_hz//g,from_hz//g),dtype=np.float32)
