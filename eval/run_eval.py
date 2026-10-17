#!/usr/bin/env python3
import argparse
import json
import os
import sys
import time
from pathlib import Path
import soundfile as sf
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'src'))
from soorin_stt.core.config import get_settings
from soorin_stt.backends.registry import resolve,build_backend
from soorin_stt.audio.decoder import decode_audio
from soorin_stt.models_cli import verify
from soorin_stt.text.persian_normalizer import normalize_text
from metrics import wer,cer

def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--output',required=True)
    args=p.parse_args();s=get_settings();spec=resolve(s);verify(spec.name)
    backend=build_backend(s,spec);backend.load();backend.warmup()
    rows=[]
    for line in Path(args.manifest).read_text(encoding='utf-8').splitlines():
        if not line.strip():continue
        row=json.loads(line);audio=decode_audio(Path(row['audio']).read_bytes(),s.audio_sample_rate,s.audio_max_seconds)
        started=time.monotonic();hyp=backend.transcribe(audio,s.audio_sample_rate).text;dt=time.monotonic()-started
        ref=normalize_text(row['reference'])[0];hyp=normalize_text(hyp)[0]
        rows.append({'audio':row['audio'],'reference':ref,'hypothesis':hyp,'wer':wer(ref,hyp),'cer':cer(ref,hyp),'rtf':dt/max(len(audio)/s.audio_sample_rate,.001)})
    backend.close()
    output={'model':spec.name,'n':len(rows),'mean_wer':sum(r['wer'] for r in rows)/max(len(rows),1),
            'mean_cer':sum(r['cer'] for r in rows)/max(len(rows),1),'items':rows}
    Path(args.output).parent.mkdir(parents=True,exist_ok=True)
    Path(args.output).write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in output.items() if k!='items'},indent=2))
if __name__=='__main__':main()
