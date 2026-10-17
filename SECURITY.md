# Security and privacy

Soorin STT operates on potentially confidential audio and generated transcripts.

- For production **must** set `APP_API_KEY`, terminate TLS at an authenticated gateway, configure restrictive `APP_CORS_ORIGINS`, and avoid exposing `/metrics` and `/docs` publicly. Browser WebSocket headers cannot send `X-API-Key`; use same-origin authenticated gateway/session routing for production UI.
- Audio/transcript bodies are not logged. Do not enable diagnostic audio capture without approval and a retention policy.
- Model weights are loaded from pinned, locally hashed files only (default `STT_REQUIRE_MODEL_PIN=true`). Never use remote code from model repos. Use isolated HF download identity, with appropriately restricted permissions.
- ASR output is **untrusted text**. Treat it as a command request requiring authorization and confirmation in Agentic SOC/Copilot, not as a trusted instruction.
- Reject oversized audio and frames, enforce stream timeouts/concurrency, deploy a reverse-proxy rate limiter for admission control.
- Container runs without root, with read-only filesystem and read-only model mount. Maintain dependency scans and periodically pin image digests.
- Use privacy-safe metrics. Do not include request IDs, text content, token values or arbitrary hostnames as Prometheus labels.
- Model hallucination/error may corrupt network IDs. Keep `text` (raw) and `normalized_text`, and verify entities independently before taking an action.
- No external call for inference. Downloader uses Hugging Face only during installation; the runtime is configured offline.

Contact the Soorin security team privately before deploying this service outside a protected network.
