from pathlib import Path
from fastapi.testclient import TestClient
from soorin_stt.core.config import Settings
from soorin_stt.main import create_app

def test_missing_model_stays_unready(tmp_path):
    settings=Settings(stt_catalog_dir=Path('configs/models'),stt_model_dir=tmp_path,
                      stt_model='shenava-koochik',stt_warmup=True)
    with TestClient(create_app(settings)) as client:
        assert client.get('/health/live').status_code==200
        assert client.get('/health/ready').status_code==503
        assert client.get('/v1/models/current').json()['ready'] is False
