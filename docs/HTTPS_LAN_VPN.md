# HTTPS Studio on LAN/VPN (no shared password required)

Plain IP HTTP (`http://192.168.0.62:3015`) is not a browser secure context.
Microphone access requires trusted HTTPS. The gateway is not a bypass around TLS trust.

## Deployment modes
- Local developer: HTTP on localhost using `--profile studio`, microphone available.
- LAN/VPN: HTTPS with `--profile studio --profile secure`, `STT_AUTH_MODE=none`.
- Optional organization login: `STT_AUTH_MODE=basic` with a bcrypt hash (or deploy a separately audited SSO gateway).
- TLS `internal`: Caddy internal CA; distribute and trust its **public root CA** on browsers.
- TLS `files`: mount `fullchain.pem` and `privkey.pem`, provisioned by organizational PKI or public ACME DNS-01. For broadly trusted access without per-device CA installation, use a domain with a publicly trusted certificate and internal DNS pointing at the VPN/LAN address. Certificate issuance is external to this deployment.

## Server 62
```bash
cd /srv/soorin-stt
git pull --ff-only origin main
cp -p .env ".env.backup.$(date +%Y%m%d-%H%M%S)"
# Upgrade an existing .env without discarding the pinned model revision, CPU limits or secrets.
# Legacy HTTPS .env files may be missing these options.
for key in STT_TLS_MODE STT_AUTH_MODE STT_TLS_CERT_DIR; do
  grep -q "^$key=" .env || grep "^$key=" .env.example >> .env
done
# Preserve the existing model revision, resource limits and audio settings.
# Set these in .env:
# UI_BIND_HOST=127.0.0.1
# STT_BIND_HOST=127.0.0.1
# STT_HTTPS_HOST=192.168.0.62   # or internal DNS hostname
# STT_HTTPS_BIND_HOST=192.168.0.62
# STT_HTTPS_PORT=3443
# STT_TLS_MODE=internal          # or files
# STT_AUTH_MODE=none             # no shared password
# STT_TLS_CERT_DIR=../certs
# STT_HTTPS_USER=
# STT_HTTPS_PASSWORD_HASH=
python3 scripts/deploy/check_https.py
# Ensure TCP/3443 is accessible ONLY to authorized LAN/VPN ranges before publishing it.
sudo docker compose --env-file .env -f deploy/compose.yaml --profile studio --profile secure config --quiet
sudo docker compose --env-file .env -f deploy/compose.yaml --profile studio build stt-ui
sudo docker compose --env-file .env -f deploy/compose.yaml --profile studio --profile secure up -d --no-build
sudo docker compose --env-file .env -f deploy/compose.yaml --profile studio --profile secure ps
```

For `files` mode, the certificate/key must exist outside Git in the configured directory *before* preflight. Keep private keys restricted and renew certificates using an external PKI/ACME workflow; restart only `stt-https` to pick up replacement keys.

For `internal` mode, Caddy stores the CA in the persistent `stt_https_data` volume. Export **only the public CA root**, verify SHA256 fingerprint out-of-band, and install it as trusted on managed clients:
```bash
CID="$(sudo docker compose --env-file .env -f deploy/compose.yaml --profile secure ps -q stt-https)"
sudo docker cp "$CID:/data/caddy/pki/authorities/local/root.crt" /tmp/soorin-stt-root-ca.crt
openssl x509 -in /tmp/soorin-stt-root-ca.crt -noout -fingerprint -sha256
```
Do NOT copy private CA keys; do NOT use `docker compose down -v` to rotate persistent CA storage. Verify browsers actually trust the cert; simply bypassing a certificate warning is insufficient.

## Security and smoke checks

Access should be restricted by organization firewall/VPN policy to TCP/3443.
**No shared login does not mean public Internet access is appropriate.**
The default API and plain UI bindings must remain loopback; otherwise the HTTPS ingress could be bypassed. Docker published ports can bypass standard UFW policies, so verify host/network edge policy.

```bash
curl -fsS http://127.0.0.1:8080/health/ready
# Internal CA only for server-side smoke testing, not browser trust:
curl -sk https://192.168.0.62:3443/api/health/ready
# Check TLS certificate trust without -k once the CA is exported:
curl --cacert /tmp/soorin-stt-root-ca.crt -fsS https://192.168.0.62:3443/api/health/ready
sudo ss -ltnp | grep -E ':(3443|3015|8080)\b'
```
Expected ports: `192.168.0.62:3443`, `127.0.0.1:3015`, `127.0.0.1:8080`.
Open `https://192.168.0.62:3443` from trusted VPN/LAN devices. In browser Console, verify `window.isSecureContext === true` and `typeof navigator.mediaDevices?.getUserMedia === 'function'`. Verify `wss://` handshake and live transcript.

