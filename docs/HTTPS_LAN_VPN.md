# Soorin STT | HTTPS, LAN, and Public Alias

Server 62: internal `https://192.168.0.62:3443`; public NAT forwards
`https://93.118.154.255:35942` to private port 3443 and container Caddy 8443.
Backend (8080) and plain React/Nginx (3015) stay host-loopback only.

## Authentication options

- `STT_TLS_MODE=internal-public` serves BOTH private and public Hosts
  with the SAME authentication policy (never bypass auth using Host headers).
- `STT_AUTH_MODE=basic` keeps the existing shared Caddy login on both.
  Set `STT_HTTPS_USER` and single-quoted bcrypt `STT_HTTPS_PASSWORD_HASH`.
- `STT_AUTH_MODE=none` removes browser username/password on BOTH Hosts.
  For `internal-public` this MUST be paired with
  `STT_ALLOW_PUBLIC_NO_AUTH=true`. Defaults to `false` to preserve
  authentication unless the operator explicitly opts in.
- LAN-only `internal` mode supports no-auth WITHOUT the public flag,
  but public NAT forwarding must be disabled for LAN-only exposure.

**Security:** Password-free public access is reachable by *any* internet
client that can reach the forwarded port. The opt-in flag is an operational
acknowledgement, not access control. Before enabling it, obtain network
approval, review perimeter ACLs, abuse/rate limits and capacity quotas.
The Studio does not provide identity, per-user audit or rate limits.
CORS and IP-based Host checks are not effective alternatives to auth.

## Server configuration (no browser login, both Hosts)

Edit the existing server `.env` after synchronizing repository source;
preserve all model revision/CPU settings and any API token.

```dotenv
STT_BIND_HOST=127.0.0.1
APP_PORT=8080
UI_BIND_HOST=127.0.0.1
UI_PORT=3015
STT_HTTPS_HOST=192.168.0.62
STT_HTTPS_BIND_HOST=192.168.0.62
STT_HTTPS_PORT=3443
STT_TLS_MODE=internal-public
STT_PUBLIC_HTTPS_HOST=93.118.154.255
STT_AUTH_MODE=none
STT_ALLOW_PUBLIC_NO_AUTH=true
STT_HTTPS_USER=
STT_HTTPS_PASSWORD_HASH=
```

`APP_API_KEY` is a SEPARATE backend mechanism: if configured, backend
requests require `X-API-Key` and React does not inject this header.
Use a trusted BFF if production requires API-key authentication and a
browser UI. Do not place the API key inside JavaScript.

## Update only Caddy, not other Docker projects

```bash
cd /srv/soorin-stt
cp -p .env ".env.backup.$(date +%Y%m%d-%H%M%S)"
chmod 600 .env
# Edit the HTTPS/auth keys above, retaining all other values.
python3 scripts/deploy/check_https.py
sudo docker compose --env-file .env -f deploy/compose.yaml --profile studio --profile secure config --quiet
sudo docker compose --env-file .env -f deploy/compose.yaml --profile studio --profile secure up -d --no-deps --no-build --force-recreate stt-https
sudo docker compose --env-file .env -f deploy/compose.yaml --profile studio --profile secure ps
```

Do not run `down -v` or delete the Caddy data volume: it holds the private
CA certificates. The API and UI images need no rebuild for this gateway-only
change. To roll back, set `STT_AUTH_MODE=basic`, restore the prior username
and bcrypt hash, set `STT_ALLOW_PUBLIC_NO_AUTH=false`, validate and
recreate only `stt-https`.

## Post-deploy verification

```bash
curl -k -i https://192.168.0.62:3443/api/health/ready
curl -k -i https://93.118.154.255:35942/api/health/ready
curl -k -o /dev/null -w '%{http_code} %{size_download}\n' https://192.168.0.62:3443/
curl -k -o /dev/null -w '%{http_code} %{size_download}\n' https://93.118.154.255:35942/
```

Both Hosts should return 200 with nonempty React HTML; there should
be NO `WWW-Authenticate: Basic` challenge. Test public access from
an independent external network, not only via server NAT loopback.
Check JS/CSS assets and `wss://.../api/v1/audio/transcriptions/stream`.

## TLS limitations

`tls internal` uses a locally managed Caddy CA not trusted on public
browsers by default. Raw-IP TLS clients typically omit SNI; `default_sni`
currently selects the PRIVATE-IP certificate, which might not cover the
public IP. Thus `curl -k` only validates HTTP routing, not certificate
identity/trust or browser microphone permission. To support outside
browsers reliably, prefer a publicly trusted domain certificate and
audited gateway. For managed LAN devices, export only the PUBLIC CA root:

```bash
CID="$(sudo docker compose --env-file .env -f deploy/compose.yaml --profile studio --profile secure ps -q stt-https)"
sudo docker cp "$CID:/data/caddy/pki/authorities/local/root.crt" /tmp/soorin-stt-root-ca.crt
openssl x509 -in /tmp/soorin-stt-root-ca.crt -noout -fingerprint -sha256
```

Never export the CA private key. Verify `window.isSecureContext`,
`navigator.mediaDevices.getUserMedia`, and live WebSocket transcription
from the target browsers before release.
