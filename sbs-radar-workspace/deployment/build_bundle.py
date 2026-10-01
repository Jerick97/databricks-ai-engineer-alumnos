"""Create a reviewable project snapshot, never deploy it or include credentials."""
import argparse
import io
import hashlib
import json
import tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
# Explicit roots: excludes .git, home files, caches, environment and downloaded model weights.
ROOTS=['web','src','contracts','config','context','skills','docs','notebooks','deployment','tests','data/foundation-repository','data/foundation-holdout','data/retrieval','runs/sk06-pilot-002','runs/sk06-component-real']
FILES=['app.py','pyproject.toml','requirements.txt','AGENTS.md','STATE.md','runs/sk12-execute-runtime-notebook.py','runs/sk03-map-compaction-027-before/structural.py']
RUN_PATTERNS=['sk02-*-capture.json','sk03-pilot*.json','sk04-real-001*.json',
              'sk05-qwen-tokenizer.json','sk07-generation*.json','astra-normative-review*.json',
              'sk12-notebook*.json','sk12-notebook*-executed.ipynb',
              'sk12-refresh-notebook*.json','sk12-refresh-notebook*-executed.ipynb',
              'sk12-runtime-notebook*.json','sk12-runtime-notebook*-executed.ipynb',
              'sk11-cloud-driver-014-*.json','sk11-cloud-driver-014-*-executed.ipynb',
              'sk11-remote-refresh-015-notebook-*.json','sk11-remote-refresh-015-notebook-*-executed.ipynb',
              'sk06-publication-writer-016-*.json','sk06-publication-writer-016-*-executed.ipynb',
              'sk11-capture-recovery-016-record.json','sk09-capture-recovery-016-review.json',
              'e2e-acceptance-current.json',
              # Frozen fixtures required by the structural tests shipped in ROOTS.
              'sk03-market-018-inputs.json','sk02-structure-019-fix-before.json',
              'sk02-structure-019-fix-after.json','sk02-cyber-boundary-020-invocation.json',
              'sk05-workspace-preflight.json','sk12-phase-s-017.py',
              'sk12-uc-metadata-preflight-015.json','sk09-genie-publication-writer-016-review.json']
# Origin admission and journals are operational state, not portable configuration.
OPERATIONAL_PATTERN='deployment/*-authorization.json'
OPERATIONAL_TREE='deployment/state'
# Optional local development profile: fixed dependencies, not all runs/history.
STRUCTURAL_PROFILE_FILES=[
    'runs/sk04-embeddings-041-vectors/vectors.json',
    'runs/sk04-structural-ranking-047-v2/index.json',
    'runs/sk04-structural-ranking-047-v2/record.json',
    'runs/sk04-structural-ranking-047-v2/records.json',
    'runs/sk05-query-compatibility-046.json',
    'runs/sk07-runtime-structural-049-config.json',
    'runs/sk09-query-compatibility-046-review.json',
]
def selected_paths(include_models=False, *, include_structural_profile=False):
    """Select portable files without reading payloads or writing an archive."""
    paths=set()
    for name in ROOTS + (['data/models'] if include_models else []):
        paths.update(p for p in (ROOT/name).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')
    paths.update(ROOT/name for name in FILES if (ROOT/name).is_file())
    for pattern in RUN_PATTERNS: paths.update((ROOT/'runs').glob(pattern))
    if include_structural_profile:
        for name in STRUCTURAL_PROFILE_FILES:
            path=ROOT/name
            if not path.is_file():raise ValueError('STRUCTURAL_PROFILE_FILE_MISSING')
            paths.add(path)
    # IAM metadata executor is intentionally outside this runtime snapshot.
    paths.discard(ROOT/'tests/unit/test_writer_create_016b.py')
    for path in paths:
        if not path.resolve().is_relative_to(ROOT) or path.is_symlink(): raise ValueError('Outside path or symlink in bundle')
    # The deployment root is the namespace for live admission capabilities.
    # Templates, plans and explicitly archived history retain their identities.
    return {p for p in paths
            if not (p.relative_to(ROOT).parent==Path('deployment') and p.name.endswith('-authorization.json'))
            and not p.relative_to(ROOT).is_relative_to(OPERATIONAL_TREE)}

def build(include_models=False, *, include_structural_profile=False):
    paths=selected_paths(include_models=include_models,include_structural_profile=include_structural_profile)
    # One immutable byte snapshot per file feeds both digest and tar payload.
    # Callers still freeze related source files to obtain a coherent release.
    snapshots={str(p.relative_to(ROOT)):p.read_bytes() for p in sorted(paths)}
    manifest={'status':'review_snapshot_not_deployed','format':'full_source_tree','files':{name:hashlib.sha256(raw).hexdigest() for name,raw in snapshots.items()},'models_included':include_models,'structural_profile_included':include_structural_profile,'structural_profile_scope':'Optional local exposed-development049 only; not activated or quality-approved','model_scope':'Materialized pilot artifacts; experimental candidate manifests do not imply their weights are bundled','excluded':[OPERATIONAL_PATTERN,OPERATIONAL_TREE+'/', 'credentials','.git','home caches','runs/sk12-writer-create-016b.py','tests/unit/test_writer_create_016b.py']+([] if include_models else ['downloaded model weights']),'limitations':['Snapshot of current files; final app release requires re-build after runtime changes','Remote inference dependencies and authenticated deployment not provisioned']}
    suffix=('-models' if include_models else '')+('-structural' if include_structural_profile else '')
    target=ROOT/'runs'/f'sk12-review-bundle{suffix}.tar.gz'
    with tarfile.open(target,'w:gz') as archive:
        for name,raw in snapshots.items():
            entry=tarfile.TarInfo('sbs-radar/'+name)
            entry.size=len(raw);entry.mode=0o644
            archive.addfile(entry,io.BytesIO(raw))
    (ROOT/'runs'/f'sk12-release-manifest{suffix}.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'files':len(paths),'bundle':str(target.relative_to(ROOT)),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'bytes':target.stat().st_size}))
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--include-models',action='store_true')
    parser.add_argument('--include-structural-profile',action='store_true',help='Include pinned local development049 inputs; does not activate runtime')
    args=parser.parse_args()
    build(include_models=args.include_models,include_structural_profile=args.include_structural_profile)
