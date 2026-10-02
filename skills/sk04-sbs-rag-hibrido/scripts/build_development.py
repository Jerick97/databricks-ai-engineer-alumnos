"""Build only development data/input inventory; no vector/provider capability."""
from pathlib import Path
import argparse,json
from sbs.retrieval.development import write_dataset
parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=Path.cwd());parser.add_argument('--output',type=Path,required=True)
a=parser.parse_args();manifest,artifacts=write_dataset(a.root,a.output)
print(json.dumps({k:v for k,v in manifest.items() if k not in ('source_files','cache_provenance')},ensure_ascii=False,indent=2))