Operational metrics/docs are not exposed via the Studio UI proxy. Use loopback/container access for operator diagnostics. Model is downloaded only once, on a read-only runtime mount.

## Caveats
- `STT_AUTH_MODE=none` is intended only for trusted internal users behind a verified firewall/VPN. It does not implement user identity, quotas by user, or audit.
- `APP_ENV=production` currently requires an `APP_API_KEY`; browsers do not send that key. Enable production only with an authenticated trusted service gateway/BFF that injects a protected server-side API key. This profile is currently a restricted intranet demo mode, not audited multi-tenant production SSO.

## Compatibility and configuration verification

`STT_TLS_MODE` and `STT_AUTH_MODE` are optional in legacy `.env` files; Compose
and preflight both default to `internal` and `none`, respectively. Add the
explicit keys using the migration commands above so operator intent is visible.
Never overwrite the server's complete `.env` with `.env.example`: doing so
would discard its pinned Shenava revision. The HTTPS bind port must differ
from the published API and HTTP Studio ports.

Run `docker compose ... config --quiet` and `python3 scripts/deploy/check_https.py`
before starting the secure profile. A successful configuration check does not
prove certificate-chain trust on other browsers, VPN reachability, or working
microphone permissions; validate these separately on client devices.

## Caddy TLS alert on raw IP behind Docker (SNI)

Browsers and curl do not normally send SNI for an IP-address URL. With Docker
published-port NAT, Caddy can see the container IP rather than the server's
host IP and fail certificate selection during TLS handshake. The internal CA
configuration sets `default_sni {$STT_HTTPS_HOST}` so non-SNI requests use
the issued certificate for that host address. The Docker CI workflow tests a
TLS handshake without SNI through a mapped host port. Use both Compose profiles
for all inspection commands, because the HTTPS service depends on `stt-ui`:

```bash
sudo docker compose --env-file .env -f deploy/compose.yaml --profile studio --profile secure logs --tail=100 stt-https
sudo docker compose --env-file .env -f deploy/compose.yaml --profile studio --profile secure up -d --no-deps --no-build --force-recreate stt-https
curl -kfsS https://192.168.0.62:3443/api/health/ready
```

A failed TLS handshake is different from a certificate trust failure. The
latter requires installation of the local CA root certificate or a publicly
trusted domain certificate; `-k` is diagnostics-only and not a browser fix.

## Controlled public IP alias / NAT test (Oct 2026)

The network gateway maps public TCP/35942 -> 192.168.0.62:3443 -> container TCP/8443.
A blank HTTP 200 from Caddy occurred when an external Host did not match the configured
private Host. Opt in to an authenticated dual-host route without rebuilding the STT UI/API:

```dotenv
STT_HTTPS_HOST=192.168.0.62
STT_HTTPS_BIND_HOST=192.168.0.62
STT_HTTPS_PORT=3443
STT_TLS_MODE=internal-public
STT_PUBLIC_HTTPS_HOST=93.118.154.255
STT_AUTH_MODE=basic
STT_HTTPS_USER=<username>
STT_HTTPS_PASSWORD_HASH='<bcrypt-hash>'
```

The administrator creates a username and strong password locally. They are NOT
Linux users, FastAPI users, or accounts in a database. Caddy checks this one
shared Basic Auth credential for both web origins; staff obtain the username
and plaintext password securely from the administrator and enter them into
the browser authentication prompt. No self-service registration exists.

Generate the hash interactively without printing the password in a shell command:

```bash
docker run --rm -it caddy:2.10-alpine caddy hash-password
```

Copy the resulting bcrypt hash to the server `.env`, surrounded with single
quotes: `STT_HTTPS_PASSWORD_HASH='$2a$14$...'`. Without single quotes, Compose
may interpret the `# HTTPS Studio on LAN/VPN (no shared password required)

Plain IP HTTP (`http://192.168.0.62:3015`) is not a browser secure context.
Microphone access requires trusted HTTPS. The gateway is not a bypass around TLS trust.

## Deployment modes
- Local developer: HTTP on localhost using `--profile studio`, microphone available.
- LAN/VPN: HTTPS with `--profile studio --profile secure`, `STT_AUTH_MODE=none`.
- Optional organization login: `STT_AUTH_MODE=basic` with a bcrypt hash (or deploy a separately audited SSO gateway).
- TLS `internal`: Caddy internal CA; distribute and trust its **public root CA** on browsers.
- TLS `files`: mount `fullchain.pem` and `privkey.pem`, provisioned by organizational PKI or public ACME DNS-01. For broadly trusted access without per-device CA installation, use a domain with a publicly trusted certificate and internal DNS pointing at the VPN/LAN address. Certificate issuance is external to this deployment.

