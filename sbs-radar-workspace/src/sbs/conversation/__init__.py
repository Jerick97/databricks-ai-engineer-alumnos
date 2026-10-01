"""SK07 v0.1.6. Server-owned session, finite fixed routing, injected adapters.

No authentication, institutional approval, semantic entailment or E2E claim.
See README.md for the trusted backend boundary and adapter signatures.
"""
from copy import deepcopy
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import re
from uuid import uuid4
from jsonschema import Draft202012Validator

from sbs.contracts import validate_contract
from sbs.guardrails import authorize, validate_answer

ROOT = Path(__file__).resolve().parents[3]
RESOURCE = ROOT / 'skills/sbs-conversacion-orquestacion/assets/generator-instructions.md'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def route_intent(question):
    """One bounded routing policy shared with lazy runtime dependency setup."""
    q=question.casefold()
    counts=bool(re.search(r'cu[aá]nt|conteo|cantidad|lista|estado',q))
    comparison=bool(re.search(r'antes|despu[eé]s|cambi|diferenc',q))
    implications=bool(re.search(r'implican|impacto',q))
    pure_count=counts and not re.search(r'antes|despu[eé]s|qu[eé]\s+(?:dec|cambi)|c[oó]mo|explica|implican|impacto|diferenc',q)
    return {'counts':counts,'comparison':comparison,'implications':implications,'pure_count':pure_count}


def _documentary_count(output, context, snapshot):
    """Typed transport gate after SK06 verification; no SQL re-authorization here.

    Tool is a trusted backend dependency. This gate cannot make a caller-supplied
    scope_verified flag trustworthy and does not prove question/query entailment.
    """
    if not isinstance(output,dict):return None
    reference=output.get('reference_query_id')
    expected={'document_count':('documents','document_version_count','versiones documentales'),
              'provision_count':('provisions','provision_row_count','filas de disposiciones')}.get(reference)
    if expected is None:return None
    table,column,unit=expected
    if (output.get('kind')!='structured_query_result' or output.get('status')!='completed'
            or output.get('scope_verified') is not True or output.get('context')!=context
            or output.get('snapshot')!=snapshot
            or output.get('scope_verification')!='exact_executed_reference_sql_and_pinned_rows'
            or output.get('columns')!=[column]):return None
    if (reference=='provision_count') != (context['selected_provision_id'] is not None):return None
    for key in ('query','query_id'):
        if not isinstance(output.get(key),str) or not output[key].strip():return None
    tables=output.get('source_tables')
    if not isinstance(tables,list) or len(tables)!=1 or not isinstance(tables[0],str) or not tables[0].endswith('.sbs_radar.'+table):return None
    lineage=output.get('lineage');params=output.get('parameters')
    if not isinstance(lineage,dict) or not isinstance(params,dict):return None
    if (lineage.get('snapshot')!=snapshot or lineage.get('pair')!=context['pair']
            or lineage.get('selected_provision_id')!=context['selected_provision_id']
            or not isinstance(lineage.get('rows'),list)
            or not isinstance(lineage.get('corpus_hash'),str) or not lineage['corpus_hash']):return None
    expected_params={'family':context['family'],'corpus_hash':lineage['corpus_hash']}
    for side in ('before','after'):
        for key in ('document_id','version_id'):expected_params[side+'_'+key]=context['pair'][side][key]
    if reference=='provision_count':expected_params['provision_id']=context['selected_provision_id']
    if params!=expected_params:return None
    rows=output.get('rows')
    if not isinstance(rows,list) or len(rows)!=1 or not isinstance(rows[0],list) or len(rows[0])!=1:return None
    raw=rows[0][0]
    if type(raw) is int:
        if raw<0:return None
        value=raw
    elif isinstance(raw,str) and raw.isascii() and raw.isdecimal():
        try:value=int(raw)
        except ValueError:return None
    else:return None
    wrapper={k:deepcopy(output[k]) for k in ('rows','columns','query','query_id','source_tables','snapshot','context','lineage','parameters','reference_query_id')}
    wrapper.update(kind='documentary_count',schema_version='1',value=value,unit=unit,
                   meaning='Cuenta '+unit+' del par y foco seleccionados en el corpus fijado; no cuenta cambios materiales ni acredita vigencia jurídica. Cero filas no acredita ausencia de cambios.',
                   scope_verified=True,
                   semantic_mapping='Explicit documentary unit only; unrestricted question-to-SQL entailment is not verified.')
    return wrapper


