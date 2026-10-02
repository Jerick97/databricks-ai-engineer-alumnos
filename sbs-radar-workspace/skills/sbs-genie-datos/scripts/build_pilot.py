#!/usr/bin/env python3
"""Generate reviewable pilot002 artifacts offline; never publish or start resources."""
import argparse
from pathlib import Path
import sys

root_default=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(root_default/'src'))
from sbs.genie.pilot import export_pilot_002

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=root_default)
    args=parser.parse_args()
    result=export_pilot_002(args.root)
    print('snapshot='+result['bundle']['snapshot_hash'])
    print('rows='+str({t:len(rows) for t,rows in result['bundle']['tables'].items()}))
    print('status=local_only_cloud_resources_pending')
