from pydantic import BaseModel, Field
class Segment(BaseModel):
    start_ms:int
    end_ms:int
    text:str
class Entity(BaseModel):
    type:str
    raw:str
    normalized:str
    start:int
    end:int
class TranscriptResponse(BaseModel):
    request_id:str
    model:str
    language:str='fa'
    text:str
    normalized_text:str
    duration_ms:int
    processing_ms:int
    rtf:float
    segments:list[Segment]=Field(default_factory=list)
    entities:list[Entity]=Field(default_factory=list)
    streaming_mode:str
