# Soorin STT deployment checklist (Shenava Koochik CPU)

**Status:** deployment configuration prepared; real multi-user performance and final
production security approval require testing on target infrastructure. The model
is **offline Sherpa CTC**, offering *bounded buffered* pseudo-streaming, not
native cache-aware recognition.

## 1. Prepare host and artifacts

Install Docker Engine and Compose v2. Clone the same Git commit as the build.
Set up the verified Shenava model at
`models/downloads/shenava-koochik/{model.onnx,tokens.txt,.soorin-model.json}`.
**Do not put model binaries or .env in a Docker image or commit them to Git.**
The model directory mounts read-only.

```bash
cp .env.example .env
# edit .env; use APP_ENV=production and a strong APP_API_KEY for production
./scripts/deploy/preflight.sh
./scripts/deploy/prepare-network.sh
docker compose --env-file .env -f deploy/compose.yaml config
docker compose --env-file .env -f deploy/compose.yaml up --build -d
docker compose --env-file .env -f deploy/compose.yaml ps
docker compose --env-file .env -f deploy/compose.yaml logs -f --tail=100 stt-api
curl --fail http://127.0.0.1:8080/health/ready
```

`preflight.sh` checks prerequisites and file presence; `soorin-models verify`
and service startup perform cryptographic verification. Start from the repo
root, where the host .env lives.

## 2. Shared Docker network and service consumers

An external attachable Docker bridge named `soorin-ai` is required.
`prepare-network.sh` creates it idempotently. Containers from *other*
Compose projects can attach with an external network declaration and call
`http://stt-api:8080/v1/audio/transcriptions` (HTTP) or
`ws://stt-api:8080/v1/audio/transcriptions/stream` (WS).
The Compose API/UI port bindings default to **127.0.0.1 only**, not public
host interfaces. In production, route through a trusted authenticated
gateway with TLS; do not expose port 8080 directly.

A client Compose example:

```yaml
services:
  consumer:
    image: your-consumer-image:tag
    networks: [soorin-ai]
networks:
  soorin-ai:
    external: true
    name: soorin-ai
```

## 3. Studio UI (development/trusted private demo only)

The UI is opt-in to avoid shipping an unprotected browser client as a
production frontend. With `APP_ENV=development` and empty APP_API_KEY:

```bash
docker compose --env-file .env -f deploy/compose.yaml --profile studio up --build -d
# UI: http://127.0.0.1:3015 | API: http://127.0.0.1:8080
```

Port 3000 is reserved by Soorin Copilot Grafana on the development host.\nThe STT Studio uses host port 3015 by default; Nginx still listens on port 80\ninside the container. To override this, set `UI_PORT` in the host `.env` or\nsupply `UI_PORT=3015` before the `docker compose` command. If an existing\n`.env` contains `UI_PORT=3000`, change that value manually: Compose\ninterpolation will otherwise keep using the old port. Confirm the port is free\nusing `ss -ltnp | grep ':3015 '` before starting.\n\nThe studio does not implement SSO or browser-safe API key exchange. When
`APP_API_KEY` is configured, a trusted authenticated reverse proxy must
supply the credential upstream, otherwise browser transcription requests
will fail. Never embed a service credential into React JavaScript.

## 4. Operational and resource checklist

- One Uvicorn worker by design (one ONNX model copy per process).
- Default CPU quota: 4 cores; memory and combined swap limit: 3 GiB.
  **Tune from measured concurrency and memory, not from guesses.**
- Inference slots and WebSocket sessions are separately limited. Tune
  `APP_INFERENCE_CONCURRENCY` and `STREAM_MAX_SESSIONS` conservatively.
- Runtime model checksum pinning and warmup precede readiness.
- Confirm `/health/ready` = 200 and `stt_model_loaded 1`. Keep
  `/metrics`, `/docs`, and STT content private.
- Run repeatable Persian WAV and microphone tests, disconnections and
  load tests; track streaming queue overflows, duration/RTF and memory.
- Rotate keys via your secret manager, deploy pinned images, configure
  reverse-proxy request limits/TLS, and monitor container restarts.

### Kubernetes template

`deploy/kubernetes` is an example only. Replace the image registry,
models PVC, Secret, ingress, network policy and resource requests to match
your cluster. The template now mounts a writable, size-capped `/tmp`
while preserving a read-only root filesystem.

**Do not claim production release acceptance until target-host smoke,
concurrent-client and authentication checks pass.**
