"""Static deployment contracts; no Docker daemon or model download required."""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_docker_build_context_excludes_secrets_and_weights():
    ignored = (ROOT / ".dockerignore").read_text().splitlines()
    required = {".env", ".git", ".venv", "models/downloads", "ui/node_modules", "ui/dist"}
    assert required.issubset(set(ignored))


def test_compose_protects_host_ports_and_shares_network():
    compose = yaml.safe_load((ROOT / "deploy/compose.yaml").read_text())
    api = compose["services"]["stt-api"]
    studio = compose["services"]["stt-ui"]
    assert api["ports"][0].startswith("${STT_BIND_HOST:-127.0.0.1}:")
    assert studio["ports"][0] == "${UI_BIND_HOST:-127.0.0.1}:${UI_PORT:-3015}:80"
    assert "studio" in studio["profiles"]
    assert studio["depends_on"]["stt-api"]["condition"] == "service_healthy"
    assert "soorin-ai" in api["networks"]
    assert compose["networks"]["soorin-ai"]["external"] is True
    assert api["read_only"] is True
    assert api["volumes"][0].endswith(":ro")


def test_kubernetes_read_only_container_has_writable_temp():
    deployment = yaml.safe_load((ROOT / "deploy/kubernetes/deployment.yaml").read_text())
    container = deployment["spec"]["template"]["spec"]["containers"][0]
    assert container["securityContext"]["readOnlyRootFilesystem"]
    assert any(volume["mountPath"] == "/tmp" for volume in container["volumeMounts"])

def test_https_gateway_defaults_match_preflight_and_preserve_loopback():
    compose = yaml.safe_load((ROOT / "deploy/compose.yaml").read_text())
    gateway = compose["services"]["stt-https"]
    assert "secure" in gateway["profiles"]
    assert gateway["environment"]["STT_TLS_MODE"] == "${STT_TLS_MODE:-internal}"
    assert gateway["environment"]["STT_AUTH_MODE"] == "${STT_AUTH_MODE:-none}"
    assert gateway["ports"][0].startswith("${STT_HTTPS_BIND_HOST:-127.0.0.1}:")
    assert "/certs:ro" in gateway["volumes"][1]


def test_caddy_binary_file_capability_is_in_bounding_set():
    compose = yaml.safe_load((ROOT / "deploy/compose.yaml").read_text())
    gateway = compose["services"]["stt-https"]
    assert gateway["cap_drop"] == ["ALL"]
    assert gateway["cap_add"] == ["NET_BIND_SERVICE"]
    assert gateway["security_opt"] == ["no-new-privileges:true"]


def test_ip_https_default_sni_is_explicit_for_docker_nat():
    config = (ROOT / "deploy/caddy/Caddyfile.internal").read_text()
    assert "default_sni {$STT_HTTPS_HOST}" in config
    assert "tls internal" in config
