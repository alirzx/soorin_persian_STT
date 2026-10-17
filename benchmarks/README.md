# Reproducible benchmarks

Run `python scripts/benchmark.py --file /path/audio.wav --reference '...' --out benchmarks/results/local.json` with a locally loaded model. The public numbers in the R&D report are NOT local Soorin measurements. Record CPU model, commit, threads, RTF, RSS and WER with a common text-normalization protocol. Avoid logging confidential recordings.
