"""Independent phase S. Default local preflight; optional bounded authorized warehouse start.

Authorization file is trusted server input transcribing actual SQL/start/time authorization, not a browser request or self-authenticating proof.
"""
from pathlib import Path
import argparse,hashlib,json,os,re,sys,time,uuid
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from sbs.genie.publication_writer import load_write_plan,WriterConfig,sdk_writer
from sbs.genie.publication import require
from sbs.paths import project_path

def sync_directory(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:os.fsync(fd)
    finally:os.close(fd)

def sha(raw):return hashlib.sha256(raw).hexdigest()
def load(root):
    root=Path(root).resolve();raw=(root/'deployment/phase-s-017.json').read_bytes();c=json.loads(raw)
    require(c['version']==1 and c['phase']=='S' and c['profile']=='databricks-ai-engineer-aws','PHASE_CONFIG_INVALID')
    require(c['start_warehouse'] is False and all(c[k] is False for k in ('requires_genie_space','requires_job','requires_app')),'PHASE_SCOPE_INVALID')
    require(c['writer']['evidence_mode']=='real' and c['writer']['max_http_calls']==512 and c['writer']['host']=='https://dbc-0410b264-20c7.cloud.databricks.com','PHASE_WRITER_INVALID')
    for p,h in c['inputs'].items():require(sha(project_path(root,p).read_bytes())==h,'PHASE_INPUT_DRIFT')
    me=json.loads(project_path(root,'runs/sk12-uc-metadata-preflight-015.json').read_bytes())['observations']['me']
    schema=json.loads(project_path(root,'deployment/uc-observed-015.json').read_bytes())['schema']
    w=c['writer'];require(type(w['executor_id']) is int and str(w['executor_id'])==me['id'] and w['owner']==me['userName']==schema['owner'] and w['schema_id']==schema['id'] and w['schema_name']==schema['full_name'],'PHASE_OBSERVED_IDENTITY_MISMATCH')
    require(w['warehouse_id']=='828756322bedff37' and w['plan_sha256']==c['inputs']['runs/sk06-publication-writer-016-plan.json'],'PHASE_RESOURCE_PIN_MISMATCH')
    plan=load_write_plan(root,publication_id=c['publication_id']);require(plan.sha256==w['plan_sha256'],'PHASE_PLAN_MISMATCH')
    require(c['state_root']=='deployment/state/phase-s-017' and type(c['max_window_ms']) is int and 300000<c['max_window_ms']<=3600000,'PHASE_STATE_OR_WINDOW_INVALID')
    require(c['server_policy_profile']=='trusted_admin_observed_v1' and c['policy_selected_by']=='server_executor' and c['policy_user_attestation'] is False,'PHASE_SERVER_PROFILE_INVALID')
    require(set(c['server_policy_assumptions_unobserved'])=={'trusted_administrators','exclusive_maintenance','retention','no_inherited_abac'} and all(isinstance(v,str) and v for v in c['server_policy_assumptions_unobserved'].values()),'PHASE_DECLARATIONS_INVALID')
    return root,c,sha(raw),plan

def preflight(root):
    root,c,h,plan=load(root)
    return dict(status='pending_sql_start_authorization',configuration_sha256=h,plan_sha256=plan.sha256,executor_id=c['writer']['executor_id'],owner=c['writer']['owner'],warehouse_id=c['writer']['warehouse_id'],schema_id=c['writer']['schema_id'],state_root=c['state_root'],requires_genie_space=False,requires_job=False,requires_app=False,remote_calls=0,starts_warehouse=False,optional_start_requires_same_phase_authorization=True,activity_http_cap_separate=5,cost=None,sql_success_path=80,sql_cap_per_instance=112,http_cap_per_instance=512,observations_are_historical=True,pending=['one publication SQL cost authorization; no monetary ceiling inferred','warehouse RUNNING re-observed by publisher; optional single-attempt start under same phase authorization, no automatic shared stop'])

def authorize(c,config_sha,a,now):
    require(isinstance(a,dict) and set(a)=={'status','phase','configuration_sha256','approved_by','accept_sql_cost_unknown','issued_at_ms','expires_at_ms','warehouse_running_observation_required','allow_start_if_stopped'},'PHASE_AUTHORIZATION_SHAPE')
    require(a['status']=='approved' and a['phase']=='S' and a['configuration_sha256']==config_sha and a['approved_by']==c['writer']['owner'],'PHASE_AUTHORIZATION_REQUIRED')
    require(type(a['allow_start_if_stopped']) is bool,'PHASE_START_DECISION_REQUIRED')
    require(a['accept_sql_cost_unknown'] is True and a['warehouse_running_observation_required'] is True,'PHASE_ACCEPTANCE_REQUIRED')
    require(type(a['issued_at_ms']) is int and type(a['expires_at_ms']) is int and a['issued_at_ms']<=now<a['expires_at_ms'] and 300000<a['expires_at_ms']-now and a['expires_at_ms']-a['issued_at_ms']<=c['max_window_ms'],'PHASE_AUTHORIZATION_WINDOW_INVALID')
    return WriterConfig(**c['writer'],policy={**c['server_policy_assumptions_unobserved'],'issued_at_ms':a['issued_at_ms'],'expires_at_ms':a['expires_at_ms']})

class WarehouseActivity:
    """Narrow, single-attempt GET warehouse / POST start only. No stop/delete.
    Separate cap: at most four GETs and one POST, 32KiB/response, 160KiB total.
    """
    def __init__(self,cfg,warehouse_id):
        import requests
        self.cfg=cfg;self.path='/api/2.0/sql/warehouses/'+warehouse_id;self.id=warehouse_id
        self.session=requests.Session();self.session.trust_env=False
        require(all(a.max_retries.total==0 for a in self.session.adapters.values()),'ACTIVITY_RETRIES_DISABLED_REQUIRED')
        self.gets=0;self.posts=0;self.admit=lambda:None
    def call(self,method):
        if method=='POST':self.admit()
        if method=='GET':require(self.gets<4,'ACTIVITY_GET_CAP');self.gets+=1;path=self.path
        else:require(method=='POST' and self.posts==0,'ACTIVITY_POST_CAP');self.posts+=1;path=self.path+'/start'
        response=None
        try:
            headers=self.cfg.authenticate()
            if method=='POST':self.admit()
            response=self.session.request(method,self.cfg.host.rstrip('/')+path,headers=headers,json={} if method=='POST' else None,timeout=(5,20),allow_redirects=False,stream=True)
            raw=response.raw.read(32769,decode_content=True);require(len(raw)<=32768,'ACTIVITY_RESPONSE_CAP')
            require(200<=response.status_code<300,'ACTIVITY_HTTP_UNCONFIRMED')
            d=json.loads(raw) if raw else {};require(isinstance(d,dict),'ACTIVITY_RESPONSE_INVALID')
            if method=='GET':require(d.get('id')==self.id,'ACTIVITY_WAREHOUSE_ID_MISMATCH')
            return d
        except Exception:raise ValueError('ACTIVITY_REQUEST_UNCONFIRMED') from None
        finally:
            if response is not None:
                try:response.close()
                except Exception:pass
    def close(self):self.session.close()

def ensure_running(activity,state,*,allow_start,sleep=time.sleep,admit=lambda:None):
    before=activity.call('GET');prior=state/'warehouse-start-intent.json'
    if before.get('state')=='RUNNING':return dict(state='RUNNING',start_requested=False,prior_start_intent=prior.exists(),auto_stop_mins=before.get('auto_stop_mins'),shared_warehouse=True,automatic_stop=False)
    if before.get('state')=='STOPPED':
        require(allow_start is True,'WAREHOUSE_START_NOT_AUTHORIZED');admit()
        # Exclusive reservation forbids blind resubmission after ambiguous start.
        fd=os.open(prior,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'w') as f:json.dump(dict(status='start_intent',warehouse_id=activity.id,at_ms=int(time.time()*1000)),f);f.flush();os.fsync(f.fileno())
        sync_directory(state)
        admit()
        try:activity.call('POST')
        except Exception:pass # only GET reconciliation below, never retry start
    else:require(before.get('state') in ('STARTING','STOPPING'),'WAREHOUSE_STATE_UNSUPPORTED')
    for _ in range(3):
        sleep(5);after=activity.call('GET')
        if after.get('state')=='RUNNING':return dict(state='RUNNING',start_requested=before.get('state')=='STOPPED',prior_start_intent=prior.exists(),creation_attribution='not_claimed',auto_stop_mins=after.get('auto_stop_mins'),shared_warehouse=True,automatic_stop=False)
    raise ValueError('WAREHOUSE_TRANSITION_PENDING_NO_RETRY')


class AdmissionConfig:
    """Check after normal SDK authentication, immediately before HTTP dispatch.
    The wrapper also refuses new GETs after expiry; in-flight requests are not
    cancelled. No credential/header is stored or returned as evidence.
    """
    def __init__(self,delegate,admit):self.delegate=delegate;self.admit=admit
    def authenticate(self):
        headers=self.delegate.authenticate();self.admit();return headers
    def __getattr__(self,name):return getattr(self.delegate,name)


class AdmissionStatements:
    """Close SQL admission at the authorized deadline; cannot cancel an already
    admitted statement or guarantee warehouse shutdown/zero idle charges.
    """
    def __init__(self,delegate,expires_at_ms,clock):self.delegate=delegate;self.expires_at_ms=expires_at_ms;self.clock=clock
    def execute_statement(self,**kwargs):
        require(self.clock()<self.expires_at_ms,'PHASE_SQL_ADMISSION_CLOSED')
        return self.delegate.execute_statement(**kwargs)
    def __getattr__(self,name):return getattr(self.delegate,name)


def execute(root,authorization,*,attempt_id='initial',config_factory=None,writer_factory=sdk_writer,activity_factory=None,clock=lambda:int(time.time()*1000)):
    root,c,h,plan=load(root);cfg=authorize(c,h,authorization,clock())
    require(isinstance(attempt_id,str) and re.fullmatch('[a-zA-Z0-9_-]{1,64}',attempt_id),'PHASE_ATTEMPT_ID_INVALID')
    # Future creation of protected local journal is not a cloud resource action.
    from sbs.genie.publication_registry import _directory
    state=root/c['state_root'];fd=_directory(state,True);os.close(fd)
    for directory in (state,*state.parents):sync_directory(directory)
    record=state/('attempt-'+attempt_id+'.json')
    r=dict(phase='S',status='started',configuration_sha256=h,plan_sha256=plan.sha256,authorization_sha256=sha(json.dumps(authorization,sort_keys=True).encode()),started_at_ms=clock(),warehouse_start_requested=None)
    def save(initial=False):
        if initial:
            f=os.open(record,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
            with os.fdopen(f,'w') as out:json.dump(r,out,indent=2);out.flush();os.fsync(out.fileno())
        else:
            tmp=state/('.pending-'+uuid.uuid4().hex)
            f=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
            with os.fdopen(f,'w') as out:json.dump(r,out,indent=2);out.flush();os.fsync(out.fileno())
            require(not record.is_symlink(),'PHASE_RECORD_SYMLINK');os.replace(tmp,record)
        sync_directory(state)
    save(True)
    try:
        if config_factory is None:
            from databricks.sdk.core import Config
            config_factory=Config
        sdk_config=config_factory(profile=c['profile'])
        require(sdk_config.host.rstrip('/')==cfg.host,'PHASE_SDK_HOST_MISMATCH')
        def admit():require(clock()<authorization['expires_at_ms'],'PHASE_EFFECT_ADMISSION_CLOSED')
        admit();sdk_config=AdmissionConfig(sdk_config,admit)
        activity=(activity_factory or WarehouseActivity)(sdk_config,cfg.warehouse_id);activity.admit=admit
        try:r['warehouse_activity']=ensure_running(activity,state,allow_start=authorization['allow_start_if_stopped'],admit=admit)
        finally:activity.close()
        r['warehouse_start_requested']=r['warehouse_activity']['start_requested'];save()
        with writer_factory(plan,cfg,state/'journal',sdk_config=sdk_config) as writer:
            gated=AdmissionStatements(writer.statements,authorization['expires_at_ms'],clock)
            writer.statements=gated;writer.reader.sdk=gated
            result=writer.publish(certificate_directory=state/'certificates',registry_directory=state/'registry')
        r.update(status='published',result=result)
    except Exception:
        # Component preserves actionable journal; never persist provider secrets.
        r.update(status='incomplete',error_code='PHASE_PUBLICATION_UNCONFIRMED')
    finally:r['finished_at_ms']=clock();save()
    return r

def main():
    p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');p.add_argument('--authorization');p.add_argument('--attempt-id',default='initial');a=p.parse_args()
    if not a.execute:print(json.dumps(preflight(ROOT),indent=2));return 0
    require(a.authorization is not None,'PHASE_AUTHORIZATION_REQUIRED')
    authorization=json.loads(project_path(ROOT,a.authorization).read_bytes())
    result=execute(ROOT,authorization,attempt_id=a.attempt_id);print(json.dumps(result,indent=2));return 0 if result['status']=='published' else 1
if __name__=='__main__':raise SystemExit(main())
