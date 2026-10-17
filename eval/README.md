# Dataset evaluation

JSONL: each row is `{ "audio": "/path/to/file.wav", "reference": "متن مرجع", "speaker_id": "...", "domain": "soc", "entities": [] }`. Run `python eval/run_eval.py --manifest eval/manifests/local.jsonl --output benchmarks/results/eval.json`. Keep audio and protected manifests out of the source repository. Compare per speaker/dataset/accent and the same normalization policy. This evaluation code does not load remote model weights.
