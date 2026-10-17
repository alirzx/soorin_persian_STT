from pydantic import BaseModel, Field, model_validator
class AudioConfig(BaseModel):
    format:str='pcm_s16le'
    sample_rate:int=16000
    channels:int=1
class StreamStart(BaseModel):
    type:str='session.start'
    audio:AudioConfig=Field(default_factory=AudioConfig)
    language:str='fa'
    normalize:bool=True
    domain:str='general'
    @model_validator(mode='after')
    def valid(self):
        if self.type!='session.start' or self.language!='fa':
            raise ValueError('Only session.start / language fa are supported')
        if (self.audio.format!='pcm_s16le' or self.audio.sample_rate!=16000 or self.audio.channels!=1):
            raise ValueError('Streaming requires mono pcm_s16le at 16000Hz')
        if self.domain not in {'general','soc'}:
            raise ValueError('Invalid text domain')
        return self
