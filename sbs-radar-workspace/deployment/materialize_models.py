"""Copy exact pinned artifacts from an explicit local HF cache; never download."""
import argparse
import json
from pathlib import Path
import shutil
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from sbs.paths import resolve_model_manifest,model_relative_path,project_path,file_sha256


def materialize(root,cache_root):
    root=Path(root).resolve(); output={'status':'materialized_local_only','downloads':0,'artifacts':[],'manifests':{}}
    for label,relative in [('reranker','context/reranker-manifest.json'),('embedding_tokenizer','runs/sk05-qwen-tokenizer.json')]:
        original=json.loads((root/relative).read_text())
        resolved=resolve_model_manifest(original,root=root,cache_root=cache_root)
        for name,artifact in resolved['files'].items():
            target=project_path(root,model_relative_path(original,name)); target.parent.mkdir(parents=True,exist_ok=True)
            if not target.exists():
                with Path(artifact['path']).open('rb') as source,target.open('xb') as destination:shutil.copyfileobj(source,destination)
            if file_sha256(target)!=artifact['sha256']:raise ValueError('materialized_hash_mismatch')
            output['artifacts'].append({'path':str(target.relative_to(root)),'sha256':artifact['sha256'],'bytes':target.stat().st_size})
        # Sidecar is relocation metadata, not replacement of the sealed historical manifest.
        output['manifests'][label]={'path':relative,'sha256':file_sha256(root/relative),'revision':original['revision'],'repo_id':original['repo_id']}
    target=root/'data/models/manifest.json'; serialized=json.dumps(output,indent=2)+'\n'
    if target.exists() and target.read_text()!=serialized:raise ValueError('model_materialization_manifest_conflict')
    if not target.exists():target.write_text(serialized)
    return output

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);parser.add_argument('--cache-root',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(materialize(args.root,args.cache_root),indent=2))
