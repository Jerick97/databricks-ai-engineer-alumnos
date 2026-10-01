"""SK07/SK10 local operator runtime. Frozen real corpus; no fixture fallback.

Supports local operator or verified cloud identity through AuthorizedService.
Inference is lazy, finite, serialized, and never runs during construction.
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import threading
from uuid import uuid4
from functools import wraps

from sbs.conversation import Conversation, Session, Tool, route_intent
from sbs.foundation.extract import extract
from sbs.retrieval import LocalIndex, ServerScope, retrieve
from sbs.paths import project_path, resolve_model_manifest
from sbs.guardrails import authorize

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data/retrieval/sk04-real-001'
LIMITS = ['Se comparan copias del repositorio; su numeración no acredita vigencia actual.',
          'Cobertura parcial: faltan actos modificatorios y revisión completa de tablas y anexos.',
          'La muestra fue revisada por IA; las implicancias son propuestas, sin aprobación institucional.']
LABELS = {'cybersecurity':'Seguridad de la información y ciberseguridad',
          'market_conduct':'Conducta de mercado'}
SELECTIONS = {'cyber-504': [('art20.3','cyber-art20-3','Artículo 20.3 · Responsabilidad por pérdidas','v4-art20-3','v5-art20-3')],
              'market-3274': [('art27','market-art27','Artículo 27 · Seguros adicionales','market-v7-art27','market-v8-art27'),
                              ('art29.1.4','market-art29-1-4','Artículo 29.1.4 · Pagos anticipados','market-v7-art29-1','market-v8-art29-1')]}

def read(path): return json.loads(Path(path).read_text())
def digest(v): return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def unseal(path):
    obj=read(path)
    if digest(obj['payload'])!=obj['sha256']: raise ValueError('cache_integrity_failed')
    return obj['payload']

def synchronized(method):
    @wraps(method)
    def call(self,*args,**kwargs):
        with self.lock:return method(self,*args,**kwargs)
    return call

class LocalService:
    def __init__(self, mode='local', *, generation_selection_path='config/generation-selection-073.json'):
        if mode not in ('local','cloud'):raise ValueError('invalid_runtime_mode')
        self.mode=mode
        self.generation_selection_path=generation_selection_path
        paths=['skills/sbs-conversacion-orquestacion/SKILL.md','skills/sbs-canal-revision/SKILL.md',
               'skills/sbs-conversacion-orquestacion/assets/generator-instructions.md',
               'src/sbs/conversation/__init__.py','src/sbs/conversation/databricks.py','src/sbs/runtime.py']
        self.provenance={'created_at':datetime.now(timezone.utc).isoformat(),
                         'files':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
                         'skills':{p:(ROOT/p).read_text() for p in paths[:2]}}
        report=read(ROOT/'runs/sk04-real-001-report.json')
        for path,sha in report['artifacts_sha256'].items():
            if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=sha:
                raise ValueError('corpus_cache_integrity_failed')
        self.index_payload=unseal(DATA/'index.json')
        records=read(DATA/'records.json'); p=self.index_payload
        self.index=LocalIndex(records,p['vectors'],dimension=p['dimension'],model_identity=p['bundle_hash'],actual_identity=p['bundle_hash'],complete=True)
        if self.index.index_hash!=p['index_hash']: raise ValueError('index_identity_failed')
        self.protocol=unseal(ROOT/'runs/sk04-real-001-protocol.json')
        self.snapshot=self.protocol['corpus_hash']
        self.sources={}; self.source_families={}; self.originals={}; self.bundles={}
        for capture in ['sk02-repository-capture','sk02-amendments-capture']:
            for row in read(ROOT/f'runs/{capture}.json')['sources']:
                source=row['source']; version=source['version_id']
                original=project_path(ROOT,row['original_path'])
                if hashlib.sha256(original.read_bytes()).hexdigest()!=source['sha256']: raise ValueError('source_identity_failed')
                bundle=extract(source,root=ROOT/'data/foundation-repository')
                identity=(source['document_id'],version)
                self.originals[identity]=bundle['rawtext']; self.bundles[identity]=bundle
                self.sources[version]=original
                self.source_families[version]=source['family']
        self.scope=ServerScope(frozenset(LABELS),frozenset(self.originals))
        citations={**read(ROOT/'runs/astra-normative-review.json')['citations'],**read(ROOT/'runs/astra-normative-review-003.json')['citations']}
        self.entries={}; self.pairs=[]
        for pair_id,specs in SELECTIONS.items():
            for provision,qid,label,b,a in specs:
                q=next(q for q in self.protocol['questions'] if q['query_id']==qid)
                ctx=deepcopy(q['context']); ctx['pair']['pair_id']=pair_id
                ctx.update(context_id=f'{pair_id}-{provision}',selected_provision_id=provision)
                before,after=deepcopy(citations[b]),deepcopy(citations[a])
                for cite in (before,after):
                    raw=self.originals[(cite['document_id'],cite['version_id'])]
                    if raw[cite['start']:cite['end']]!=cite['quote_raw']: raise ValueError('review_span_identity_failed')
                self.entries[(pair_id,provision)]={'context':ctx,'label':label,'before':before,'after':after}
            self.pairs.append({'id':pair_id,'family_id':ctx['family'],'title':'Resolución SBS '+('504-2021' if pair_id=='cyber-504' else '3274-2017'),
                'before_label':'Copia v4' if pair_id=='cyber-504' else 'Copia v7','after_label':'Copia v5' if pair_id=='cyber-504' else 'Copia v8',
                'status':'unreviewed','evidence_status':'partial','provisions':[{'id':x[0],'label':x[2]} for x in specs]})
        qcache=unseal(DATA/'queries-000.json')
        self.query_cache={q['question']:vector for q,vector in zip(self.protocol['questions'],qcache['embeddings'])}
        from sbs.comparison.pilot import by_provision
        self.comparisons=by_provision(ROOT)
        for e in self.entries.values():
            item=self.comparisons[(e['context']['family'],e['context']['selected_provision_id'])]
            for side in ('before','after'):
                p=item[side]
                e[side].update(start=p['start'],end=p['end'],quote_raw=p['text'],citation_id=p['citation_id'])
        self.generator=None; self.embedding=None; self.reranker=None; self.genie_binding=None
        self.limitations=list(LIMITS)
        self.sessions={}; self.lock=threading.RLock(); self.last_result=None

    @classmethod
    def from_release(cls,state_root,*,pointer,mode='local'):
        if mode not in ('local','cloud'):raise ValueError('invalid_runtime_mode')
        service=cls.__new__(cls);service.mode=mode
        model=read(ROOT/'config/pilot-model-bundle.json')
        if digest(model['bundle'])!=model['bundle_hash']:raise ValueError('model_bundle_integrity_failed')
        report=read(ROOT/'runs/sk04-real-001-report.json')
        for name in ('data/retrieval/sk04-real-001/queries-000.json',):
            if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=report['artifacts_sha256'][name]:raise ValueError('query_cache_integrity_failed')
        protocol=unseal(ROOT/'runs/sk04-real-001-protocol.json');queries=unseal(DATA/'queries-000.json')
        if digest(protocol)!=report['protocol_sha256']:raise ValueError('query_protocol_integrity_failed')
        if queries['bundle_hash']!=model['bundle_hash']:raise ValueError('query_cache_model_mismatch')
        service.query_cache={q['question']:vector for q,vector in zip(protocol['questions'],queries['embeddings'])}
        service.index_payload={'bundle_hash':model['bundle_hash']};service.snapshot=None
        service.provenance={'created_at':datetime.now(timezone.utc).isoformat(),'runtime_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
        service.generator=None;service.embedding=None;service.reranker=None;service.genie_binding=None
        service.sessions={};service.lock=threading.RLock();service.last_result=None
        service.promote_release(state_root,pointer=pointer)
        return service

    def promote_release(self,state_root,*,pointer):
        if hasattr(self,'structural_metadata'):raise ValueError('STRUCTURAL_MIXED_PROMOTION')
        from sbs.operations.runtime_release import load_release
        # All I/O/validation finishes before readers see any candidate field.
        candidate=load_release(state_root,pointer=pointer,model_identity=self.index_payload['bundle_hash'])
        with self.lock:
            previous=self.snapshot
            if candidate['snapshot']==previous:
                return {'status':'unchanged','snapshot':previous,'previous_snapshot':previous}
            self.__dict__.update(candidate)
            self.genie_binding=None
            self.limitations=list(LIMITS[:2])+['Comparación literal parcial; correspondencias estructurales heurísticas cuando disponibles. Anotaciones IA reutilizadas: '+str(self.release_metadata['annotation_count'])+'. Sin aprobación institucional.']
            self.provenance={**self.provenance,'release':deepcopy(self.release_metadata)}
            self.last_result=None
            return {'status':'promoted','snapshot':self.snapshot,'previous_snapshot':previous,'coverage':'partial','cloud_publication':False}

    @synchronized
    def session_key(self,subject,session_id):
        return (subject,session_id,self.snapshot)

    def _comparison_item(self,context):
        key=(context['pair']['pair_id'],context['selected_provision_id']) if hasattr(self,'release_metadata') else (context['family'],context['selected_provision_id'])
        return self.comparisons[key]

    def refresh_if_due(self):
        refresh=getattr(self,'cloud_refresh',None)
        if refresh is not None:return refresh.refresh_if_due()
        return {'enabled':False,'status':'disabled','reason':None,'last_checked_at':None,'last_success_at':None,'publication_id':None,'checks':0,'evidence_mode':'not_observed'}

    def catalog(self):
        freshness=self.refresh_if_due()
        with self.lock:
            if getattr(self,'cloud_refresh',None) is not None:freshness=self.cloud_refresh.status()
            return {'families':[{'id':k,'label':v} for k,v in LABELS.items()], 'pairs':deepcopy(self.pairs),'snapshot':self.snapshot,'runtime_refresh':freshness,**({'retrieval_profile':deepcopy(self.structural_metadata)} if hasattr(self,'structural_metadata') else {})}

    @synchronized
    def entry(self,pair_id,provision_id=None):
        if not any(p['id']==pair_id for p in self.pairs): raise KeyError('unknown_pair')
        if provision_id is None:raise KeyError('explicit_provision_required')
        return self.entries[(pair_id,provision_id)]

    @synchronized
    def source(self,source_id): return self.sources[source_id]

    def for_actor(self,actor):
        view=AuthorizedService(self,actor)
        self.refresh_if_due()
        return view

    @staticmethod
    def cite(c,metadata=None):
        pages=(metadata or {}).get('pages',[c['page']])
        return {'source_id':c['version_id'],'label':c['document_id']+' · p. '+', '.join(str(p) for p in pages),
                'excerpt':c.get('quote_raw',c.get('text','')),'page':c['page'],'pages':pages,'citation_id':c.get('citation_id')}

    @synchronized
    def comparison(self,pair_id,provision_id=None):
        e=self.entry(pair_id,provision_id); p=next(p for p in self.pairs if p['id']==pair_id)
        out={'snapshot':self.snapshot,'pair_id':pair_id,'provision_id':e['context']['selected_provision_id'],'title':e.get('display_label',e['label']),
             'status':'unreviewed','evidence_status':'partial','summary':'Pasajes de las copias comparadas; correspondencia y cobertura parciales, vigencia actual no establecida.',
             'citations':[self.cite(e[s]) for s in ('before','after')],'limitations':list(self.limitations)}
        for side in ('before','after'):
            c=e[side]; out[side]={'label':p[side+'_label'],'text':c['quote_raw'],'source_id':c['version_id'],'page':c['page']}
        item=self._comparison_item(e['context'])
        if item.get('focus_origin')=='SK03_structural_heuristic':
            out.update(evidence=deepcopy(item['change_set']['evidence']),citation_metadata=deepcopy(item['citation_metadata']),
                       evidence_context=deepcopy(item['evidence_context']),alignment_provenance=deepcopy(item['alignment_provenance']),
                       derived_comparison=deepcopy(item['derived_comparison']))
            out['citations']=[self.cite(c,item['citation_metadata'].get(c['citation_id'])) for c in item['citations']]
            out['limitations']=list(dict.fromkeys(out['limitations']+item['evidence_context']['global_limitations']))
            for side in ('before','after'):out[side]['pages']=item['citation_metadata'][e[side]['citation_id']]['pages']
        return out

    def initialize_models(self):
        if self.generator is not None:return
        from sbs.models.generation_selection import load_selection
        selection=load_selection(ROOT,getattr(self,'generation_selection_path','config/generation-selection-073.json'))
        from databricks.sdk import WorkspaceClient
        from sbs.models import ModelManifest
        from sbs.models.databricks import DatabricksEmbeddingAdapter, PinnedQwenTokenizer, SingleShotTransport
        from sbs.models.reranker import LocalOnnxReranker
        from sbs.conversation.databricks import DatabricksGenerator, SingleShotTransport as GenerationTransport
        client=WorkspaceClient(profile='databricks-ai-engineer-aws') if self.mode=='local' else WorkspaceClient(auth_type='oauth-m2m')
        m=ModelManifest.from_bundle(read(ROOT/'config/pilot-model-bundle.json')['bundle'])
        if m.bundle_hash!=self.index_payload['bundle_hash']:raise ValueError('model_bundle_changed')
        tok=resolve_model_manifest(read(ROOT/'runs/sk05-qwen-tokenizer.json'),root=ROOT); f=tok['files']['tokenizer.json']
        tokenizer=PinnedQwenTokenizer(f['path'],revision=tok['revision'],sha256=f['sha256'])
        self.embedding=DatabricksEmbeddingAdapter(m,tokenizer,transport=SingleShotTransport(client),max_calls=20,max_tokens=20000)
        self.reranker=LocalOnnxReranker.from_manifest(resolve_model_manifest(read(ROOT/'context/reranker-manifest.json'),root=ROOT),cpu_threads=2)
        self.generator=DatabricksGenerator(transport=GenerationTransport(client,endpoint=selection['endpoint']),max_requests=selection['max_requests'],max_tokens=selection['max_output_tokens'],endpoint=selection['endpoint'],expected_response_model=selection['expected_response_model'],max_input_chars=selection['max_input_chars'])
        self.provenance['generation_selection']=deepcopy(selection)

    @synchronized
    def initialize_genie(self):
        if hasattr(self,'structural_metadata'):raise ValueError('GENIE_STRUCTURAL_UNPUBLISHED')
        if hasattr(self,'release_metadata'):raise ValueError('GENIE_RELEASE_UNPUBLISHED')
        if self.genie_binding is None:
            from sbs.genie.server import load_server_binding
            self.genie_binding=load_server_binding(ROOT,mode=self.mode)
        if self.genie_binding.rag_snapshot!=self.snapshot:
            raise ValueError('genie_rag_mapping_conflict')
        return self.genie_binding

    def rag_live(self,question,context):
        if hasattr(self,'structural_metadata'):
            self._structural_query_guard(question,context)
        self.initialize_models()
        return self.rag(question,context)

    def _structural_query_guard(self,question,context):
        entry=self.entry(context['pair']['pair_id'],context['selected_provision_id'])
        if context!=entry['context']:raise ValueError('STRUCTURAL_CONTEXT_MISMATCH')
        if question not in self.query_cache:raise ValueError('STRUCTURAL_QUERY_NOT_REVIEWED')

    @synchronized
    def rag(self,question,context):
        if hasattr(self,'structural_metadata'):self._structural_query_guard(question,context)
        vector=self.query_cache.get(question)
        entry=self.entry(context['pair']['pair_id'],context['selected_provision_id'])
        retrieval_question=question if vector is not None else entry['label']+' · Consulta: '+question
        options={'query_vector':vector,'query_identity':self.index_payload['bundle_hash']} if vector is not None else {'adapter':self.embedding}
        out=retrieve(self.index,retrieval_question,context,self.scope,top_k=5,candidate_k=20,reranker=self.reranker,counterparts=self.protocol['alignment'],**options)
        if out.get('evidence'):
            # Deterministic focus expansion from verified SK03 annotations, not
            # an asserted relevance win of lexical/vector/reranker retrieval.
            item=self._comparison_item(context)
            existing={c['citation_id'] for c in out['evidence']['citations']}
            added=[deepcopy(c) for c in item['citations'] if c['citation_id'] not in existing]
            out['evidence']['citations'].extend(added)
            out.setdefault('trace',{})['selected_provision_expansion']={'origin':item.get('focus_origin','SK03_AI_annotated_subset'),'citation_ids':[c['citation_id'] for c in added]}
            out['evidence']['limitations']=list(dict.fromkeys(out['evidence']['limitations']+self.limitations))
            if item.get('focus_origin')=='SK03_structural_heuristic':
                out['trace']['selected_provision_expansion']['retrieval_strategy']='cached_raw_pages_plus_structural_expansion'
                out['trace']['selected_provision_expansion']['semantic_vectors']='pending_not_built'
                out['citation_metadata']=deepcopy(item['citation_metadata']);out['evidence_context']=deepcopy(item['evidence_context'])
                out['alignment_provenance']=deepcopy(item['alignment_provenance'])
                out['evidence']['limitations']=list(dict.fromkeys(out['evidence']['limitations']+item['evidence_context']['global_limitations']))
                for c in out['evidence']['citations']:
                    if c['citation_id'] not in out['citation_metadata']:
                        b=self.bundles[(c['document_id'],c['version_id'])]
                        out['citation_metadata'][c['citation_id']]={'pages':[p['page'] for p in b['pages'] if p['start']<c['end'] and p['end']>c['start']],'kind':'retrieved_raw_page'}
        if hasattr(self,'structural_metadata'):
            out.setdefault('trace',{})['runtime_retrieval_profile']=deepcopy(self.structural_metadata)
            expansion=out['trace'].get('selected_provision_expansion')
            if expansion is not None:
                expansion['retrieval_strategy']=self.structural_metadata['retrieval_strategy']
                expansion['semantic_vectors']='real231_cached'
            out['citation_metadata']={r['citation']['citation_id']:{'pages':r['pages'],'kind':'retrieved_structural_unit','origin':r['origin']} for r in self.index._rows if any(c['citation_id']==r['citation']['citation_id'] for c in (out.get('evidence') or {}).get('citations',[]))}
        return {**out,'snapshot':self.snapshot}

    @synchronized
    def compare(self,question,context):
        item=self._comparison_item(context)
        out={k:deepcopy(item[k]) for k in ('change_set','changes','alignments','candidates','provenance','no_changes')}
        return {**out,**{k:deepcopy(item[k]) for k in ('citation_metadata','evidence_context','alignment_provenance','derived_comparison') if k in item},'status':'partial','snapshot':self.snapshot,'limitations':['Comparación literal parcial; materialidad no adjudicada.']+item.get('evidence_context',{}).get('global_limitations',[])}

    def ask(self,session_id,question,pair_id,provision_id=None,cross_family=False,*,actor=None):
        # One finite local process quota. Client identities/roles are never accepted.
        with self.lock:
            if not isinstance(question,str) or not question.strip() or len(question)>8000:raise ValueError('invalid_question')
            context=deepcopy(self.entry(pair_id,provision_id)['context'])
            if actor is None:
                if self.mode!='local':raise PermissionError('verified_actor_required')
                actor={'authenticated':True,'subject':'local-operator','role':'reader','families':list(LABELS)}
            if not authorize(actor,'chat',{'family':context['family'],'processing_status':'partial'})['valid']:
                raise PermissionError('family_denied')
            if cross_family and not set(LABELS).issubset(actor['families']):raise PermissionError('cross_family_denied')
            session_id=self.session_key(actor['subject'],session_id)
            run_id='sk07-live-'+uuid4().hex
            invocation={'run_id':run_id,'started_at':datetime.now(timezone.utc).isoformat(),
                        'context':context,'cross_family':cross_family,'question_sha256':hashlib.sha256(question.encode()).hexdigest(),
                        'provenance':self.provenance,'snapshot':self.snapshot,'status':'started','automatic_retries':0}
            (ROOT/'runs'/f'{run_id}-invocation.json').write_text(json.dumps(invocation,ensure_ascii=False,indent=2)+'\n')
            if session_id not in self.sessions:
                self.sessions[session_id]=Session(deepcopy(actor),context,self.snapshot,self.originals,'partial')
            session=self.sessions[session_id]
            session.actor=deepcopy(actor)
            tools={'rag':Tool(self.rag_live,'real'),'comparison':Tool(self.compare,'real')}
            if route_intent(question)['counts']:
                try:
                    binding=self.initialize_genie()
                    tools['genie']=Tool(lambda q,c:binding.ask_scoped(q,context=c),'real',
                        expected_snapshot=binding.genie_snapshot,mapped_from_snapshot=binding.rag_snapshot,
                        mapping_sha256=binding.mapping_sha256)
                except ValueError:
                    tools['genie']=Tool(lambda q,c:{'status':'unavailable','reason':'GENIE_LOCAL_CONFIG_INVALID'},'real')
            from sbs.conversation.process_context import process_context
            engine=Conversation(tools=tools,generator=RuntimeGenerator(self),generator_mode='real',process_context=lambda ctx:process_context(ROOT,ctx['family']))
            if cross_family:
                other=next((p for p in self.pairs if p['family_id']!=context['family']),None)
                if other is None:raise ValueError('cross_family_unavailable')
                result=engine.ask_many(session,question,focuses=[context,deepcopy(self.entry(other['id'],other['provisions'][0]['id'])['context'])])
                results=result['answers']
            else:
                result=engine.ask(session,question,focus=context); results=[result]
            self.last_result=deepcopy(result)
            record={'run_id':run_id,'created_at':datetime.now(timezone.utc).isoformat(),'skill':'SK07','result':result,
                    'generator':deepcopy(getattr(self.generator,'last_attempt',None)),'embedding':deepcopy(getattr(self.embedding,'last_attempt',None)),
                    'local_operator':self.mode=='local','cost':None,'semantic_review':'pending'}
            (ROOT/'runs'/f'{run_id}.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
            answers=[r['answer'] for r in results if r.get('answer')]
            citations=[self.cite(c) for a in answers for c in a['evidence']['citations']
                       if c['citation_id'] in {cid for claim in a['material_claims'] for cid in claim['citation_ids']}]
            limits=list(dict.fromkeys(self.limitations+[l for r in results for l in r.get('limitations',[])]+[l for a in answers for l in a['limitations']]))
            texts=[(LABELS[r['focus']['family']]+' · '+r['focus']['selected_provision_id']+'\n' if cross_family else '')+r['answer']['text'] for r in results if r.get('answer')]
            structured=[r['structured_result'] for r in results if r.get('structured_result')]
            for r in results:
                prefix=(LABELS[r['focus']['family']]+' · '+r['focus']['selected_provision_id']+'\n') if cross_family else ''
                if r.get('structured_result'):
                    w=r['structured_result']
                    texts.append(prefix+str(w['value'])+' '+w['unit']+'. '+w['meaning'])
                elif r['status']=='structured_result_unavailable':
                    texts.append(prefix+'Genie no pudo entregar un resultado documental verificado. Revisa la disponibilidad y la configuración del servicio; esto no significa que haya cero registros.')
                elif r['status']=='scope_not_answered':
                    texts.append(prefix+'La consulta disponible no responde al significado solicitado. '+r.get('available_meaning',''))
            return {'snapshot':self.snapshot,'answer':'\n\n'.join(texts),'status':result['status'],'structured_results':structured,
                    'evidence_status':'partial','citations':citations,'limitations':limits}

class RuntimeGenerator:
    """Lazy server dependency: pure structured queries never initialize models."""
    def __init__(self,service):self.service=service
    def __call__(self,request):
        self.service.initialize_models()
        return self.service.generator(request)
    @property
    def last_attempt(self):return deepcopy(getattr(self.service.generator,'last_attempt',None))

class AuthorizedService:
    """Request-scoped view over verified identity. Never constructed from request JSON."""
    def __init__(self,service,actor):
        if not isinstance(actor,dict) or not isinstance(actor.get('subject'),str) or not actor['subject']:
            raise PermissionError('verified_actor_required')
        if not any(authorize(actor,'chat',{'family':f,'processing_status':'partial'})['valid'] for f in LABELS):
            raise PermissionError('family_denied')
        self.service=service;self.actor=deepcopy(actor)

    def _allow(self,family,action='chat'):
        if not authorize(self.actor,action,{'family':family,'processing_status':'partial'})['valid']:
            raise PermissionError('family_denied')

    def catalog(self):
        catalog=self.service.catalog(); families=set(self.actor['families'])
        return {**catalog,'families':[f for f in catalog['families'] if f['id'] in families],
                'pairs':[p for p in catalog['pairs'] if p['family_id'] in families]}

    def comparison(self,pair_id,provision_id=None):
        self.service.refresh_if_due()
        with self.service.lock:
            self._allow(self.service.entry(pair_id,provision_id)['context']['family'])
            return self.service.comparison(pair_id,provision_id)

    def source(self,source_id):
        self.service.refresh_if_due()
        with self.service.lock:
            self._allow(self.service.source_families[source_id],'open_evidence')
            return self.service.source(source_id)

    def ask(self,session_id,question,pair_id,provision_id=None,cross_family=False):
        self.service.refresh_if_due()
        with self.service.lock:
            self._allow(self.service.entry(pair_id,provision_id)['context']['family'])
            if cross_family:
                for family in LABELS:self._allow(family)
            return self.service.ask(session_id,question,pair_id,provision_id,cross_family,actor=self.actor)


def _create_service_local(config_path=None,*,mode='local'):
    path=Path(config_path) if config_path is not None else ROOT/'config/runtime-release.json'
    if not path.exists():
        if config_path is not None:raise ValueError('runtime_release_config_missing')
        return LocalService(mode=mode)
    config=read(path)
    if not isinstance(config,dict) or type(config.get('enabled')) is not bool:raise ValueError('runtime_release_config_invalid')
    if config['enabled'] is False:
        if set(config)!={'enabled'}:raise ValueError('runtime_release_config_invalid')
        return LocalService(mode=mode)
    if set(config)!={'enabled','state_root','pointer'} or not isinstance(config['state_root'],str):raise ValueError('runtime_release_config_invalid')
    relative=Path(config['state_root'])
    if relative.is_absolute() or '..' in relative.parts:raise ValueError('runtime_release_path_invalid')
    return LocalService.from_release(ROOT/relative,pointer=config['pointer'],mode=mode)


def create_service(config_path=None,*,mode='local',cloud_config_path=None,cloud_reader_factory=None,cloud_clock=None,structural_config_path=None):
    if structural_config_path is not None:
        if mode!='local':raise ValueError('STRUCTURAL_LOCAL_ONLY')
        if any(x is not None for x in (config_path,cloud_config_path,cloud_reader_factory,cloud_clock)):raise ValueError('STRUCTURAL_MIXED_BOOTSTRAP')
        from sbs.runtime_structural import load_profile, bind_profile
        candidate=load_profile(ROOT,structural_config_path)
        return bind_profile(LocalService(mode=mode),candidate)
    from sbs.operations.runtime_cloud import attach_cloud_refresh
    # Local bootstrap stays explicit in catalog until a cloud release is observed.
    service=_create_service_local(config_path,mode=mode)
    return attach_cloud_refresh(service,ROOT,config_path=cloud_config_path,reader_factory=cloud_reader_factory,clock=cloud_clock)
