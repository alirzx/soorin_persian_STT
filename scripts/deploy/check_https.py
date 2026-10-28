#!/usr/bin/env python3
"""Check HTTPS LAN/VPN deployment settings. Never print credential values."""
from __future__ import annotations
import ipaddress
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
def fail(message: str) -> None:
    sys.exit(f"HTTPS preflight failed: {message}")

def read_env(path: Path) -> dict[str, str]:
    if not path.is_file():
        fail(".env missing")
    values = {}
    for row in path.read_text(encoding="utf-8").splitlines():
        if "=" not in row or row.lstrip().startswith("#"):
            continue
        key, value = row.split("=", 1)
        values[key.strip()] = value.strip().strip("'").strip('"')
    return values

def validate(values: dict[str, str], root: Path = ROOT) -> None:
    host = values.get("STT_HTTPS_HOST", "").strip()
    bind = values.get("STT_HTTPS_BIND_HOST", "").strip()
    tls = values.get("STT_TLS_MODE", "internal")
    auth = values.get("STT_AUTH_MODE", "none")
    if not host or host in {"0.0.0.0", "::", "*"}:
        fail("STT_HTTPS_HOST must be the URL hostname or LAN IP, not a wildcard")
    if "://" in host or "/" in host or ":" in host or not re.fullmatch(r"[A-Za-z0-9_.-]+", host):
        fail("STT_HTTPS_HOST must be a bare DNS hostname or IPv4 address")
    if not bind or bind in {"0.0.0.0", "::"}:
        fail("STT_HTTPS_BIND_HOST must be a specific trusted host interface")
    try:
        ipaddress.ip_address(bind)
    except ValueError:
        fail("STT_HTTPS_BIND_HOST must be a specific interface IP")
    if values.get("UI_BIND_HOST", "127.0.0.1") not in {"127.0.0.1", "localhost"}:
        fail("UI_BIND_HOST must remain loopback to prevent bypass of the HTTPS gateway")
    if values.get("STT_BIND_HOST", "127.0.0.1") not in {"127.0.0.1", "localhost"}:
        fail("STT_BIND_HOST must remain loopback")
    if tls not in {"internal", "internal-public", "files"}:
        fail("STT_TLS_MODE must be internal, internal-public or files")
    if auth not in {"none", "basic"}:
        fail("STT_AUTH_MODE must be none or basic")
    try:
        port_text = values.get("STT_HTTPS_PORT", "3443")
        if not port_text.isdigit():
            raise ValueError("not an integer")
        port = int(port_text)
        if not 1 <= port <= 65535:
            raise ValueError("out of range")
        api_port = int(values.get("APP_PORT", "8080"))
        ui_port = int(values.get("UI_PORT", "3015"))
    except (ValueError, TypeError):
        fail("STT_HTTPS_PORT, APP_PORT and UI_PORT must be valid TCP port numbers")
    if port in {api_port, ui_port}:
        fail("STT_HTTPS_PORT cannot equal the published API or HTTP UI port")
    if auth == "basic":
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", values.get("STT_HTTPS_USER", "")):
            fail("STT_HTTPS_USER is invalid")
        if not re.fullmatch(r"\$2[aby]\$\d\d\$[./A-Za-z0-9]{53}", values.get("STT_HTTPS_PASSWORD_HASH", "")):
            fail("STT_HTTPS_PASSWORD_HASH requires a bcrypt hash")
    if tls == "internal-public":
        public_host = values.get("STT_PUBLIC_HTTPS_HOST", "").strip()
        if not public_host or public_host == host or public_host in {"0.0.0.0", "::", "*"}:
            fail("internal-public needs a distinct STT_PUBLIC_HTTPS_HOST")
        if ("://" in public_host or "/" in public_host or ":" in public_host
                or not re.fullmatch(r"[A-Za-z0-9_.-]+", public_host)):
            fail("STT_PUBLIC_HTTPS_HOST must be an IP or DNS name without port/scheme")
        if auth != "basic":
            fail("internal-public requires STT_AUTH_MODE=basic on both hostnames")
    if tls == "files":
        source = Path(values.get("STT_TLS_CERT_DIR", "../certs"))
        certs = (root / "deploy" / source).resolve() if not source.is_absolute() else source
        for name in ("fullchain.pem", "privkey.pem"):
            if not (certs / name).is_file():
                fail(f"Missing TLS certificate file: {certs / name}")
    if values.get("APP_ENV") == "production" and not values.get("APP_API_KEY"):
        fail("APP_API_KEY is required in production; configure a browser-safe trusted gateway")

if __name__ == "__main__":
    validate(read_env(ROOT / ".env"))
    print("HTTPS preflight passed. Browser certificate trust and VPN/firewall ACLs still required.")
