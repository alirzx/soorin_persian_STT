"""Browser origin validation for both HTTP and WebSocket.
Network ACLs and service API keys are distinct from browser-origin validation.
"""
from urllib.parse import urlsplit

def origin_allowed(origin: str | None, host: str | None, allowed_dev_origins: list[str]) -> bool:
    if not origin:
        return True
    if origin in allowed_dev_origins:
        return True
    try:
        source = urlsplit(origin)
        target = urlsplit("//" + (host or ""))
        expected_port = 443 if source.scheme == "https" else 80
        source_port = source.port or expected_port
        target_port = target.port or expected_port
        return (
            source.scheme in {"http", "https"}
            and bool(source.hostname)
            and bool(target.hostname)
            and source.username is None
            and source.password is None
            and source.path in {"", "/"}
            and not source.query and not source.fragment
            and source.hostname == target.hostname
            and source_port == target_port
        )
    except ValueError:
        return False
