#!/usr/bin/env python3
import argparse
import json
import os
import time
from pathlib import Path
import psutil
from soorin_stt.audio.decoder import decode_audio
from soorin_stt.backends.registry import resolve,build_backend
from soorin_stt.core.config import get_settings
from soorin_stt.models_cli import verify
from soorin_stt.text.persian_normalizer import normalize_text

def main():
    p=argparse.ArgumentParser();p.add_argument('--file',required=True);p.add_argument('--reference',default='');p.add_argument('--out',default='benchmarks/results/local.json');a=p.parse_args()
    s=get_settings();spec=resolve(s);meta=verify(spec.name)
    sound=decode_audio(Path(a.file).read_bytes(),s.audio_sample_rate,s.audio_max_seconds)
    backend=build_backend(s,spec)
    proc=psutil.Process(os.getpid());start=time.monotonic();backend.load();backend.warmup();load=time.monotonic()-start
    start=time.monotonic();result=backend.transcribe(sound,s.audio_sample_rate);seconds=time.monotonic()-start;rss=proc.memory_info().rss
    report={'model':spec.name,'revision':meta.get('revision'),'backend':spec.backend,'cpu_threads':s.stt_cpu_threads,
            'audio_seconds':len(sound)/s.audio_sample_rate,'warmup_seconds':load,'inference_seconds':seconds,
            'rtf':seconds/max(len(sound)/s.audio_sample_rate,.001),'rss_bytes':rss,'transcript':result.text}
    if a.reference:
        from eval.metrics import wer,cer
        ref=normalize_text(a.reference)[0];hyp=normalize_text(result.text)[0]
        report['wer']=wer(ref,hyp);report['cer']=cer(ref,hyp)
    dest=Path(a.out);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2));backend.close()
if __name__=='__main__':main()
