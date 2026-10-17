import asyncio
from soorin_stt.core.exceptions import Overloaded

class SessionCapacity:
    def __init__(self,capacity:int):
        self.capacity=capacity
        self.active=0
        self.lock=asyncio.Lock()
    async def enter(self)->None:
        async with self.lock:
            if self.active>=self.capacity:
                raise Overloaded('Maximum concurrent streams reached')
            self.active+=1
    async def leave(self)->None:
        async with self.lock:
            self.active=max(self.active-1,0)
