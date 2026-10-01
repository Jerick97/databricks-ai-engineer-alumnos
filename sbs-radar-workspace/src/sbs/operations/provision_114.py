"""Additive106 HEAD404 compatibility correction. No frozen bytes/journal migration.

Files HEAD has no JSON error body. For the exact bootstrap directory only,
HTTP404 is normalized to106's local missing-resource sentinel. This is not a
provider error_code observation. All other methods, paths and statuses propagate.
"""
from pathlib import Path
import json,time
from . import exclusive_lock
from .cloud_dispatch import require
from . import provision_106 as base

class Head404Api:
 def __init__(self,original,*,expected_directory):
  self.original=original;self.path='/api/2.0/fs/directories'+expected_directory
 def __getattr__(self,name):return getattr(self.original,name)
 def do(self,method,path=None,**kwargs):
  try:return self.original.do(method,path,**kwargs)
  except base.RemoteError as error:
   if method=='HEAD' and path==self.path and error.status==404 and error.code=='UNCLASSIFIED':
    corrected=base.RemoteError(404,'RESOURCE_DOES_NOT_EXIST')
    corrected.normalization='local_missing_directory_sentinel_from_exact_HEAD_404'
    raise corrected from None
   raise

def patch_inputs(root):
 root=Path(root)
 names=['src/sbs/operations/provision_114.py','runs/sk11-files-head-114.json','runs/sk11-provision-106-freeze.json']
 return {name:base.sha((root/name).read_bytes()) for name in names}

class Provisioner114(base.Provisioner):
 def __init__(self,root,journal,review,patch_review,**kwargs):
  self.patch_review=patch_review;self.patch_root=Path(root).resolve()
  require(patch_review.get('files')==patch_inputs(self.patch_root),'PATCH_REVIEW_INPUTS_REQUIRED')
  state=Path(journal).resolve()
  require((state/'budget.json').is_file() and (state/'policy.json').is_file() and all(len(list((state/stage).glob('*.observed.json')))==1 for stage in ('table','seed','control_acl')),'EXISTING_106_JOURNAL_REQUIRED')
  super().__init__(root,journal,review,**kwargs)
  # Only Files serializer requests pass through the compatibility wrapper.
  # Original ScopedApi, permit, session, quota, authorization and state are shared.
  self.files._api=Head404Api(self.api,expected_directory=self.prefix)
 def authorize(self):
  r=self.patch_review;now=int(time.time()*1000)
  require(r.get('approved') is True and r.get('scope')=='provision114_head404' and r.get('writer_mode')==self.mode and r.get('limits')==base.LIMITS,'PATCH_REVIEW_REQUIRED')
  require(type(r.get('issued_at_ms')) is int and type(r.get('expires_at_ms')) is int and r['issued_at_ms']<=now<r['expires_at_ms'] and 0<r['expires_at_ms']-r['issued_at_ms']<=1800000,'PATCH_WINDOW_REQUIRED')
  for name,pin in r['files'].items():require(base.sha((self.patch_root/name).read_bytes())==pin,'PATCH_INPUT_DRIFT')
  super().authorize()

def preflight(root):
 result=base.preflight(root)
 evidence=base.safe_json(Path(root)/'runs/sk11-files-head-114.json')
 package=base.safe_json(Path(root)/'runs/sk12-writer-portable-105.json')
 require(evidence.get('http_status')==404 and evidence.get('body_bytes')==0 and evidence.get('path')==base.PREFIX+'/bootstrap106/'+package['archive_sha256'],'HEAD_DIAGNOSIS_BINDING_REQUIRED')
 return {**result,'adapter':'provision114_exact_HEAD404','frozen106_preserved':True,'existing_journal_required':True,'patch_inputs':patch_inputs(root)}

def main():
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path.cwd());p.add_argument('--execute',action='store_true');p.add_argument('--review-file',type=Path);p.add_argument('--patch-review-file',type=Path);p.add_argument('--journal',type=Path);p.add_argument('--profile');p.add_argument('--writer-mode',choices=['preflight','execute'],default='preflight');a=p.parse_args()
 if not a.execute:print(json.dumps(preflight(a.root)));return
 require(all(v is not None for v in (a.review_file,a.patch_review_file,a.journal)),'REVIEW_PATCH_AND_EXISTING_JOURNAL_REQUIRED')
 preflight(a.root)
 review=base.safe_json(a.review_file);patch=base.safe_json(a.patch_review_file)
 with exclusive_lock(a.journal):
  executor=Provisioner114(a.root,a.journal,review,patch,profile=a.profile,writer_mode=a.writer_mode)
  try:print(json.dumps(executor.run()))
  finally:executor.api.session.close()
if __name__=='__main__':main()
