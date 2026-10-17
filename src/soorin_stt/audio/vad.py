import numpy as np

def has_speech(samples: np.ndarray, threshold: float = 0.006) -> bool:
    if not len(samples):
        return False
    # Energy-gate for endpoint UI, NOT a speech classifier; real ASR always receives all audio.
    return float(np.sqrt(np.mean(samples.astype(np.float64)**2))) >= threshold
