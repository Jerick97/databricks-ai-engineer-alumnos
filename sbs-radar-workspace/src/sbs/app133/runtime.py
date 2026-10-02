"""App-owned lifecycle;125 semantics reused unchanged on the focal route."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
import json,time,threading
from sbs.runtime import LocalService
from sbs.conversation import route_intent
from sbs.conversation.databricks import DatabricksGenerator,SingleShotTransport
from sbs.conversation.comparison_focus_094 import TrialTypedTransport
from sbs.conversation.hybrid_125 import HybridGenerator
from sbs.conversation.qwen_trial_110 import initialize_trial_models,load_candidate
from sbs.conversation.generation_contract_086 import write_once

class ProcessBudget:
    def __init__(self,*,deadline,max_posts,clock=time.time):
        if type(deadline) is not int or deadline<0 or type(max_posts) is not int or not 1<=max_posts<=100:raise ValueError('APP133_LIMIT_INVALID')
        self.deadline=deadline;self.max_posts=max_posts;self.clock=clock;self.posts=0;self.lock=threading.Lock()
    def check(self):
        if self.clock()>=self.deadline:raise ValueError('APP133_DEADLINE_EXPIRED')
    def reserve(self):
        with self.lock:
            self.check()
            if self.posts>=self.max_posts:raise ValueError('APP133_PROCESS_POST_LIMIT')
            self.posts+=1

class GuardedTransport(SingleShotTransport):
    def __init__(self,delegate,budget):self.delegate=delegate;self.budget=budget;self.last_attempt={}
    def __call__(self,body):
        self.last_attempt={'stage':'process_budget'};self.budget.reserve()
        try:return self.delegate(body)
        finally:self.last_attempt=deepcopy(self.delegate.last_attempt)

class DeadlineTransport:
    def __init__(self,delegate,budget):self.delegate=delegate;self.budget=budget
    @property
    def last_attempt(self):return self.delegate.last_attempt
    def __call__(self,body):self.budget.check();return self.delegate(body)

class RouteGenerator:
    """Explicit routing, never retry/fallback after hybrid rejection.

    Generic/mixed preserves the complete original request and existing strict
    parser. It is a separate unaccepted route, not covered by125quality.
    """
    def __init__(self,raw,directory,root,budget):
        self.raw=GuardedTransport(raw,budget);self.directory=Path(directory);self.root=Path(root);self.budget=budget
        self.calls=0;self.last_attempt={};self.lock=threading.Lock()
    @property
    def requests(self):return self.budget.posts
    def __call__(self,request):
        with self.lock:
            self.budget.check();self.calls+=1
            directory=self.directory/('request-'+uuid4().hex)
            data=json.loads(request['messages'][1]['content']);intent=route_intent(data['question'])
            hybrid=intent['comparison'] and not intent['counts'] and set(data.get('tool_results',{}))=={'rag','comparison'}
            route='hybrid125' if hybrid else 'generic_preserved_request'
            write_once(directory,'route.json',{'route':route,'component_call':self.calls,'process_posts_before':self.requests,'deadline':self.budget.deadline,'budget_scope':'process_only; external_demo_ledger_required','semantic_acceptance':False})
            transport=TrialTypedTransport(self.raw,directory,'qwen35-122b-a10b')
            delegate=DatabricksGenerator(transport=transport,max_requests=4,max_tokens=8000,endpoint='databricks-qwen35-122b-a10b',expected_response_model='qwen35-122b-a10b',max_input_chars=120000)
            generator=HybridGenerator(delegate,directory,self.root) if hybrid else delegate
            try:return generator(request)
            finally:
                self.last_attempt={'route':route,'capture_id':directory.name,'component_invocations':self.calls,'process_posts_reserved':self.requests,'budget_scope':'process_only','generation':deepcopy(generator.last_attempt),'network_known':transport.network_post_attempts,'network_unknown':transport.network_post_attempts_unknown,'quality_accepted':False}
                write_once(directory,'route-result.json',self.last_attempt)

class AppService(LocalService):
    def configure133(self,root,config,*,clock=time.time,client_factory=None):
        self.app_root=Path(root).resolve();self.app_config=deepcopy(config);self.app_client_factory=client_factory
        self.process_budget=ProcessBudget(deadline=config['deadline_unix'],max_posts=config['generation_posts_per_process'],clock=clock)
        self.capture_directory=self.app_root/'.runtime133'/('process-'+uuid4().hex)
        self.provenance['app133']={'capture_process':self.capture_directory.name,'budget_scope':'process_only','deadline_unix':config['deadline_unix'],'demo_ledger':'external_orchestrator','quality_accepted':False}
        return self
    def ask(self,*args,**kwargs):
        self.process_budget.check()
        return super().ask(*args,**kwargs)
    def initialize_models(self):
        if self.generator is not None:return
        self.process_budget.check()
        from databricks.sdk import WorkspaceClient
        from databricks.sdk.core import Config
        cfg=self.app_config
        client=self.app_client_factory() if self.app_client_factory else WorkspaceClient(config=Config(host=cfg['workspace_host'],auth_type='oauth-m2m',http_timeout_seconds=60,retry_timeout_seconds=0))
        if (client.config.host.rstrip('/'),client.config.auth_type,client.config.client_id)!=(cfg['workspace_host'], 'oauth-m2m',cfg['reader_client_id']):raise ValueError('APP133_IDENTITY_MISMATCH')
        #110's local-only guard applies to an isolated dependency container;
        # the real service remains cloud, retaining actor/Genie guards.
        proxy=SimpleNamespace(mode='local',generator=None,index_payload=self.index_payload,provenance={})
        capture=initialize_trial_models(proxy,self.app_root,self.capture_directory,load_candidate(self.app_root),client_factory=lambda:client)
        proxy.embedding.max_calls=cfg['embedding_posts_per_process'];proxy.embedding.max_tokens=cfg['embedding_tokens_per_process']
        if hasattr(self.process_budget, 'reserve_embedding'):
            from .lifecycle210 import CAPS, EmbeddingTransport210
            proxy.embedding.max_calls=CAPS['embedding_posts'];proxy.embedding.max_tokens=CAPS['embedding_tokens']
            proxy.embedding._transport=EmbeddingTransport210(proxy.embedding._transport,proxy.embedding,self.process_budget)
        else:
            proxy.embedding._transport=DeadlineTransport(proxy.embedding._transport,self.process_budget)
        self.embedding=proxy.embedding;self.reranker=proxy.reranker
        self.generator=RouteGenerator(capture.delegate,self.capture_directory,self.app_root,self.process_budget)
        self.generation_selection_path='config/generation-selection-110.json'
        self.provenance.update(proxy.provenance)
