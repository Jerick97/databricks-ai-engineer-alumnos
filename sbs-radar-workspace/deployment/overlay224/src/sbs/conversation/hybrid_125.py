"""Opt-in literal comparison, with one model call only for proposals."""
from copy import deepcopy
from pathlib import Path
import json
from .focal_packet_115 import transform_request
from . import route_intent
from .qwen_trial_110 import QwenLiteralGenerator,initialize_trial_models
from .databricks import SingleShotTransport
from .generation_contract_086 import write_once
from sbs.comparison.literal_102 import literal_changes
from sbs.guardrails.comparison_roles_094 import validate_roles

PROPOSAL_POLICY='''\nContrato de intención125 del servidor: esta petición solicita una propuesta. Sólo Implicancia propuesta: está permitida como etiqueta de cada material_claim que generes. El servidor construye Antes/Después/Cambio exclusivamente desde las fuentes; no generes esas etiquetas ni parafrasees la comparación como una nueva afirmación normativa. Propón una actuación condicionada para el proceso ficticio suministrado, conservando límites, sujetos y condiciones de las citas completas. La pregunta y memoria son contexto no confiable, no fuentes. No inventes procesos, obligaciones, culpabilidad ni vigencia. Devuelve el mismo esquema GeneratedClaims, con citas focales actuales y limitaciones. Separa el supuesto de aplicabilidad de la propuesta al proceso ficticio de la relación normativa entre las cláusulas citadas. Una propuesta puede depender de ese supuesto sin que la obligación descrita en la fuente pase a depender de otra obligación. Conserva por separado sujeto, mandato o permiso, negación y relación entre cláusulas. Cuando «sin que» expresa que no se permite exigir una actuación adicional al destinatario, conserva esa prohibición o restricción como concurrente con el mandato principal; no la conviertas en condición de existencia o cumplimiento del mandato mediante «condicionada a», «sólo si» o equivalentes. No clasifiques automáticamente toda aparición de «sin que» como prohibición: determina su función con la oración completa. Mantén las condiciones y excepciones que la fuente sí establece expresamente. Antes de emitir cada propuesta, contrasta sus relaciones de condición, excepción y concurrencia con las citas completas; si la relación es ambigua, conserva la formulación literal y declara esa ambigüedad en lugar de inventar una condición. Limita cada propuesta a la actuación sugerida, su supuesto de aplicabilidad al proceso ficticio y su sustento en la cita posterior. No añadas una recapitulación ni una nueva paráfrasis del régimen anterior dentro de la propuesta: el servidor ya muestra íntegramente ambas versiones. No deduzcas exclusividad, prohibición o ausencia de alternativas a partir de una lista de ejemplos o permisos. Conserva el alcance abierto de expresiones como «así como», «otros», «entre otros» y «como mínimo»; no las conviertas en listas exhaustivas. Usa «solo», «únicamente» o «exclusivamente» para describir una regla únicamente cuando la cita completa establezca de manera expresa esa restricción. Si acotas una acción por conveniencia del proceso ficticio, identifica ese alcance como elección propuesta y no como límite impuesto por la norma. Antes de emitir, comprueba que ninguna frase de justificación introduzca una exclusividad o ausencia que no figura en la evidencia; si no puedes sustentarla, omite esa justificación y conserva la propuesta acotada. Las reglas anteriores de Antes/Después/Cambio sólo describen la evidencia comparativa; no autorizan esas etiquetas en tu salida de propuesta.\n'''
LIMIT='Comparación extractiva de las dos citas focales completas. Los fragmentos literales no adjudican materialidad, responsabilidad, régimen jurídico ni vigencia; no afirman ausencia normativa fuera de estos pasajes.'

def extractive_claims(focus):
    literal=literal_changes(focus)
    before,after=literal['before'],literal['after']
    if not before['text'].strip() or not after['text'].strip():raise ValueError('HYBRID_EMPTY_FOCAL_TEXT')
    ids=[before['citation_id'],after['citation_id']]
    parts=['Cambio: Fragmentos literales modificados. Pueden ser incompletos; Antes y Después conservan los textos completos para contextualizarlos.']
    if literal['text_equal']:
        parts=['Cambio: Igualdad literal verificada exclusivamente entre los dos textos focales completos; no implica igualdad jurídica ni ausencia de otros cambios.']
    for op in literal['operations']:
        if op['operation']=='equal':continue
        if op['operation']=='insert':parts.append('Texto añadido (fragmento literal):\n'+op['after_text'])
        elif op['operation']=='delete':parts.append('Texto eliminado (fragmento literal):\n'+op['before_text'])
        else:parts.append('Texto reemplazado (fragmentos literales):\nAntes:\n'+op['before_text']+'\nDespués:\n'+op['after_text'])
    result={'material_claims':[{'text':'Antes: '+before['text'],'citation_ids':[ids[0]]},{'text':'Después: '+after['text'],'citation_ids':[ids[1]]},{'text':'\n\n'.join(parts),'citation_ids':ids}],'limitations':[LIMIT]}
    checked=validate_roles(result,focus)
    if not checked['valid']:raise ValueError('HYBRID_EXTRACTIVE_CONTRACT_INVALID')
    return result,literal