## Server 62
```bash
cd /srv/soorin-stt
git pull --ff-only origin main
cp -p .env ".env.backup.$(date +%Y%m%d-%H%M%S)"
# Upgrade an existing .env without discarding the pinned model revision, CPU limits or secrets.
# Legacy HTTPS .env files may be missing these options.
for key in STT_TLS_MODE STT_AUTH_MODE STT_TLS_CERT_DIR; do
  grep -q "^$key=" .env || grep "^$key=" .env.example >> .env
done
# Preserve the existing model revision, resource limits and audio settings.
# Set these in .env:
# UI_BIND_HOST=127.0.0.1
# STT_BIND_HOST=127.0.0.1
# STT_HTTPS_HOST=192.168.0.62   # or internal DNS hostname
# STT_HTTPS_BIND_HOST=192.168.0.62
# STT_HTTPS_PORT=3443
# STT_TLS_MODE=internal          # or files
# STT_AUTH_MODE=none             # no shared password
# STT_TLS_CERT_DIR=../certs
# STT_HTTPS_USER=
# STT_HTTPS_PASSWORD_HASH=
python3 scripts/deploy/check_https.py
# Ensure TCP/3443 is accessible ONLY to authorized LAN/VPN ranges before publishing it.
sudo docker compose --env-file .env -f deploy/compose.yaml --profile studio --profile secure config --quiet
sudo docker compose --env-file .env -f deploy/compose.yaml --profile studio build stt-ui
sudo docker compose --env-file .env -f deploy/compose.yaml --profile studio --profile secure up -d --no-build
sudo docker compose --env-file .env -f deploy/compose.yaml --profile studio --profile secure ps
```

For `files` mode, the certificate/key must exist outside Git in the configured directory *before* preflight. Keep private keys restricted and renew certificates using an external PKI/ACME workflow; restart only `stt-https` to pick up replacement keys.

For `internal` mode, Caddy stores the CA in the persistent `stt_https_data` volume. Export **only the public CA root**, verify SHA256 fingerprint out-of-band, and install it as trusted on managed clients:
```bash
CID="$(sudo docker compose --env-file .env -f deploy/compose.yaml --profile secure ps -q stt-https)"
sudo docker cp "$CID:/data/caddy/pki/authorities/local/root.crt" /tmp/soorin-stt-root-ca.crt
openssl x509 -in /tmp/soorin-stt-root-ca.crt -noout -fingerprint -sha256
```
Do NOT copy private CA keys; do NOT use `docker compose down -v` to rotate persistent CA storage. Verify browsers actually trust the cert; simply bypassing a certificate warning is insufficient.

## Security and smoke checks

Access should be restricted by organization firewall/VPN policy to TCP/3443.
**No shared login does not mean public Internet access is appropriate.**
The default API and plain UI bindings must remain loopback; otherwise the HTTPS ingress could be bypassed. Docker published ports can bypass standard UFW policies, so verify host/network edge policy.

```bash
curl -fsS http://127.0.0.1:8080/health/ready
# Internal CA only for server-side smoke testing, not browser trust:
curl -sk https://192.168.0.62:3443/api/health/ready
# Check TLS certificate trust without -k once the CA is exported:
curl --cacert /tmp/soorin-stt-root-ca.crt -fsS https://192.168.0.62:3443/api/health/ready
sudo ss -ltnp | grep -E ':(3443|3015|8080)\b'
```
Expected ports: `192.168.0.62:3443`, `127.0.0.1:3015`, `127.0.0.1:8080`.
Open `https://192.168.0.62:3443` from trusted VPN/LAN devices. In browser Console, verify `window.isSecureContext === true` and `typeof navigator.mediaDevices?.getUserMedia === 'function'`. Verify `wss://` handshake and live transcript.

Operational metrics/docs are not exposed via the Studio UI proxy. Use loopback/container access for operator diagnostics. Model is downloaded only once, on a read-only runtime mount.

## Caveats
- `STT_AUTH_MODE=none` is intended only for trusted internal users behind a verified firewall/VPN. It does not implement user identity, quotas by user, or audit.
- `APP_ENV=production` currently requires an `APP_API_KEY`; browsers do not send that key. Enable production only with an authenticated trusted service gateway/BFF that injects a protected server-side API key. This profile is currently a restricted intranet demo mode, not audited multi-tenant production SSO.

## Compatibility and configuration verification

`STT_TLS_MODE` and `STT_AUTH_MODE` are optional in legacy `.env` files; Compose
and preflight both default to `internal` and `none`, respectively. Add the
explicit keys using the migration commands above so operator intent is visible.
Never overwrite the server's complete `.env` with `.env.example`: doing so
would discard its pinned Shenava revision. The HTTPS bind port must differ
from the published API and HTTP Studio ports.

