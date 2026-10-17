# Model and data licenses (release gate)

The repository source code is MIT. That license **does not** license model weights, datasets, third-party code or runtime binaries.

| Model/package | Reported license | Product gate |
|---|---|---|
| PersianML Shenava Koochik source/sherpa/tract | Apache-2.0 | Confirm exact deployed repo snapshot and include attribution |
| Reza2kn Rizeh/Rizeh-Pizeh sherpa | Apache-2.0 | Verify exact snapshot |
| mah92 Shenava streaming INT8 conversion | **CC-BY-NC-4.0** | **Not commercially permitted by default**; requires separate authorization |
| Nemotron Farsi original and ONNX conversion | OpenMDW-1.1 | Legal review before commercial release |
| Taraneh WBase/WMedium/WLarge | MIT (published) | Keep source notices; verify exact snapshot |
| Taraneh Q0.6B / Q1.7B | Apache-2.0 (published) | Keep source notices |
| C1Tech Whisper Base/Small | Apache-2.0 (published) | Recheck gated datasets/artifacts |
| BuzzASR Persian | MIT | Verify model repo and attribution |
| Vosk Persian Small | Apache-2.0 in upstream materials | Verify actual unpacked release |
| steja Whisper Large Persian | Apache-2.0 | Historical benchmark only |
| Unknown/unreviewed models | Unknown | Not for commercial deployment |

This table is an R&D record, not legal advice. Model cards and downstream exports sometimes disagree: do **not** resolve conflicts by guessing. `STT_ALLOW_NONCOMMERCIAL=false` blocks explicitly flagged weights. Do not set it true for Soorin production.

The downloader records model repository, immutable HF commit, advertised license and checksums in `.soorin-model.json`. For production you must also pin runtime wheels/container digests and validate training dataset terms where applicable.
