# Soorin STT

**Persian speech recognition as an independent, offline-first, CPU-first service.** A unified HTTP/WebSocket contract fronts interchangeable model runtimes. This repository is a runnable engineering baseline, not a claim that every catalog checkpoint has passed Soorin hardware benchmarks.

## What is implemented

- FastAPI REST transcription and PCM16 WebSocket sessions with partial/final events.
- **Native cache-aware streaming** through `sherpa_onnx.OnlineRecognizer.from_nemo_ctc()` for compatible model exports; native RNNT support through `OnlineRecognizer.from_transducer()`; **clearly labeled buffered pseudo-streaming** for non-streaming models.
- Model catalog covering >20 configurations: Shenava Koochik/Rizeh/Pizeh, Nemotron, Taraneh Whisper/Qwen, C1Tech, BuzzASR, generic Qwen, XLS-R and Vosk.
- Hugging Face model downloader that resolves an immutable revision, computes local SHA-256 files, and writes a local manifest; offline-only inference after initial download.
- Explicit runtime types, fail-closed model loading/verification, one backend process, resource caps, CPU threads, warmup-before-readiness, metrics and tests.
- Persian character and technical-term normalization, configurable domain behavior, and retention of raw transcription.
- React/Vite web studio with local microphone streaming and file transcription, Docker Compose, Kubernetes examples, CI.

## The crucial Shenava artifact distinction

