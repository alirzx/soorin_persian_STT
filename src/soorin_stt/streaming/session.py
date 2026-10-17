from dataclasses import dataclass
from time import monotonic
@dataclass
class SessionState:
    sequence:int=0
    received_samples:int=0
    last_text:str=''
    started:float=0.0
    last_activity:float=0.0
    def __post_init__(self):
        self.started=monotonic()
        self.last_activity=self.started
    def touch(self,frames:int):
        self.received_samples+=frames
        self.last_activity=monotonic()
    def next_seq(self)->int:
        self.sequence+=1
        return self.sequence
