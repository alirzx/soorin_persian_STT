from io import BytesIO
import numpy as np
import soundfile as sf
from fastapi.testclient import TestClient

def test_liveness_and_batch(fake_app):
    with TestClient(fake_app) as client:
        assert client.get('/health/live').status_code==200
        assert client.get('/health/ready').status_code==200
        assert client.get('/v1/models/current').json()['streaming_mode']=='native'
        buf=BytesIO();sf.write(buf,np.zeros(16000,dtype=np.float32),16000,format='WAV')
        resp=client.post('/v1/audio/transcriptions',files={'file':('test.wav',buf.getvalue(),'audio/wav')},data={'domain':'general','normalize':'true'})
        assert resp.status_code==200,resp.text
        body=resp.json()
        assert body['text']=='سلام دنيا'
        assert body['normalized_text']=='سلام دنیا'
        assert body['duration_ms']==1000

def test_websocket(fake_app):
    with TestClient(fake_app) as client:
        with client.websocket_connect('/v1/audio/transcriptions/stream') as ws:
            ws.send_json({'type':'session.start','audio':{'format':'pcm_s16le','sample_rate':16000,'channels':1}})
            assert ws.receive_json()['type']=='session.ready'
            ws.send_bytes(b'\x00\x00'*6400)
            ws.send_json({'type':'session.end'})
            # Might have a partial event before final depending on mock timing.
            for _ in range(3):
                data=ws.receive_json()
                if data['type']=='transcript.final':
                    assert data['text']=='سلام دنیا'
                    break
            else:raise AssertionError('no final')

def test_bad_stream_start(fake_app):
    with TestClient(fake_app) as client:
        with client.websocket_connect('/v1/audio/transcriptions/stream') as ws:
            ws.send_json({'type':'session.start','audio':{'sample_rate':48000}})
            assert ws.receive_json()['type']=='session.error'