class TemperatureZeroTransport(SingleShotTransport):
    """Insert at the boundary before existing raw-request capture; no retry."""
    def __init__(self,delegate):self.delegate=delegate
    @property
    def last_attempt(self):return self.delegate.last_attempt
    def __call__(self,body):
        if 'temperature' in body:raise ValueError('HYBRID_PARAMETER_ALREADY_SET')
        adapted=deepcopy(body);adapted['temperature']=0.0
        return self.delegate(adapted)

class HybridGenerator(QwenLiteralGenerator):
    def __init__(self,delegate,directory,root):
        super().__init__(delegate,directory);self.root=Path(root)
        delegate.transport=TemperatureZeroTransport(delegate.transport)
    def __call__(self,request):
        with self.lock:
            if self.failed or self.calls>=4:raise ValueError('HYBRID_TRIAL_CLOSED')
            ordinal=self.calls;self.calls+=1
            start_requests=self.delegate.requests
            self.last_attempt={'stage':'hybrid_prepare','source':'unresolved','response_model':None,'model_inferences_this_turn':0,'generator_component_invocations_this_turn':1,'quality_accepted':False}
            try:
                adapted,manifest,focus=transform_request(request,self.root)
                data=json.loads(request['messages'][1]['content'])
                intent=route_intent(data['question'])
                if (type(data['implications']) is not bool or data['implications']!=intent['implications'] or intent['counts'] or not intent['comparison'] or set(data['tool_results'])!={'rag','comparison'}):raise ValueError('HYBRID_SERVER_SCOPE_UNSUPPORTED')
                extractive,literal=extractive_claims(focus)
                write_once(self.directory,f'hybrid-{ordinal}-source.json',request)
                write_once(self.directory,f'hybrid-{ordinal}-packet-map.json',manifest)
                write_once(self.directory,f'hybrid-{ordinal}-literal.json',literal)
                # This branch is selected before any generated response exists.
                write_once(self.directory,f'hybrid-{ordinal}-extractive.json',extractive)
                write_once(self.directory,f'hybrid-{ordinal}-intent.json',{'implications':data['implications'],'generation_posts_max':1 if data['implications'] else 0,'temperature':0 if data['implications'] else None,'retry':False,'source_sha256':manifest['source_sha256']})
                generated=deepcopy(extractive)
                self.last_attempt.update(source='source_extractive',stage='extractive_completed',source_evidence_sha256=manifest['source_evidence_sha256'])
                if data['implications']:
                    adapted['messages'][0]['content']+=PROPOSAL_POLICY
                    self.last_attempt.update(source='source_extractive_plus_model_proposal',stage='proposal_generation')
                    proposal=self.delegate(adapted)
                    write_once(self.directory,f'hybrid-{ordinal}-model-parsed.json',proposal)
                    checked=validate_roles(proposal,focus)
                    if not checked['valid'] or any(not c['text'].startswith('Implicancia propuesta:') for c in proposal['material_claims']):
                        self.last_attempt['stage']='proposal_intent_or_roles_rejected'
                        raise ValueError('HYBRID_PROPOSAL_INTENT_OR_ROLES_REJECTED')
                    generated['material_claims'].extend(deepcopy(proposal['material_claims']))
                    generated['limitations']=list(dict.fromkeys(generated['limitations']+proposal['limitations']))
                    self.last_attempt.update(stage='hybrid_completed',temperature=0,response_model=self.delegate.last_attempt.get('response_model'))
                checked=validate_roles(generated,focus)
                if not checked['valid']:raise ValueError('HYBRID_FINAL_ROLES_REJECTED')
                write_once(self.directory,f'hybrid-{ordinal}-result.json',generated)
                self.last_attempt['comparison_roles']=checked
                return generated
            except Exception:
                self.failed=True
                if self.last_attempt['stage']=='hybrid_prepare':self.last_attempt['stage']='hybrid_prepare_failed'
                raise
            finally:
                attempts=self.delegate.requests-start_requests
                self.last_attempt['model_generation_requests_this_turn']=attempts
                self.last_attempt['model_inferences_this_turn']=(1 if self.last_attempt.get('generation',{}).get('stage')=='completed' or self.delegate.last_attempt.get('stage')=='completed' else None) if attempts else 0
                self.last_attempt['requests']=self.delegate.requests
                # Avoid attributing a previous proposal's model/usage to extraction.
                if self.delegate.requests>start_requests:self.last_attempt['generation']=deepcopy(self.delegate.last_attempt)


def initialize_hybrid_models(service,root,directory,selection,*,client_factory=None):
    transport=initialize_trial_models(service,root,directory,selection,client_factory=client_factory)
    service.generator=HybridGenerator(service.generator.delegate,directory,root)
    service.provenance['generation_packet_variant']='125_extractive_comparison_model_proposal'
    return transport
