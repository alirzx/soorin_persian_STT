#!/usr/bin/env python3
"""Convert an already downloaded HF Whisper snapshot to local CT2 INT8.

Needs optional whisper + transformers dependencies, and does not fetch external weights.
"""
import argparse
from pathlib import Path
import subprocess
from soorin_stt.core.config import get_settings
from soorin_stt.backends.registry import catalog

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--model',required=True)
    parser.add_argument('--quantization',default='int8',choices=['int8','float32','float16'])
    args=parser.parse_args()
    settings=get_settings();spec=catalog(settings.stt_catalog_dir)[args.model]
    if spec.backend!='faster_whisper':raise SystemExit('not a Whisper catalog entry')
    root=settings.stt_model_dir/args.model
    if not (root/'config.json').is_file():raise SystemExit('download the HF model first')
    subprocess.run(['ct2-transformers-converter','--model',str(root),
            '--output_dir',str(root/'ct2'),'--quantization',args.quantization,'--force'],check=True)
    print('CT2 ready:',root/'ct2')
if __name__=='__main__':main()
