from collections import deque
import numpy as np
class AudioBuffer:
    def __init__(self,max_samples:int):
        self.data: deque[np.ndarray] = deque()
        self.max_samples=max_samples
        self.n=0
    def append(self,samples:np.ndarray):
        if self.n+len(samples)>self.max_samples:
            raise OverflowError('stream duration exceeded')
        self.data.append(samples.copy()); self.n+=len(samples)
    def join(self)->np.ndarray:
        return np.concatenate(list(self.data)) if self.data else np.zeros(0,dtype=np.float32)
    def clear(self):
        self.data.clear();self.n=0
