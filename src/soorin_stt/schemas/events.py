from pydantic import BaseModel
class TranscriptEvent(BaseModel):
    type:str
    sequence:int
    text:str
    normalized_text:str|None=None
    start_ms:int|None=None
    end_ms:int|None=None
