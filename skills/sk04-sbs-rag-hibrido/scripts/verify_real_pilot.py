"""Verify persisted real pipeline without inference, source edits, or new resources."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from run_real_pilot import ROOT,D,RUN,read,sha,file_sha,unseal,write
from sbs.models import ModelManifest
from sbs.retrieval import LocalIndex
from sbs.evaluation import retrieval_metrics
from sbs.contracts import validate_contract

report=read(ROOT/'runs'/f'{RUN}-report.json')
for p,digest in report['artifacts_sha256'].items(): assert file_sha(ROOT/p)==digest
protocol=unseal(ROOT/'runs'/f'{RUN}-protocol.json'); assert sha(protocol)==report['protocol_sha256']
bundle=read(ROOT/'config/pilot-model-bundle.json'); manifest=ModelManifest.from_bundle(bundle['bundle'])
assert manifest.bundle_hash==bundle['bundle_hash']==report['bundle_hash']
records=read(D/'records.json'); index_data=unseal(D/'index.json')
index=LocalIndex(records,index_data['vectors'],dimension=manifest.bundle['dimension'],model_identity=manifest.bundle_hash,actual_identity=manifest.bundle_hash)
assert index.index_hash==report['index_hash']==index_data['index_hash']
byid={r['citation']['citation_id']:r for r in records}
source_runs=[read(ROOT/'runs/sk02-repository-capture.json'),read(ROOT/'runs/sk02-amendments-capture.json')]
raw={s['source']['version_id']:Path(s['rawtext_path']).read_text() for run in source_runs for s in run['sources']}
for r in records:
 c=r['citation']; assert raw[c['version_id']][c['start']:c['end']]==c['text']
assert len(records)==135
batchfiles=sorted(D.glob('doc-[0-9][0-9][0-9].json'))+[D/'queries-000.json']
assert len(batchfiles)==18
vectors=[]; usages=[]
for p in batchfiles:
 b=unseal(p); assert b['bundle_hash']==manifest.bundle_hash
 assert b['model']==manifest.bundle['parameters']['expected_response_model']
 assert len(b['embeddings'])<=8 and not b['server_usage_exceeds_reserve']
 usages.append(b['usage']['prompt_tokens'])
 if b['role']=='document': vectors.extend(b['embeddings'])
 assert (ROOT/'runs'/f'{RUN}-protocol.json').stat().st_mtime <= p.with_name(p.stem+'-attempt.json').stat().st_mtime
assert vectors==index_data['vectors']
results={}
for q in protocol['questions']:
 item=unseal(ROOT/'runs'/f"{RUN}-{q['query_id']}.json")
 assert validate_contract('EvidencePack',item['result']['evidence'])['valid']
 for c in item['result']['evidence']['citations']: assert c['text']==raw[c['version_id']][c['start']:c['end']]
 for name,key in [('lexical','lexical'),('vector','vector'),('rrf','fusion'),('rrf_rerank','reranked')]:
  computed=retrieval_metrics([r[0] for r in item['result']['trace'][key]],protocol['qrels'][q['query_id']],5,protocol['counterparts'][q['query_id']])
  assert computed==item['metrics_top5_before_expansion'][name]
 for (cid,_),trace in zip(item['result']['trace']['fusion'],item['reranker_windows']):
  text=byid[cid]['citation']['text']; cursor=0
  for w in trace['windows']:
   assert w['start']==cursor and w['pair_tokens']<=512
   cursor=w['end']
  assert cursor==len(text)
  assert max(w['score'] for w in trace['windows'])==trace['score']
 results[q['query_id']]={'family':q['family'],'citable_output_count':len(item['result']['evidence']['citations']),'reranked_candidates':len(item['reranker_windows']),'local_rerank_inference_seconds':sum(w['inference_seconds'] for t in item['reranker_windows'] for w in t['windows']),'metrics_verified':True}
verification={'run_id':RUN,'status':'passed_offline_artifact_integrity_and_recomputed_metrics','inference_calls_this_verification':0,'original_inference_calls':len(batchfiles),'original_prompt_tokens_observed':sum(usages),'original_reserved_tokens':report['reserved_tokens'],'real_models':True,'index_records':len(records),'query_checks':results,'protocol_before_inference_verified':True,'original_cost':None,'acceptance':'not_evaluated','report_sha256':file_sha(ROOT/'runs'/f'{RUN}-report.json'),'run_script_sha256':file_sha(Path(__file__).with_name('run_real_pilot.py')),'limitations':'Integrity and metrics verification; does not authenticate legal truth or certify exhaustive relevance.'}
write(ROOT/'runs'/f'{RUN}-verification.json',verification)
print(json.dumps(verification,ensure_ascii=False,indent=2))
