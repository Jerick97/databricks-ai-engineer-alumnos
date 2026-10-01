"""Prepare separate diagnostic source; no release-gate change or cloud call."""
from pathlib import Path
import argparse,hashlib,json,shutil,time,importlib.util
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def prepare(destination,*,root=ROOT,expires_at=0):
    root=Path(root);dest=Path(destination)
    if type(expires_at) is not int or expires_at!=0 and not time.time()<expires_at<=time.time()+1800:raise ValueError('CANARY141_WINDOW_INVALID')
    stage=root/'runs/sk12-app-133-source-v3';manifest=json.loads((stage/'manifest.json').read_bytes())
    if manifest['source_sha256']!='afa0e1a63851af5d8419a2af16ef674d1602f65d06de1edd254cf1a18388a432':raise ValueError('CANARY141_BASE_SOURCE_CHANGED')
    dest.mkdir(parents=True,exist_ok=False);source=dest/'source';source.mkdir()
    for p,h in manifest['files_sha256'].items():
        original=stage/'source'/p
        if Path(p).is_absolute() or '..' in Path(p).parts or original.is_symlink() or sha(original)!=h:raise ValueError('CANARY141_INPUT_DRIFT')
        target=source/p;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(original,target)
    def add(p,raw):
        target=source/p;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as f:f.write(raw)
    add('deployment/requirements-app.txt',(root/'runs/sk12-linux-installed.txt').read_bytes())
    add('canary141.py',(root/'deployment/linux_canary_141.py').read_bytes())
    add('canary133-manifest.json',(stage/'manifest.json').read_bytes())
    add('canary141-numeric-baseline.json',(root/'runs/sk12-linux-baseline.json').read_bytes())
    add('canary141-config.json',json.dumps({'kind':'diagnostic_only_not_release','expires_at_unix':expires_at,'provider_calls':0,'source133_sha256':manifest['source_sha256']}).encode())
    app={'command':['python','canary141.py'],'env':[{'name':k,'value':v} for k,v in {'PYTHONDONTWRITEBYTECODE':'1','PYTHONUNBUFFERED':'1','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','TOKENIZERS_PARALLELISM':'false','OMP_NUM_THREADS':'2'}.items()]}
    add('app.yaml',json.dumps(app,indent=2).encode())
    files={p.relative_to(source).as_posix():sha(p) for p in source.rglob('*') if p.is_file()}
    out={'kind':'prepared_linux_canary_not_release','expires_at_unix':expires_at,'source133_sha256':manifest['source_sha256'],'files_sha256':files,'source_sha256':hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'root_requirements_unchanged':True,'linux_verified':False,'quality_accepted':False}
    (dest/'manifest.json').write_text(json.dumps(out,indent=2)+'\n');return out
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--destination',required=True);p.add_argument('--expires-at-unix',type=int,default=0);a=p.parse_args();out=prepare(a.destination,expires_at=a.expires_at_unix);print(json.dumps({k:v for k,v in out.items() if k!='files_sha256'},indent=2))
