import numpy as np

def chunks(samples: np.ndarray, size: int):
    if size <= 0:
        raise ValueError('size must be positive')
    for i in range(0,len(samples),size):
        yield samples[i:i+size]
