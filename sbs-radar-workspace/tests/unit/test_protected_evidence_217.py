from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'runs/sk06-protected-evidence-217-overlay'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def test_three_file_hash_chain_only_prefix_and_pins_change():
 m=read(BASE/'manifest.json');assert len(m['files_sha256'])==3
 for n,h in m['base_files_sha256'].items():assert sha(ROOT/n)==h
 for n,h in m['files_sha256'].items():assert sha(BASE/'source'/n)==h
 server='config/genie-server-template-098.json';rotation='config/genie-rotation-098.json';bootstrap='config/genie-bootstrap-098.json'
 assert read(BASE/'source'/server)=={**read(ROOT/server),'evidence_prefix':m['evidence_prefix']}
 assert read(BASE/'source'/rotation)=={**read(ROOT/rotation),'server_template_sha256':sha(BASE/'source'/server)}
 assert read(BASE/'source'/bootstrap)=={**read(ROOT/bootstrap),'rotation_config_sha256':sha(BASE/'source'/rotation)}
def test_publisher_runtime_same_trust_binding_new_store_and_unchanged_ttls():
 pub=ROOT/'runs/sk06-protected-evidence-217-publisher';s=read(pub/'genie-server-publisher-217.json');r=read(pub/'genie-rotation-publisher-217.json');runtime=read(BASE/'source/config/genie-rotation-098.json')
 assert s=={**read(ROOT/'config/genie-server-068-proposal.json'),'evidence_prefix':read(BASE/'manifest.json')['evidence_prefix']}
 assert r['server_template_sha256']==sha(pub/'genie-server-publisher-217.json')
 assert ROOT/r['server_template_path']==pub/'genie-server-publisher-217.json'
 for key in ('snapshot_binding_sha256','policy_invariants_sha256','publisher_identity','publisher_executor_id','warehouse_id'):assert r[key]==runtime[key]
 assert s['policy_sha256']==read(ROOT/'config/genie-server-068-proposal.json')['policy_sha256']
def test_plan_preserves_job_writer_separates_volume_and_retains_sql():
 p=read(ROOT/'runs/sk06-protected-evidence-217-plan.json');assert p['create_body']['volume_type']=='MANAGED';assert p['mutation_caps']=={'volume_create':1,'add_read_grant':1,'sql':0,'warehouse_start':0,'app_start':0}
 assert p['grant_body']=={'changes':[{'principal':'a947eccf-5f94-4369-a3d4-8f83b4ea98a1','add':['READ_VOLUME']}]}
 assert p['forbidden_writer'] not in str(p['grant_body']);assert 'release_artifacts' not in p['prefix'];assert p['fresh_sql_consumed_before_next']==36 and p['aggregate_after_next']==69
