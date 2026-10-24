"""Offline HTTPS deployment validation cases."""
import importlib.util
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("check_https", ROOT / "scripts/deploy/check_https.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def config(**overrides):
    values = dict(STT_HTTPS_HOST="192.168.0.62",STT_HTTPS_BIND_HOST="192.168.0.62",STT_TLS_MODE="internal",STT_AUTH_MODE="none",UI_BIND_HOST="127.0.0.1",STT_BIND_HOST="127.0.0.1")
    return values | overrides

def test_password_free_internal_https():
    module.validate(config())

def test_hostname_can_differ_from_bind_address():
    module.validate(config(STT_HTTPS_HOST="stt.example.com",STT_TLS_MODE="internal"))

@pytest.mark.parametrize("values",[
    {"STT_HTTPS_BIND_HOST":"0.0.0.0"},
    {"UI_BIND_HOST":"192.168.0.62"},
    {"STT_BIND_HOST":"0.0.0.0"},
    {"STT_TLS_MODE":"unknown"},
    {"STT_AUTH_MODE":"basic"},
])
def test_unsafe_configuration_is_rejected(values):
    with pytest.raises(SystemExit,match="HTTPS preflight failed"):
        module.validate(config(**values))

def test_files_mode_requires_certificate_files(tmp_path):
    with pytest.raises(SystemExit,match="Missing TLS"):
        module.validate(config(STT_TLS_MODE="files",STT_TLS_CERT_DIR=str(tmp_path)))
    (tmp_path/"fullchain.pem").write_text("mock")
    (tmp_path/"privkey.pem").write_text("mock")
    module.validate(config(STT_TLS_MODE="files",STT_TLS_CERT_DIR=str(tmp_path)))

def test_origin_rules():
    from soorin_stt.core.origin import origin_allowed
    assert origin_allowed("https://stt.example.com:3443","stt.example.com:3443",[])
    assert origin_allowed("http://localhost:5173","localhost:8080",["http://localhost:5173"])
    assert not origin_allowed("https://evil.example.com","stt.example.com",[])
    assert not origin_allowed("https://stt.example.com:3443","stt.example.com:8080",[])

@pytest.mark.parametrize("value", ["0", "65536", "not-a-port", "-1"])
def test_invalid_https_port_fails(value):
    with pytest.raises(SystemExit, match="HTTPS preflight failed"):
        module.validate(config(STT_HTTPS_PORT=value))

def test_https_cannot_reuse_http_port():
    with pytest.raises(SystemExit, match="cannot equal"):
        module.validate(config(STT_HTTPS_PORT="3015"))

def test_omitted_auth_tls_keys_match_compose_defaults():
    module.validate(config(STT_TLS_MODE="internal", STT_AUTH_MODE="none"))
