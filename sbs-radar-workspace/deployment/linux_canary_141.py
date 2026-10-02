"""Restricted Linux runtime diagnostic. Never serves chat or promotes App133."""
from pathlib import Path
from types import SimpleNamespace
from http.server import BaseHTTPRequestHandler,HTTPServer
import hashlib,importlib.metadata,json,math,os,platform,socket,sys,threading,time
PUBLIC_PATHS={'/health','/evidence'}
def check_expiry(value,*,now=None):
    now=time.time() if now is None else now
    if type(value) is not int or not now<value<=now+1800:raise ValueError('CANARY141_EXPIRED_OR_WINDOW_INVALID')
    return value

def require_platform(*,system=None,machine=None,python=None):
    system=platform.system() if system is None else system;machine=platform.machine() if machine is None else machine;python=sys.version_info[:2] if python is None else python
    if system!='Linux':raise ValueError('CANARY141_LINUX_REQUIRED')
    if tuple(python)!=(3,11):raise ValueError('CANARY141_PYTHON311_REQUIRED')
    if machine not in ('x86_64','amd64','aarch64','arm64'):raise ValueError('CANARY141_ARCHITECTURE_UNOBSERVED')
    return machine

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def validate_source(root):
    manifest=json.loads((root/'canary133-manifest.json').read_bytes());files=manifest['files_sha256']
    encoded=json.dumps(files,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
    if hashlib.sha256(encoded).hexdigest()!=manifest['source_sha256']:raise ValueError('CANARY141_MANIFEST_DRIFT')
    for p,h in files.items():
        target=root/p
        if Path(p).is_absolute() or '..' in Path(p).parts or target.is_symlink() or sha(target)!=h:raise ValueError('CANARY141_SOURCE_DRIFT')
    return manifest

def deny_connect(*a,**k):raise RuntimeError('CANARY141_OUTBOUND_NETWORK_FORBIDDEN')

def probe(root,expires_at):
    root=Path(root).resolve();check_expiry(expires_at);machine=require_platform();manifest=validate_source(root)
    sys.path.insert(0,str(root/'src'))
    socket.socket.connect=deny_connect;socket.socket.connect_ex=deny_connect;socket.create_connection=deny_connect
    from sbs.app133.runtime import AppService
    from sbs.app133.bootstrap import load_config
    from sbs.genie.bootstrap_098 import create_rotating_service,SELECTOR
    config=load_config(root)
    # Separate diagnostic authority, never writes or enables the133config.
    config['deadline_unix']=expires_at
    def deny(*a,**k):raise RuntimeError('CANARY141_PROVIDER_CALL_FORBIDDEN')
    client=SimpleNamespace(config=SimpleNamespace(host=config['workspace_host'],auth_type='oauth-m2m',client_id=config['reader_client_id'],authenticate=deny),files=SimpleNamespace(download=deny))
    def factory(**kwargs):return AppService(**kwargs).configure133(root,config,client_factory=lambda:client)
    service=create_rotating_service({'SBS_GENIE_ROTATION_CONFIG':SELECTOR},root=root,mode='cloud',service_factory=factory,client_factory=lambda:client)
    service.initialize_models()
    assert service.generator.requests==service.embedding.calls_attempted==0
    assert service.initialize_genie().readiness()['remote_verified'] is False
    actor={'authenticated':True,'subject':'canary141-local-diagnostic-fixture','role':'reader','families':['cybersecurity','market_conduct']}
    comparisons=[]
    for pair,provision in [('cyber-504','art20.3'),('market-3274','art27'),('market-3274','art29.1.4')]:
        item=service.for_actor(actor).comparison(pair,provision)
        assert item['before']['text'] and item['after']['text'];comparisons.append({'pair':pair,'provision':provision,'before_chars':len(item['before']['text']),'after_chars':len(item['after']['text'])})
    # Same diagnostic inputs as historical Linux smoke; do not switch weights.
    from sbs.comparison.pilot import build_pilot
    item=build_pilot(root)['items'][0];rows=[{'citation':item[s]} for s in ('before','after')]
    question='¿Quién responde por las operaciones digitales no reconocidas?'
    scores=service.reranker(question,rows)
    if len(scores)!=2 or not all(math.isfinite(x) for x in scores):raise ValueError('CANARY141_CPU_NONFINITE')
    input_sha=hashlib.sha256(json.dumps([question,rows],sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    baseline=json.loads((root/'canary141-numeric-baseline.json').read_bytes())
    same_input=input_sha==baseline['smoke_input_sha256']
    deltas=[abs(a-b) for a,b in zip(scores,baseline['scores'])] if same_input else None
    observed={}
    for line in (root/'deployment/requirements-app.txt').read_text().splitlines():
        if line and not line.startswith('#'):
            name,expected=line.split('==');value=importlib.metadata.version(name);observed[name]=value
            if value!=expected:raise ValueError('CANARY141_DEPENDENCY_DRIFT')
    return {'status':'PASS_LINUX_CANARY_RUNTIME_ONLY','platform':{'system':platform.system(),'machine':machine,'python':platform.python_version()},'source133_sha256':manifest['source_sha256'],'dependencies':observed,'cpu_execution':service.reranker.execution_identity,'comparisons':comparisons,'local_onnx_calls':1,'scores':scores,'smoke_input_sha256':input_sha,'numeric_comparison':{'same_input':same_input,'absolute_deltas':deltas,'tolerance':.001,'status':'passed' if deltas is not None and all(v<=.001 for v in deltas) else 'failed' if deltas is not None else 'not_evaluated','historical_failure_preserved':True},'diagnostic_identity_fixture':True,'diagnostic_deadline_override_memory_only':True,'provider_calls':0,'sql_calls':0,'m2m_verified':False,'user_auth_verified':False,'quality_accepted':False,'release_authorized':False,'e2e':False}


def main():
    root=Path(__file__).resolve().parent
    c=json.loads((root/'canary141-config.json').read_bytes());expires=check_expiry(c['expires_at_unix'])
    # Hard process deadline, independent of HTTP traffic; root must stop compute.
    timer=threading.Timer(expires-time.time(),lambda:os._exit(0));timer.daemon=True;timer.start()
    try:report=probe(root,expires)
    except Exception as error:report={'status':'FAIL_LINUX_CANARY','error_type':type(error).__name__,'error_code':str(error) if str(error).startswith('CANARY141_') else 'CANARY141_BOOTSTRAP_FAILED','quality_accepted':False,'release_authorized':False}
    raw=json.dumps(report,sort_keys=True).encode()
    print('SBS_CANARY141_RESULT '+raw.decode(),flush=True)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            if time.time()>=expires:self.send_error(410);return
            if self.path not in PUBLIC_PATHS:self.send_error(404);return
            body=raw if self.path=='/evidence' else json.dumps({'status':report['status'],'diagnostic_only':True}).encode()
            self.send_response(200 if report['status']=='PASS_LINUX_CANARY_RUNTIME_ONLY' else 503);self.send_header('Content-Type','application/json');self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(body)
    server=HTTPServer(('0.0.0.0',int(os.environ['DATABRICKS_APP_PORT'])),Handler);server.serve_forever()
if __name__=='__main__':main()
