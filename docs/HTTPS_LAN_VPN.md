# Secure LAN/VPN microphone access (Server 62)

## Why the microphone failed

Browser `navigator.mediaDevices.getUserMedia` is **undefined on ordinary HTTP IP origins**
such as `http://192.168.0.62:3015`. File upload can succeed, but live microphone
cannot. Changing React code or adding more Docker bridge networks cannot bypass the
browser security policy.

Use an HTTPS origin with a **browser-trusted certificate** (or use localhost for
individual SSH-tunnel testing). The optional `secure` Compose profile adds **Caddy
with an internal certificate authority**, HTTP Basic Auth and persistent cert storage,
without modifying the offline STT model or the existing containers of other projects.

Architecture: **LAN/VPN browser -> HTTPS :3443 -> Caddy (TLS/auth) -> Nginx UI :80 ->
FastAPI :8080**. This uses secure `wss://` on the same HTTPS origin. All three STT
containers share only the dedicated external Docker bridge `soorin-ai`.
The original `studio` profile remains available for localhost development.

## Server 62 setup

Only touch `/srv/soorin-stt`. Do not run Docker prune, stop Copilot or edit other
Compose projects. In `/srv/soorin-stt`, after `git pull --ff-only origin main`:

```bash
cd /srv/soorin-stt
cp -p .env ".env.backup.$(date +%Y%m%d-%H%M%S)"
# Set these in .env, preserving all audio/model values:
# UI_BIND_HOST=127.0.0.1
# STT_BIND_HOST=127.0.0.1
# STT_HTTPS_HOST=192.168.0.62
# STT_HTTPS_BIND_HOST=192.168.0.62
# STT_HTTPS_PORT=3443
# STT_HTTPS_USER=stt

# Generate an auth hash without putting the plaintext in shell history:
read -rsp 'Studio HTTPS password: ' STT_PW; echo
HASH="$(printf '%s\n' "$STT_PW" | sudo docker run --rm -i caddy:2.10-alpine caddy hash-password --algorithm bcrypt)"
unset STT_PW
# Copy the printed hash into .env as STT_HTTPS_PASSWORD_HASH='<bcrypt hash>'
# The single quotes are important: Compose must not interpolate bcrypt's dollar signs.
# Do not commit .env or publish the hash.

python3 scripts/deploy/check_https.py
sudo docker compose --env-file .env -f deploy/compose.yaml --profile studio --profile secure config --quiet
sudo docker compose --env-file .env -f deploy/compose.yaml --profile studio --profile secure up -d --no-build
sudo docker compose --env-file .env -f deploy/compose.yaml --profile studio --profile secure ps
```

Caddy is pulled from Docker Hub; the local STT API/UI images do **not** need rebuilding
unless the React microphone warning changed. Only the STT UI needs recreation for the
HTTP host binding change. `up -d` will reconcile only the STT Compose project;
the 438 MB model remains on the same read-only host mount and is not downloaded.

Secure URL: **https://192.168.0.62:3443/**

## Distribute and trust the internal CA

The root certificate is in the **persistent** volume `stt_https_data`; keep this
volume across redeploys and backups. Never use `down -v` or rotate the CA
unintentionally. Export only the *public root certificate*; never copy private CA
keys to client machines:

```bash
CID="$(sudo docker compose --env-file .env -f deploy/compose.yaml --profile secure ps -q stt-https)"
sudo docker cp "$CID:/data/caddy/pki/authorities/local/root.crt" /tmp/soorin-stt-root-ca.crt
openssl x509 -in /tmp/soorin-stt-root-ca.crt -noout -fingerprint -sha256
```

Distribute the root certificate to authorized devices by your organization's secure
device-management channel. Verify the **SHA-256 fingerprint out of band**. Install it
as a trusted CA on each authorized device/browser (Firefox may use its own certificate
store). This grants broad trust to a CA: organizational approval and safe private-key
management are required. Simply clicking through an untrusted certificate warning is
not a reliable way to enable microphone capture.

Once trust is installed, open the secure URL, authenticate when prompted, allow
microphone permission, then test REST, upload and the live WebSocket. The browser
should report `window.isSecureContext === true`, a defined
`navigator.mediaDevices?.getUserMedia`, and a successful `wss://` handshake.

For a larger organization, **prefer a real internal DNS name with a certificate
trusted by managed clients, or a publicly-trusted organizational domain with
managed HTTPS/SSO ingress**, rather than distributing an ad-hoc CA.

## Smoke tests and security checks

```bash
# Host-side service status. No rebuild necessary unless React image changed.
sudo docker compose --env-file .env -f deploy/compose.yaml --profile studio --profile secure ps
curl -fsS http://127.0.0.1:8080/health/ready
# HTTPS must require credentials (expect HTTP 401 without auth):
curl -sk -o /dev/null -w '%{http_code}\n' https://192.168.0.62:3443/
# After exporting root CA, verify server TLS chain. No -k:
curl --cacert /tmp/soorin-stt-root-ca.crt -o /dev/null -w '%{http_code}\n' https://192.168.0.62:3443/
# Expect 401 without credentials; use the browser to authenticate and test.
sudo ss -ltnp | grep -E ':(3015|3443|8080)\\b'
```

Expected bindings: `127.0.0.1:3015` (HTTP UI, **not** LAN),
`127.0.0.1:8080` (API, **not** LAN), and
`192.168.0.62:3443` (HTTPS only). No container in another Compose project is
restarted or reconfigured. Confirm VPN routing and firewall policy restrict 3443
to intended users. Publishing Docker ports can bypass ordinary UFW expectations.

**Authentication limitation:** This is a trusted-internal v1 gateway with a shared
Basic Auth credential. Test authenticated WebSocket handshakes across Firefox and
Chrome before general rollout. Production/SSO requires identity-aware per-user auth,
access controls and audit, plus independently reviewed security settings.
The existing FastAPI API-key mechanism cannot simply be enabled for browser use
without a browser-safe server-side credential strategy.
