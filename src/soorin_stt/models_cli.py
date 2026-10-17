from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
from soorin_stt.core.config import get_settings
from soorin_stt.backends.registry import catalog,resolve,local_dir

MANIFEST='.soorin-model.json'

def hash_file(path:Path)->str:
    digest=hashlib.sha256()
    with path.open('rb') as src:
        for chunk in iter(lambda:src.read(1024*1024),b''):
            digest.update(chunk)
    return digest.hexdigest()

def verify(name:str|None=None):
    s=get_settings();models=catalog(s.stt_catalog_dir)
    key=name or s.stt_model
    if key not in models: raise RuntimeError(f'Unknown model: {key}')
    spec=models[key];root=s.stt_model_dir/key
    metadata=root/MANIFEST
    if spec.backend=='vosk':
        if not (root/'am').exists(): raise RuntimeError(f'Unpack an official Vosk model into {root}')
        return {'repo':'manual-vosk', 'revision':'manual', 'files':{}}
    if not metadata.is_file():
        raise RuntimeError(f'Missing model manifest {metadata}. Run: soorin-models download --model {key}')
    meta=json.loads(metadata.read_text())
    if meta['repo']!=spec.repo:
        raise RuntimeError('Catalog/model repo mismatch')
    if s.stt_model_revision and s.stt_model_revision != meta.get('revision'):
        raise RuntimeError('Local model revision does not match STT_MODEL_REVISION')
    if not meta.get('revision') or len(meta['revision'])<20:
        raise RuntimeError('Model revision not pinned')
    for name, expected in meta['files'].items():
        path=root/name
        if not path.is_file() or (s.stt_verify_hashes and hash_file(path)!=expected):
            raise RuntimeError(f'Corrupted/missing model file {path}')
    for name in spec.artifacts.values():
        if not (root/name).exists():
            raise RuntimeError(f'Missing required artifact {root/name}')
    return meta

def download(name:str|None=None,revision:str=''):
    s=get_settings();models=catalog(s.stt_catalog_dir)
    key=name or s.stt_model
    spec=models[key]
    if spec.status=='research-only':
        raise RuntimeError('Research-only model has no verified inference runtime')
    if spec.license.lower() in {'cc-by-nc-4.0','cc-by-nc','noncommercial'} and not s.stt_allow_noncommercial:
        raise RuntimeError('Model is noncommercial: set STT_ALLOW_NONCOMMERCIAL=true for authorized R&D ONLY')
    if not spec.repo:
        raise RuntimeError(f'{key} needs a manual model import, see catalog and README')
    from huggingface_hub import HfApi,snapshot_download
    info=HfApi().model_info(spec.repo,revision=revision or spec.revision or None)
    sha=info.sha
    card=getattr(info, 'card_data', None)
    declared=card.get('license', '') if isinstance(card, dict) else ''
    if declared and spec.license.lower() not in {'unknown', declared.lower()}:
        raise RuntimeError(f'Model license changed: catalog={spec.license} upstream={declared}. Manual review required.')
    if not sha or len(sha)<20: raise RuntimeError('Unable to resolve immutable HF revision')
    root=s.stt_model_dir/key
    root.mkdir(parents=True,exist_ok=True)
    print(f'Downloading {spec.repo}@{sha} -> {root}')
    snapshot_download(repo_id=spec.repo,revision=sha,local_dir=root,
                      allow_patterns=spec.allow_patterns or None)
    files={}
    for path in root.rglob('*'):
        if path.is_file() and path.name!=MANIFEST and '.cache' not in path.parts:
            files[str(path.relative_to(root))]=hash_file(path)
    for artifact in spec.artifacts.values():
        if not (root/artifact).is_file():
            raise RuntimeError(f'Expected artifact absent: {root/artifact}')
    meta={'repo':spec.repo,'revision':sha,'license':spec.license,'model_key':key,'files':files}
    (root/MANIFEST).write_text(json.dumps(meta,indent=2,ensure_ascii=False)+'\n')
    print(f'Pinned {sha}; verified {len(files)} downloaded files')
    return meta

def main():
    p=argparse.ArgumentParser(description='Soorin model catalog and reproducible downloader')
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('list')
    d=sub.add_parser('download');d.add_argument('--model');d.add_argument('--revision',default='')
    v=sub.add_parser('verify');v.add_argument('--model')
    a=p.parse_args()
    if a.command=='list':
        for key,spec in catalog(get_settings().stt_catalog_dir).items():
            print(f'{key:37} {spec.backend:25} {spec.license:16} {spec.status}')
    elif a.command=='download': print(json.dumps(download(a.model,a.revision),indent=2))
    else: print(json.dumps(verify(a.model),indent=2))
if __name__=='__main__':main()