@dataclass
class Tool:
    call: object
    mode: str
    # Trusted server binding only; never copied from a tool result or HTTP body.
    expected_snapshot: str | None = None
    mapped_from_snapshot: str | None = None
    mapping_sha256: str | None = None

    def __post_init__(self):
        if self.mode not in ('real', 'fixture') or not callable(self.call):
            raise ValueError('invalid_tool')


@dataclass
class Session:
    actor: dict
    context: dict
    snapshot: str
    originals: dict
    processing_status: str = 'ready'
    # Server-owned, bounded conversational memory. Never an evidence source.
    history: dict = field(default_factory=dict)

    def memory_key(self, context):
        return digest({'snapshot':self.snapshot, 'family':context['family'],
                       'pair':context['pair'], 'provision':context['selected_provision_id'],
                       'target_date':context.get('target_date')})

    def memory(self, context):
        return deepcopy(self.history.get(self.memory_key(context), []))

    def remember(self, context, question, answer):
        key=self.memory_key(context)
        turns=self.history.pop(key, [])
        turns.append({'question':question[:2000], 'answer':answer[:4000]})
        self.history[key]=turns[-4:]
        while len(self.history)>8:
            del self.history[next(iter(self.history))]


class Conversation:
    def __init__(self, *, tools, generator, generator_mode, process_context=None):
        if not set(tools).issubset({'rag', 'genie', 'comparison'}):
            raise ValueError('unknown_tool')
        if generator_mode not in ('fixture', 'real'):
            raise ValueError('invalid_generator_mode')
        self.tools, self.generator = dict(tools), generator
        self.generator_mode = generator_mode
        self.process_context = process_context
        self.instructions = RESOURCE.read_text()
        self.schema = json.loads(Path(__file__).with_name('GeneratedClaims.json').read_text())
        self.generated_validator = Draft202012Validator(self.schema)

    def ask_many(self, session, question, *, focuses):
        """Cross-family wrapper; each Answer retains its own pair and citations.

        Server supplies at most two explicit contexts. No synthetic merged pack
        and no inferred cross-family legal conclusion. Original focus survives.
        """
        if not isinstance(focuses,list) or not 1 <= len(focuses) <= 2:
            raise ValueError('invalid_focus_count')
        answers=[]
        for focus in focuses:
            scoped=Session(deepcopy(session.actor),deepcopy(session.context),
                           session.snapshot,session.originals,session.processing_status,history=session.history)
            answers.append(self.ask(scoped,question,focus=focus))
        statuses={a['status'] for a in answers}
        return {'status':next(iter(statuses)) if len(statuses)==1 and statuses.issubset({'answered','answered_structured'}) else 'partial',
                'answers':answers,'limitations':['Separate evidence pairs; no cross-family applicability inferred.']}

    def ask(self, session, question, *, focus=None):
        """focus is server-resolved QueryContext, never a raw client role/pair.

        Fixed routing inspects only the user question. Retrieved documents and
        generated output cannot schedule tools. At most one call per route and
        one generator invocation. State mutation is limited to authorized focus.
        """
        ctx = deepcopy(focus if focus is not None else session.context)
        trace = {'skill':'SK07', 'version':'0.1.6', 'routes':[],
                 'calls':{'real':{}, 'fixture':{}}, 'tools':{},
                 'instructions_sha256':hashlib.sha256(self.instructions.encode()).hexdigest(),
                 'schema_sha256':digest(self.schema), 'e2e_verified':False}
        limits=[]
        def result(status, answer=None):
            return {'status':status,'answer':answer,'focus':ctx,'limitations':list(dict.fromkeys(limits)), 'trace':trace}
        if not validate_contract('QueryContext',ctx)['valid']:
            return result('clarification_required')
        if not isinstance(question,str) or not question.strip():
            return result('clarification_required')
        if not authorize(session.actor,'chat',{'family':ctx['family'],'processing_status':session.processing_status})['valid']:
            return result('denied')
        session.context=deepcopy(ctx)
        q=question.casefold()
        if re.search(r'ese punto|esa disposición|ese artículo',q) and not ctx['selected_provision_id']:
            return result('clarification_required')
        intent=route_intent(question)
        counts,comparison,implications,pure_count=(intent[k] for k in ('counts','comparison','implications','pure_count'))
        routes=(['genie'] if counts else []) + (['rag'] if not pure_count and (comparison or implications or not counts) else [])
        if not pure_count and comparison and 'comparison' in self.tools:routes.append('comparison')
        trace['routes']=routes
        outputs={}; expected_snapshots={}
        for route in routes:
            tool=self.tools.get(route)
            if tool is None:
                limits.append(route+':unavailable');continue
            expected_snapshot=session.snapshot; mapping=None
            if any(value is not None for value in (tool.expected_snapshot,tool.mapped_from_snapshot,tool.mapping_sha256)):
                if (route!='genie' or tool.mapped_from_snapshot!=session.snapshot
                        or not isinstance(tool.expected_snapshot,str) or not re.fullmatch(r'[0-9a-f]{64}',tool.expected_snapshot)
                        or not isinstance(tool.mapping_sha256,str) or not re.fullmatch(r'[0-9a-f]{64}',tool.mapping_sha256)):
                    limits.append(route+':server_snapshot_mapping_invalid');return result('conflict')
                expected_snapshot=tool.expected_snapshot
                mapping={'source_snapshot':session.snapshot,'expected_snapshot':expected_snapshot,'mapping_sha256':tool.mapping_sha256,
                         'authority':'verified_server_binding; independent publication still required'}
            expected_snapshots[route]=expected_snapshot
            trace['calls'][tool.mode][route]=1
            try:
                output=tool.call(question,deepcopy(ctx))
                if not isinstance(output,dict):raise ValueError('invalid_tool_output')
            except TimeoutError:output={'status':'timeout'}
            except PermissionError:output={'status':'denied'}
            except Exception:output={'status':'error'}
            trace['tools'][route]={'status':output.get('status'), 'mode':tool.mode,
                                   'trace':deepcopy(output.get('trace',{}))}
            if mapping is not None:trace['tools'][route]['snapshot_mapping']=mapping
            status=output.get('status')
            if status in ('denied','access_denied'):return result('denied')
            if status=='conflict' or (output.get('snapshot') is not None and output['snapshot']!=expected_snapshot):
                limits.append(route+':snapshot_conflict');return result('conflict')
            if status not in ('completed','partial','ready'):
                limits.append(route+':'+str(status));continue
            if route=='genie' and (output.get('context')!=ctx or output.get('scope_verified') is not True):
                limits.append('genie:context_mismatch');return result('conflict')
            if output.get('snapshot') is None:
                limits.append(route+':snapshot_unverified');continue
            tool_limits=output.get('limitations',[])
            if not isinstance(tool_limits,list) or any(not isinstance(item,str) for item in tool_limits):
                limits.append(route+':invalid_limitations');continue
            limits.extend(tool_limits)
            if status not in ('completed','partial','ready'):
                limits.append(route+':'+str(status));continue
            if output.get('conflicts'):
                limits.append(route+':source_conflict');return result('conflict')
            outputs[route]=deepcopy(output)
        if pure_count:
            wrapper=_documentary_count(outputs.get('genie'),ctx,expected_snapshots.get('genie',session.snapshot))
            if wrapper is None:
                limits.append('genie:typed_documentary_count_unavailable')
                return result('structured_result_unavailable')
            # Lexical gates are conservative routing aids, not semantic proof.
            unsupported=bool(re.search(r'cambi|material|oblig|incumpl|riesgo|vigent|\bnormas?\b',q))
            wants_documents=bool(re.search(r'document|version',q))
            wants_provisions=bool(re.search(r'disposici|art[ií]cul',q))
            explicit_count=bool(re.search(r'cu[aá]nt|conteo|cantidad',q))
            explicit_unit=wants_documents or wants_provisions or bool(re.search(r'\b(?:filas?|registros?)\b',q))
            if (unsupported or not explicit_count or not explicit_unit or
                    (wants_documents and wrapper['reference_query_id']!='document_count') or
                    (wants_provisions and wrapper['reference_query_id']!='provision_count')):
                limits.append('requested_meaning_not_answered_by_documentary_count')
                return {**result('scope_not_answered'),'available_meaning':wrapper['meaning']}
            trace['display_policy']='typed_documentary_count; no normative Answer or generator'
            return {**result('answered_structured'),'structured_result':wrapper}
        pack=outputs.get('rag',{}).get('evidence')
        if pack is None:
            pack={'evidence_id':str(uuid4()),'evidence_version':'1','pair':ctx['pair'],
                  'citations':[],'coverage':'partial','limitations':['no_normative_evidence'],
                  'synthetic':self.generator_mode=='fixture'}
        if not validate_contract('EvidencePack',pack)['valid']:
            return result('invalid_evidence')
        if pack.get('pair')!=ctx['pair']:
            limits.append('evidence_pair_conflict');return result('conflict')
        if 'comparison' in outputs:
            changes=outputs['comparison'].get('change_set',{})
            if changes.get('pair')!=ctx['pair']:
                limits.append('comparison_pair_conflict');return result('conflict')
        limits.extend(pack.get('limitations',[]))
        identities={(c['document_id'],c['version_id']) for c in pack.get('citations',[])}
        pair_ids={(ctx['pair'][side]['document_id'],ctx['pair'][side]['version_id']) for side in ('before','after')}
        if comparison and not pair_ids.issubset(identities):
            limits.append('missing_comparison_counterpart');return result('insufficient_evidence')
        if not outputs or (not counts and not pack['citations']):return result('insufficient_evidence')
        if counts and not pack['citations']:
            limits.append('mixed_request_requires_normative_evidence')
            return result('insufficient_evidence')
        answer_id=str(uuid4())
        skeleton={'answer_id':answer_id,'context_id':ctx['context_id'],'evidence':pack,
                  'processing_status':'partial' if limits else 'ready','review_status':'proposed' if implications else 'unreviewed',
                  'text':'Validación de evidencia antes de generar.','material_claims':[], 'limitations':list(dict.fromkeys(limits))}
        checked=validate_answer(skeleton,pack,session.originals)
        if not checked['valid']:
            trace['validation']=checked;return result('invalid_evidence')
        data={'question':question,'context':ctx,'evidence':pack,
              'conversation_memory':{'trust':'untrusted_context_not_evidence',
                                     'turns':session.memory(ctx),
                                     'policy':'Use only to resolve follow-up references. All claims require current EvidencePack citations.'},
              'tool_results':outputs,'implications':implications,'limitations':skeleton['limitations'],
              'scope':'En las copias comparadas; vigencia actual no establecida.'}
        if self.process_context is not None:data['fictitious_process_context']=self.process_context(ctx)
        from sbs.conversation.compaction import compact_input
        original_chars=len(json.dumps(data,ensure_ascii=False))
        data=compact_input(data)
        trace['input_compaction']={'original_chars':original_chars,'compacted_chars':len(json.dumps(data,ensure_ascii=False)),'replacement_count':data['compaction']['replacement_count'],'tool_results_sha256':data['compaction']['original_tool_results_sha256']}
        req={'messages':[{'role':'system','content':self.instructions+'\nContrato interno GeneratedClaims del servidor:\n'+json.dumps(self.schema,ensure_ascii=False)},
                         {'role':'user','content':json.dumps(data,ensure_ascii=False)}], 'schema':deepcopy(self.schema)}
        trace['input_sha256']=digest(req)
        trace['calls'][self.generator_mode]['generator']=1
        try:
            answer=self.generator(deepcopy(req))
            if isinstance(answer,str):answer=json.loads(answer)
        except Exception:
            limits.append('generator:error');return result('generation_error')
        trace['generator']=deepcopy(getattr(self.generator,'last_attempt',{'mode':self.generator_mode}))
        if not isinstance(answer,dict) or not self.generated_validator.is_valid(answer):
            return result('invalid_generation')
        generated=answer
        merged_limits=list(dict.fromkeys(skeleton['limitations']+generated['limitations']))
        answer={**deepcopy(skeleton),
                'material_claims':deepcopy(generated['material_claims']),
                'text':'\n\n'.join(claim['text'] for claim in generated['material_claims']),
                'limitations':merged_limits,
                'processing_status':'partial' if merged_limits else 'ready'}
        # The model supplies no identity, evidence, actor, review or status fields.
        checked=validate_answer(answer,pack,session.originals)
        trace['validation']=checked
        if checked['valid']:
            answer=deepcopy(answer)
            answer['text']='\n\n'.join(claim['text'] for claim in answer['material_claims'])
            trace['display_policy']='text_derived_from_cited_claims; semantic_entailment_not_verified'
            session.remember(ctx,question,answer['text'])
        return result('answered' if checked['valid'] else 'invalid_generation',answer if checked['valid'] else None)
