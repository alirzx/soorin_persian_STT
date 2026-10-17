# Model adapter status and compatibility matrix

Backend types:

| Catalog backend | Dependency | Implementation | Streaming mode |
|---|---|---|---|
| `sherpa_offline_ctc` | `sherpa-onnx` | ONNX NeMo CTC, real local CPU batch | buffered partials |
| `sherpa_online_ctc` | `sherpa-onnx` | ONNX NeMo cache-aware `OnlineRecognizer` | native |
| `sherpa_online_transducer` | `sherpa-onnx` | Nemotron RNNT ONNX, 128 mel, fa-IR prompt | native |
| `faster_whisper` | `faster-whisper`, `ctranslate2` | local converted CT2 checkpoint | buffered partials |
| `qwen_asr` | `qwen-asr`/PyTorch | local Python SDK | buffered partials |
| `transformers_asr` | PyTorch/transformers | local AutoPipeline | buffered partials |
| `vosk` | `vosk` | local model directory | native |
| `external_http` | reachable inference gateway | Soorin-compatible HTTP transcoding | buffered fallback |

The official INT4 Shenava streaming checkpoint is **tract-specific**. This repository catalogs/downloads it, and can route batch requests to a separately deployed tract bridge via `STT_EXTERNAL_BASE_URL`. It **does not ship a Rust tract inference binary**, does not claim native INT4 streaming from Python, and cannot turn the export into standard ONNX Runtime simply by changing an environment variable. To integrate a native Rust tract process later, implement the stable Soorin HTTP/WS contract as a standalone adapter and set backend capabilities to native only once tested.

Some third-party INT8 Shenava graphs are listed as noncommercial, and some model cards erroneously show their streaming graph used with an offline recognizer command. Soorin's online recognizer path is intentionally separate and should be validated against graph metadata before declaring production readiness.

Nemotron third-party sherpa export uses **128 mel bins** and **requires** `stream.set_option('language','fa-IR')`; this differs from Shenava's 80 mel bins. A missing or incompatible graph must cause readiness=503, never a fake successful transcription.

Whisper requires conversion: `python scripts/convert_whisper.py --model taraneh-wbase`. Inference is from `<model>/ct2` only, not raw Hugging Face transformers checkpoints. A big model may be incompatible with CPU limits; benchmarking is mandatory.

For all catalog entries, exact file names, license and revision are verified at download time but not all have been executed here. The downloader **does not download noncommercial artifacts unless expressly allowed**, and the live runtime never pulls from HF implicitly.
