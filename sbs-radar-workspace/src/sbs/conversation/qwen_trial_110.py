"""Opt-in one-pass Qwen trial; capture strict observed block shapes, no promotion."""
from copy import deepcopy
from pathlib import Path
import hashlib,json,threading
from .comparison_focus_094 import build_focus,POLICY,TrialTypedTransport
from .verification_102 import DRAFT_POLICY
from .generation_contract_086 import write_once
from sbs.comparison.literal_102 import literal_changes
from sbs.guardrails.comparison_roles_094 import validate_roles

SELECTION='config/generation-selection-110.json'

def load_candidate(root):
    root=Path(root).resolve();path=root/SELECTION
    if path.is_symlink() or path.stat().st_size>65536:raise ValueError('QWEN_SELECTION_INVALID')
    c=json.loads(path.read_bytes())
    fields={'version','status','endpoint','expected_response_model','max_requests','max_output_tokens','max_input_chars','observation_path','observation_sha256','quality_accepted'}
    if not isinstance(c,dict) or set(c)!=fields or type(c['version']) is not int or c['version']!=1 or c['status']!='candidate_for_controlled_trial' or c['quality_accepted'] is not False:raise ValueError('QWEN_SELECTION_INVALID')
    if (c['endpoint'],c['expected_response_model'])!=('databricks-qwen35-122b-a10b','qwen35-122b-a10b'):raise ValueError('QWEN_MODEL_INVALID')
    if any(type(c[k]) is not int or c[k]!=v for k,v in [('max_requests',4),('max_output_tokens',8000),('max_input_chars',120000)]):raise ValueError('QWEN_LIMIT_INVALID')
    if c['observation_path']!='runs/sk05-generation-candidates-109-databricks-qwen35-122b-a10b.json':raise ValueError('QWEN_OBSERVATION_PATH_INVALID')
    raw=(root/c['observation_path']).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=c['observation_sha256']:raise ValueError('QWEN_OBSERVATION_DRIFT')
    observed=json.loads(raw)
    if observed.get('endpoint')!=c['endpoint'] or observed.get('model')!=c['expected_response_model'] or observed.get('http_status')!=200:raise ValueError('QWEN_OBSERVATION_IDENTITY_INVALID')
    return c


class QwenLiteralGenerator:
    def __init__(self,delegate,directory):
        if (delegate.endpoint,delegate.expected_response_model,delegate.max_requests,delegate.max_tokens,delegate.max_input_chars,delegate.requests)!=('databricks-qwen35-122b-a10b','qwen35-122b-a10b',4,8000,120000,0):raise ValueError('QWEN_GENERATOR_INVALID')
        self.delegate=delegate;self.directory=Path(directory);self.calls=0;self.failed=False;self.last_attempt={};self.lock=threading.Lock()
    def __getattr__(self,name):return getattr(self.delegate,name)
    def __call__(self,request):
        with self.lock:
            if self.failed or self.calls>=4:raise ValueError('QWEN_TRIAL_CLOSED')
            ordinal=self.calls;self.calls+=1;self.last_attempt={'stage':'qwen_prepare','quality_accepted':False}
            try:
                messages=deepcopy(request['messages'])
                if len(messages)!=2 or messages[0].get('role')!='system' or messages[1].get('role')!='user':raise ValueError('QWEN_MESSAGE_SHAPE')
                data=json.loads(messages[1]['content'])
                if any(k in data for k in ('comparison_focus','comparison_literal','draft','verification')):raise ValueError('QWEN_CLIENT_FIELDS_FORBIDDEN')
                focus=build_focus(data);literal=literal_changes(focus)
                data.update(comparison_focus=focus,comparison_literal=literal)
                messages[0]['content']+=POLICY+DRAFT_POLICY;messages[1]['content']=json.dumps(data,ensure_ascii=False)
                write_once(self.directory,f'generation-{ordinal}-intent.json',dict(turn=ordinal,phase='one_generation_no_verifier',endpoint=self.delegate.endpoint,model=self.delegate.expected_response_model,max_tokens=8000,max_input_chars=120000,retry=False))
                write_once(self.directory,f'generation-{ordinal}-literal.json',literal)
                generated=self.delegate({'messages':messages})
                write_once(self.directory,f'generation-{ordinal}-parsed.json',generated)
                checked=validate_roles(generated,focus);write_once(self.directory,f'generation-{ordinal}-roles.json',checked)
                self.last_attempt.update(stage='qwen_completed' if checked['valid'] else 'qwen_roles_rejected',comparison_roles=checked)
                if not checked['valid']:raise ValueError('QWEN_ROLES_REJECTED')
                return generated
            except Exception:
                self.failed=True
                if self.last_attempt['stage']=='qwen_prepare':self.last_attempt['stage']='qwen_generation_failed'
                raise
            finally:
                self.last_attempt['generation']=deepcopy(self.delegate.last_attempt)
                self.last_attempt['requests']=self.delegate.requests


def initialize_trial_models(service,root,directory,selection,*,client_factory=None):
    """Same pinned embedding/reranker constructors as runtime, explicit Qwen8000.

    The frozen generic selection loader caps5000; do not change it or construct
    a different generation endpoint temporarily. Nothing calls inference here.
    """
    from databricks.sdk import WorkspaceClient
    from sbs.models import ModelManifest
    from sbs.models.databricks import DatabricksEmbeddingAdapter,PinnedQwenTokenizer,SingleShotTransport
    from sbs.models.reranker import LocalOnnxReranker
    from sbs.paths import resolve_model_manifest
    from .databricks import DatabricksGenerator,SingleShotTransport as GenerationTransport
    root=Path(root)
    if service.mode!='local' or service.generator is not None:raise ValueError('QWEN_SERVICE_INVALID')
    if selection!=load_candidate(root):raise ValueError('QWEN_SELECTION_CHANGED')
    client=client_factory() if client_factory else WorkspaceClient(profile='databricks-ai-engineer-aws')
    if client.config.host.rstrip('/')!='https://dbc-0410b264-20c7.cloud.databricks.com':raise ValueError('QWEN_HOST_MISMATCH')
    def read(p):return json.loads((root/p).read_bytes())
    manifest=ModelManifest.from_bundle(read('config/pilot-model-bundle.json')['bundle'])
    if manifest.bundle_hash!=service.index_payload['bundle_hash']:raise ValueError('QWEN_EMBEDDING_BUNDLE_CHANGED')
    tokenizer_config=resolve_model_manifest(read('runs/sk05-qwen-tokenizer.json'),root=root);f=tokenizer_config['files']['tokenizer.json']
    tokenizer=PinnedQwenTokenizer(f['path'],revision=tokenizer_config['revision'],sha256=f['sha256'])
    service.embedding=DatabricksEmbeddingAdapter(manifest,tokenizer,transport=SingleShotTransport(client),max_calls=2,max_tokens=20000)
    service.reranker=LocalOnnxReranker.from_manifest(resolve_model_manifest(read('context/reranker-manifest.json'),root=root),cpu_threads=2)
    transport=TrialTypedTransport(GenerationTransport(client,endpoint=selection['endpoint']),directory,selection['expected_response_model'])
    delegate=DatabricksGenerator(transport=transport,max_requests=4,max_tokens=8000,endpoint=selection['endpoint'],expected_response_model=selection['expected_response_model'],max_input_chars=120000)
    service.generator=QwenLiteralGenerator(delegate,directory)
    service.generation_selection_path=SELECTION;service.provenance['generation_selection']=deepcopy(selection)
    return transport
