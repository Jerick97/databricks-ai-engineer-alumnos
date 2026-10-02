"""Deterministic focal generation view; full server EvidencePack stays intact."""
from copy import deepcopy
from pathlib import Path
import hashlib,json
from .compaction import digest
from .comparison_focus_094 import build_focus
from .qwen_trial_110 import QwenLiteralGenerator,initialize_trial_models
from .generation_contract_086 import write_once
from sbs.comparison.literal_102 import literal_changes
from sbs.guardrails.comparison_roles_094 import validate_roles

POLICY='skills/sbs-conversacion-orquestacion/assets/generator-instructions-115.md'
OLD_POLICY='skills/sbs-conversacion-orquestacion/assets/generator-instructions.md'
BASE_KEYS={'question','context','evidence','conversation_memory','tool_results','implications','limitations','scope','compaction'}

def focal_packet(data):
    if not isinstance(data,dict) or not BASE_KEYS<=set(data) or set(data)-BASE_KEYS-{'fictitious_process_context'}:raise ValueError('FOCAL_PACKET_INPUT_FIELDS')
    if not isinstance(data['tool_results'],dict) or set(data['tool_results'])-{'rag','comparison'}:raise ValueError('FOCAL_PACKET_UNSUPPORTED_TOOLS')
    focus=build_focus(data);literal=literal_changes(focus)
    ids=[literal[s]['citation_id'] for s in ('before','after')]
    if ids[0]==ids[1]:raise ValueError('FOCAL_PACKET_IDENTITIES_AMBIGUOUS')
    before,after=ids
    packet={k:deepcopy(v) for k,v in data.items() if k not in ('tool_results','compaction')}
    retained=[];excluded=[];positions=[]
    for index,citation in enumerate(data['evidence']['citations']):
        if citation['citation_id'] in ids:retained.append(deepcopy(citation));positions.append(index)
        else:excluded.append(dict(index=index,citation=deepcopy(citation)))
    packet['evidence']['citations']=retained
    packet['evidence_view']={'kind':'authorized_focal_subset_of_current_pack','source_evidence_id':data['evidence']['evidence_id'],'full_pack_retained_by_server':True}
    packet['required_citations']={
        'Antes':{'allowed_ids':[before],'required_ids':[before]},
        'Después':{'allowed_ids':[after],'required_ids':[after]},
        'Cambio':{'allowed_ids':ids,'required_ids':ids},
        'Implicancia propuesta':{'allowed_ids':ids,'required_ids':[],'at_least_one':True}}
    packet['comparison_operations']=dict(format='[operation,before_start,before_end,after_start,after_end]',offset_units='Unicode code points; relative to full citation text',before_citation_id=before,after_citation_id=after,opcodes=[[o['operation'],o['before_start'],o['before_end'],o['after_start'],o['after_end']] for o in literal['operations']],semantic_materiality='not_evaluated')
    manifest=dict(version=1,source_sha256=digest(data),packet_sha256=digest(packet),source_evidence_sha256=digest(data['evidence']),retained_positions=positions,excluded_citations=excluded,removed_fields={k:deepcopy(data[k]) for k in ('tool_results','compaction')},retained_citations=[dict(citation_id=c['citation_id'],citation_sha256=digest(c),text_sha256=hashlib.sha256(c['text'].encode()).hexdigest(),text_utf8_bytes=len(c['text'].encode())) for c in retained])
    if restore_packet(packet,manifest)!=data:raise ValueError('FOCAL_PACKET_ROUNDTRIP_FAILED')
    return packet,manifest


