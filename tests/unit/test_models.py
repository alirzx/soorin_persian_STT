from pathlib import Path
import pytest
from soorin_stt.backends.registry import catalog,resolve
from soorin_stt.core.config import Settings
from soorin_stt.core.exceptions import ConfigurationError

def test_catalog_has_multiple_families():
    registry=catalog(Path('configs/models'))
    assert len(registry)>=20
    assert registry['shenava-koochik'].backend=='sherpa_offline_ctc'
    assert registry['shenava-koochik-tract-int4'].backend=='external_http'
    assert registry['taraneh-q06b'].backend=='qwen_asr'

def test_config_driven_switch():
    s=Settings(stt_model='shenava-rizeh',stt_catalog_dir=Path('configs/models'))
    assert resolve(s).name=='shenava-rizeh'

def test_mismatch_fails_closed():
    s=Settings(stt_model='shenava-koochik',stt_backend='faster_whisper',stt_catalog_dir=Path('configs/models'))
    with pytest.raises(ConfigurationError):resolve(s)


def test_noncommercial_gate():
    from soorin_stt.backends.registry import build_backend
    registry=catalog(Path('configs/models'))
    settings=Settings(stt_model='shenava-koochik-stream-int8',stt_allow_noncommercial=False)
    with pytest.raises(ConfigurationError):build_backend(settings,registry[settings.stt_model])
