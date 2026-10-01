"""Offline Linux/app/CPU smoke from a copied, limited snapshot; no provider calls."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import platform
import shutil
import sys
import tempfile
import time


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--baseline',type=Path)
    parser.add_argument('--require-amd64',action='store_true')
    args=parser.parse_args()
    result={'platform':platform.system(),'machine':platform.machine(),'python':platform.python_version(),
            'network':'disabled_by_container_when_amd64','provider_inference_calls':0,'weights_downloaded':False,
            'quality_claim':False,'numeric_tolerance_absolute':0.001,'status':'started'}
    stage='copy_snapshot';started=time.perf_counter()
    try:
        if args.require_amd64 and (platform.system()!='Linux' or platform.machine() not in ('x86_64','amd64')):
            raise ValueError('amd64_emulation_unavailable')
        with tempfile.TemporaryDirectory(prefix='sbs-verify-') as tmp:
            project=Path(tmp)/'project';shutil.copytree(args.root,project,symlinks=False)
            sys.path.insert(0,str(project/'src'))
            stage='runtime_catalog'
            from sbs.runtime import LocalService
            service=LocalService(mode='cloud')
            catalog=service.catalog()
            assert len(service.sources)==6 and len(catalog['pairs'])==2
            selected=[('cyber-504','art20.3'),('market-3274','art27'),('market-3274','art29.1.4')]
            for pair,provision in selected:
                output=service.comparison(pair,provision)
                assert len(output['citations'])==2 and output['before']['text'] and output['after']['text']
            assert service.generator is None and service.embedding is None
            result['app']={'source_count':len(service.sources),'pair_count':len(catalog['pairs']),'comparisons':3,'provider_models_initialized':False}
            stage='structural_diffs'
            from sbs.comparison.pilot import build_pilot
            pilot=build_pilot(project)
            assert len(pilot['items'])==3
            assert all(i['changes'] and i['change_set']['evidence']['coverage']=='partial' for i in pilot['items'])
            result['structural_diffs']=3
            stage='model_load'
            from sbs.paths import resolve_model_manifest
            from sbs.models.reranker import LocalOnnxReranker
            manifest=json.loads((project/'context/reranker-manifest.json').read_text())
            resolved=resolve_model_manifest(manifest,root=project)
            reranker=LocalOnnxReranker.from_manifest(resolved,cpu_threads=2)
            result['providers']=reranker.session.get_providers()
            assert result['providers']==['CPUExecutionProvider']
            result['weights']={k:v['sha256'] for k,v in resolved['files'].items()}
            stage='local_rerank'
            sample=pilot['items'][0]
            rows=[{'citation':sample[side]} for side in ('before','after')]
            query='¿Quién responde por las operaciones digitales no reconocidas?'
            scores=reranker(query,rows)
            assert len(scores)==2 and all(math.isfinite(x) for x in scores)
            result['scores']=scores
            result['smoke_input_sha256']=hashlib.sha256(json.dumps([query,rows],sort_keys=True,ensure_ascii=False).encode()).hexdigest()
            result['pair_token_counts']=[t['windows'][0]['pair_tokens'] for t in reranker.last_trace]
            stage='numeric_comparison'
            if args.baseline:
                baseline=json.loads(args.baseline.read_text())
                assert baseline['smoke_input_sha256']==result['smoke_input_sha256'] and baseline['weights']==result['weights']
                result['absolute_deltas']=[abs(a-b) for a,b in zip(scores,baseline['scores'])]
                result['numeric_smoke_passed']=all(d<=result['numeric_tolerance_absolute'] for d in result['absolute_deltas'])
                if not result['numeric_smoke_passed']:raise ValueError('numeric_smoke_tolerance_exceeded')
            result['status']='passed';result['stage']='completed'
    except Exception as exc:
        result.update(status='failed',stage=stage,error_type=type(exc).__name__)
    result['elapsed_seconds']=time.perf_counter()-started
    for file in ('wheel-sha256.txt','installed.txt'):
        p=Path('/verify')/file
        if p.is_file():shutil.copyfile(p,args.output.parent/('sk12-linux-'+file))
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    return 0 if result['status']=='passed' else 1

if __name__=='__main__':raise SystemExit(main())