**There is no universally interchangeable `model.int4.onnx`.** The official [Shenava Koochik tract INT4 bundle](https://huggingface.co/PersianML/Shenava-Koochik-v1.0-tract-streaming) is a 138 MB cache-aware export for a **Rust tract revision with the custom graph support**. It is *not* an ordinary `sherpa-onnx` or `onnxruntime.InferenceSession` graph. The `shenava-koochik-tract-int4` registry entry uses the **external HTTP inference adapter** and requires a separately implemented/running compatible Rust gateway; it is not silently loaded by Python.

The **default runnable Koochik** uses the official Apache-2.0 [sherpa offline ONNX bundle](https://huggingface.co/PersianML/Shenava-Koochik-v1.0-sherpa-onnx), with buffered WebSocket partials (not cache-aware). Native streaming can be tested with `shenava-koochik-stream-int8`, a third-party `sherpa-onnx` export, **but that repository is explicitly CC-BY-NC-4.0**, so it is prohibited as Soorin's commercial default absent permission. The original Shenava project's Apache license must not be assumed to override the third-party artifact license. See [Model licensing](MODEL_LICENSES.md).

### Start locally

Requirements: Ubuntu/Linux, Python 3.11–3.13, FFmpeg if you want MP3 decoding, Node 22 (UI), and access to Hugging Face only **at installation/download time**.

```bash
cd soorin-stt
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[sherpa,test]'

# Inspect models and download the default, resolving immutable HF commit + SHA256 for artifacts.
soorin-models list
soorin-models download --model shenava-koochik
soorin-models verify --model shenava-koochik

# The startup loads and warms the model. Readiness 200 only after success.
uvicorn soorin_stt.main:app --host 127.0.0.1 --port 8080 --workers 1

# New terminal:
curl http://127.0.0.1:8080/health/ready
curl -F 'file=@path/to/persian.wav' -F 'language=fa' -F 'domain=general' http://127.0.0.1:8080/v1/audio/transcriptions

# React development server, proxying /api and WS traffic to localhost:8080
cd ui && npm install && npm run dev
# http://localhost:5173
```

**No model weights are included in this ZIP.** The runner environment has no network connectivity, so model downloads and real acoustic inference have **not** been performed here. You must run the download, inspect the licenses, and reproduce an actual Persian audio benchmark locally before shipping.

### Switch model without changing APIs

```bash
# 1. Model choice (examples)
sed -i 's/^STT_MODEL=.*/STT_MODEL=shenava-rizeh/' .env
soorin-models download --model shenava-rizeh
# 2. Restart one process; backend is only loaded at process startup.
```

After installing `uv`, run `uv lock` on a network-connected build machine and commit the generated `uv.lock` for reproducible production builds. A lockfile is deliberately not fabricated in this offline-generated source archive.

`STT_MODEL` is a key from `configs/models/*.yaml`. Do not override a catalog's `backend` with an incompatible runtime. `STT_MODEL_ID` and `STT_BACKEND` overrides are validated and rejected if they conflict. Model revisions are pinned at download time, with metadata saved in `models/downloads/<model>/.soorin-model.json`. A new model simply needs a new catalog YAML and an existing compatible adapter, or a new adapter implementing the same contract.

For a Whisper checkpoint, additionally run:

```bash
pip install -e '.[whisper,transformers]'
soorin-models download --model taraneh-wbase
python scripts/convert_whisper.py --model taraneh-wbase --quantization int8
# set STT_MODEL=taraneh-wbase then restart API
```

For Qwen, install `.[qwen]` and plan for significantly higher CPU RAM/latency. For Nemotron's sherpa conversion, model uses **128** features and `fa-IR` stream prompt; the adapter accounts for both, but this runtime/model pairing still needs an end-to-end run on your host. Where an upstream model format differs, the registry must fail instead of pretending the graph can run.

### Docker Compose

```bash
# Download model onto host first, with STT_MODEL_DIR=./models/downloads in host .env
soorin-models download --model shenava-koochik
# then run backend+UI (Compose mounts models read-only)
docker compose --env-file .env -f deploy/compose.yaml up --build -d
# UI http://localhost:3000 | backend http://localhost:8080/docs
```

Docker copies `pyproject.toml`/Python package and installs `.[sherpa]`. To use Whisper/Qwen, build a specialized image with the relevant optional extras. The backend does not fetch models at request time.

### APIs

| Method | Route | Purpose |
|---|---|---|
| POST | `/v1/audio/transcriptions` | `multipart/form-data`: `file`, `language=fa`, `normalize`, `timestamps`, `domain` |
| WS | `/v1/audio/transcriptions/stream` | JSON `session.start`, binary 16kHz mono PCM16 little-endian frames, JSON `session.end`, partial/final transcript events |
| GET | `/health/live` | Process liveness |
| GET | `/health/ready` | Model load + warmup successful |
| GET | `/v1/models/current` | Active model and native vs buffered mode |
| GET | `/metrics` | Prometheus |
| GET | `/version`, `/docs` | Version / OpenAPI |

WebSocket protocol: first message `{ "type":"session.start", "audio":{"format":"pcm_s16le","sample_rate":16000,"channels":1}, "language":"fa", "normalize":true, "domain":"general" }`. Wait for `session.ready`, then transmit binary frames (320 samples/20 ms recommended). Send `{ "type":"session.end" }`; receive `transcript.final` then `session.closed`. The React UI uses AudioWorklet resampling for microphone streams.

### Configuration and reliability

- `.env.example` documents service/CPU/model/audio/stream limits. `APP_API_KEY` protects REST and WS integrations when set. Always enable service authentication, TLS and trusted ingress for a production deployment.
- Log raw audio is disabled; incoming audio is handled in memory. Keep audio duration and upload size bounded.
- `/health/live` is 200 even if inference unavailable; `/health/ready` fails closed (503) unless the selected backend was loaded and warmed.
- One Uvicorn worker is deliberate to avoid unnecessary model copies. Concurrency is limited via a semaphore and stream/session cap.
- The audio input decoder uses `libsndfile` via `soundfile` (WAV/FLAC/Ogg supported depending on installed build); MP3 availability depends on codecs/library version, not guaranteed by the endpoint.
- Prometheus metrics have no user/session identifiers. Do not log content or use session IDs as metric labels.

### Tests and maturity

```bash
PYTHONPATH=src pytest -q
python -m compileall -q src
```

The tests validate schemas, catalog switching, Persian normalization, decoder, HTTP contract and a fake WebSocket recognizer; **they are not a substitute for tests against real models**, nor has the UI been browser-tested in this restricted sandbox. `docs/MODELS.md` details model capabilities, adapter status and licensing caveats.

### Repository status

This is **an implemented, testable service foundation with production patterns**, not a production-certified binary. The official Rust tract INT4 gateway is intentionally not represented as a working Python native adapter. High-resource and third-party Qwen/Nemotron paths are implemented as candidate integration routes but must pass live model/hardware/licensing tests before release. K8s YAML is an operational template and needs real image/PVC/Secret/ingress values.


## October 2026 hardening branch

The Shenava offline backbone is unchanged. Buffered WebSocket sessions use RMS endpointing and bounded utterance windows rather than retranscribing an unbounded recording. Partial hypotheses are provisional; segment events include the committed full transcript, and the final event remains backward compatible. Streaming metrics are separate from batch metrics. A timed-out native inference thread retains its concurrency slot until it exits.

For multiple Soorin products in the same Docker network, create one shared network before Compose startup: `docker network create soorin-ai` (once); the service hostname is `stt-api`, with `http://stt-api:8080/v1/audio/transcriptions` for other containers attached to `soorin-ai`. Use a shared secret, trusted ingress, and private networking; do not rely on CORS as authentication. The development studio has no secret-injection mechanism and should not be exposed publicly.

Brand logo slot: place your official SVG at `ui/public/brand/soorin-logo.svg`. The interface falls back to its standard voice symbol until that asset is present. Do not commit copyrighted corporate marks without permission.

Resource model: a single CPU worker and bounded concurrency protect a single loaded ONNX model; these changes are not a validated capacity claim for multiple simultaneous real-world streams. Load testing on the target server is required. Native INT4 tract inference is outside this patch.