def restore_packet(packet,manifest):
    if manifest.get('version')!=1 or digest(packet)!=manifest['packet_sha256']:raise ValueError('FOCAL_PACKET_CHANGED')
    restored=deepcopy(packet)
    for key in ('required_citations','evidence_view','comparison_operations'):restored.pop(key)
    citations=restored['evidence']['citations'];positions=manifest['retained_positions']
    proof=[dict(citation_id=c['citation_id'],citation_sha256=digest(c),text_sha256=hashlib.sha256(c['text'].encode()).hexdigest(),text_utf8_bytes=len(c['text'].encode())) for c in citations]
    if proof!=manifest['retained_citations']:raise ValueError('FOCAL_PACKET_RETENTION_PROOF_CHANGED')
    if len(citations)!=len(positions):raise ValueError('FOCAL_PACKET_POSITION_MISMATCH')
    indexed=list(zip(positions,citations))+[(item['index'],deepcopy(item['citation'])) for item in manifest['excluded_citations']]
    if sorted(i for i,_ in indexed)!=list(range(len(indexed))):raise ValueError('FOCAL_PACKET_INDEX_INVALID')
    restored['evidence']['citations']=[c for _,c in sorted(indexed,key=lambda row:row[0])]
    restored.update(deepcopy(manifest['removed_fields']))
    if digest(restored)!=manifest['source_sha256'] or digest(restored['evidence'])!=manifest['source_evidence_sha256']:raise ValueError('FOCAL_PACKET_SOURCE_CHANGED')
    return restored


def transform_request(request,root):
    root=Path(root);messages=request.get('messages')
    if not isinstance(messages,list) or len(messages)!=2 or messages[0].get('role')!='system' or messages[1].get('role')!='user':raise ValueError('FOCAL_PACKET_MESSAGES')
    schema=json.loads((root/'src/sbs/conversation/GeneratedClaims.json').read_bytes())
    suffix='\nContrato interno GeneratedClaims del servidor:\n'+json.dumps(schema,ensure_ascii=False)
    expected=(root/OLD_POLICY).read_text()+suffix
    if messages[0]['content']!=expected:raise ValueError('FOCAL_PACKET_UPSTREAM_POLICY_CHANGED')
    data=json.loads(messages[1]['content']);packet,manifest=focal_packet(data)
    result={'messages':[{'role':'system','content':(root/POLICY).read_text()+suffix},{'role':'user','content':json.dumps(packet,ensure_ascii=False)}]}
    return result,manifest,build_focus(data)


class FocalGenerator(QwenLiteralGenerator):
    def __init__(self,delegate,directory,root):
        super().__init__(delegate,directory);self.root=Path(root)
    def __call__(self,request):
        with self.lock:
            if self.failed or self.calls>=4:raise ValueError('FOCAL_TRIAL_CLOSED')
            ordinal=self.calls;self.calls+=1;self.last_attempt={'stage':'focal_prepare','quality_accepted':False}
            try:
                adapted,manifest,focus=transform_request(request,self.root)
                # Sidecar reverses the focal view without exposing excluded
                # evidence/tool duplicates to the model. Original request kept.
                write_once(self.directory,f'generation-{ordinal}-source.json',request)
                write_once(self.directory,f'generation-{ordinal}-packet-map.json',manifest)
                write_once(self.directory,f'generation-{ordinal}-intent.json',dict(turn=ordinal,phase='focal_one_pass115',endpoint=self.delegate.endpoint,model=self.delegate.expected_response_model,max_tokens=8000,max_input_chars=120000,retry=False,source_sha256=manifest['source_sha256'],packet_sha256=manifest['packet_sha256']))
                generated=self.delegate(adapted)
                write_once(self.directory,f'generation-{ordinal}-parsed.json',generated)
                checked=validate_roles(generated,focus);write_once(self.directory,f'generation-{ordinal}-roles.json',checked)
                self.last_attempt.update(stage='focal_completed' if checked['valid'] else 'focal_roles_rejected',comparison_roles=checked,packet_sha256=manifest['packet_sha256'],source_sha256=manifest['source_sha256'],source_evidence_sha256=manifest['source_evidence_sha256'])
                if not checked['valid']:raise ValueError('FOCAL_ROLES_REJECTED')
                return generated
            except Exception:
                self.failed=True
                if self.last_attempt['stage']=='focal_prepare':self.last_attempt['stage']='focal_generation_failed'
                raise
            finally:
                self.last_attempt['generation']=deepcopy(self.delegate.last_attempt);self.last_attempt['requests']=self.delegate.requests


def initialize_focal_models(service,root,directory,selection,*,client_factory=None):
    transport=initialize_trial_models(service,root,directory,selection,client_factory=client_factory)
    # The110 wrapper has never been invoked; reuse its configured8000 delegate.
    service.generator=FocalGenerator(service.generator.delegate,directory,root)
    service.provenance['generation_packet_variant']='115_focal_full_quotes_reversible'
    return transport