Run `docker compose ... config --quiet` and `python3 scripts/deploy/check_https.py`
before starting the secure profile. A successful configuration check does not
prove certificate-chain trust on other browsers, VPN reachability, or working
microphone permissions; validate these separately on client devices.

## Caddy TLS alert on raw IP behind Docker (SNI)

Browsers and curl do not normally send SNI for an IP-address URL. With Docker
published-port NAT, Caddy can see the container IP rather than the server's
host IP and fail certificate selection during TLS handshake. The internal CA
configuration sets `default_sni {$STT_HTTPS_HOST}` so non-SNI requests use
the issued certificate for that host address. The Docker CI workflow tests a
TLS handshake without SNI through a mapped host port. Use both Compose profiles
for all inspection commands, because the HTTPS service depends on `stt-ui`:

```bash
sudo docker compose --env-file .env -f deploy/compose.yaml --profile studio --profile secure logs --tail=100 stt-https
sudo docker compose --env-file .env -f deploy/compose.yaml --profile studio --profile secure up -d --no-deps --no-build --force-recreate stt-https
curl -kfsS https://192.168.0.62:3443/api/health/ready
```

A failed TLS handshake is different from a certificate trust failure. The
latter requires installation of the local CA root certificate or a publicly
trusted domain certificate; `-k` is diagnostics-only and not a browser fix.

## Controlled public IP alias / NAT test (Oct 2026)

The network gateway maps public TCP/35942 -> 192.168.0.62:3443 -> container TCP/8443.
A blank HTTP 200 from Caddy occurred when an external Host did not match the configured
private Host. Opt in to an authenticated dual-host route without rebuilding the STT UI/API:

```dotenv
STT_HTTPS_HOST=192.168.0.62
STT_HTTPS_BIND_HOST=192.168.0.62
STT_HTTPS_PORT=3443
STT_TLS_MODE=internal-public
STT_PUBLIC_HTTPS_HOST=93.118.154.255
STT_AUTH_MODE=basic
STT_HTTPS_USER=<username>
STT_HTTPS_PASSWORD_HASH='<bcrypt-hash>'
```

 characters in a bcrypt hash as interpolation tokens.
Store the password securely and keep `.env` permissions restricted (`chmod 600`).
The hash is not a password users can type; users enter the original password.
Never commit the actual credentials or hash. Note that password sharing does
not provide separate identities, per-user audit, or revocation; changing the
shared password affects everyone. Browser WebSocket auth must be tested on
Firefox/Chrome because authentication credential caching may differ.

This mode authenticates BOTH the private and the public Host. Otherwise public
clients can spoof the private HTTP Host to bypass a public-only auth rule.
The original internal mode stays unchanged unless explicitly opted in.

Critical TLS limitation: most IP-only HTTPS clients omit SNI. The existing
global default_sni uses the PRIVATE IP; on the single forwarded TLS listener
the PUBLIC IP may therefore receive a certificate whose SAN contains only
the private IP. Additional host routing alone does NOT fix public certificate
identity or trust. The internal Caddy CA is also not publicly trusted.
This is for controlled testing only, not general unauthenticated Internet
deployment. A managed organizational DNS hostname with a trusted certificate
and a real public access gateway (or separate TLS listeners) is required
for broad public-browser use without certificate warnings.

Safe STT-only deployment after network-team approval:

```bash
cd /srv/soorin-stt
python3 scripts/deploy/check_https.py
sudo docker compose --env-file .env -f deploy/compose.yaml --profile studio --profile secure config --quiet
sudo docker compose --env-file .env -f deploy/compose.yaml --profile studio --profile secure up -d --no-deps --no-build --force-recreate stt-https
```

Public route checks from an authorized client (the -k flag is for diagnostic
HTTP routing tests ONLY, not proof of trusted HTTPS):

```bash
curl -k -i https://93.118.154.255:35942/api/health/ready
curl -k -u "<user>:<password>" -i https://93.118.154.255:35942/api/health/ready
curl -k -i -H "Host: 192.168.0.62:3443" https://93.118.154.255:35942/api/health/ready
```

Expected: 401, JSON 200 after authentication, 401 for spoofed Host with no
credentials. Confirm static JS/CSS assets and authenticated browser WSS
streaming; HTTP 200 alone is insufficient. Since both hosts require Basic
Auth in this mode, the private URL will also prompt for credentials.
To roll back, restore STT_TLS_MODE=internal and recreate ONLY stt-https.
Never remove the Caddy CA storage volume or restart unrelated services.
