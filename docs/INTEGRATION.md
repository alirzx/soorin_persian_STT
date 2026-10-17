# Soorin STT consumer integration contract (v1)

## Docker network
Attach consumers and `stt-api` to the external `soorin-ai` network. Docker DNS:
`http://stt-api:8080`. The API is a single warm-loaded Shenava service.
A UI browser outside Docker uses a reverse-proxied `/api` path instead.

## Batch
`POST /v1/audio/transcriptions` multipart fields: `file`, `language=fa`,
`domain=general|soc`, `normalize=true|false`, `timestamps`.
The server returns `request_id`, `model`, `text`, `normalized_text`,
`duration_ms`, `processing_ms`, `rtf`, `segments`, `entities`,
`streaming_mode`.

## Streaming
WebSocket `/v1/audio/transcriptions/stream` with header `X-API-Key` for
trusted internal applications (when enabled). Send JSON `session.start`
before 16 kHz mono signed PCM16 frames (20 ms/640 bytes recommended).
On completion send JSON `session.end` and wait for `transcript.final`
followed by `session.closed`. `transcript.segment` denotes committed
utterance text; `transcript.partial` is provisional and may be revised.
Do not append each partial as if it were new text. `sequence` increases
per transcription event. `end_ms` on final is elapsed received audio time.
`session.error` terminates failed sessions.

## Security
Keep the API reachable only on trusted networks. Set `APP_API_KEY` to a
long random value for production and provision it via container secrets.
Untrusted browsers must use a trusted backend proxy, not an embedded key.
The supplied React UI is a development console and must not be published
on the Internet as-is. Use network isolation, reverse proxy TLS, and
separate credentials for client applications where required.
CORS is *not* a protection for machine-to-machine callers.

## Reliability
Requests exceeding a configured deadline respond with 504, but native
ONNX execution may finish asynchronously. The service holds the inference
slot until the native worker exits to prevent CPU oversubscription.
Overloaded slots return 429. Model readiness returns 503 when unavailable.
Runtime metrics are at /metrics, intended for internal monitoring only.
