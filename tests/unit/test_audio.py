from io import BytesIO
import soundfile as sf
import numpy as np
import pytest
from soorin_stt.audio.decoder import decode_audio
from soorin_stt.audio.formats import pcm_s16le_to_float
from soorin_stt.core.exceptions import InvalidAudio

def test_wav_resampling():
    buf=BytesIO();sf.write(buf,np.zeros((4410,2),dtype=np.float32),44100,format='WAV')
    audio=decode_audio(buf.getvalue(),16000)
    assert len(audio)==1600 and audio.dtype==np.float32

def test_invalid_audio():
    with pytest.raises(InvalidAudio):decode_audio(b'not a wav')

def test_pcm_input():
    assert np.allclose(pcm_s16le_to_float(b'\x00\x00\xff\x7f'),[0,32767/32768])
    with pytest.raises(InvalidAudio):pcm_s16le_to_float(b'\x00')
