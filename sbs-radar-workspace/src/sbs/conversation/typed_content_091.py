"""Opt-in observed GPT-OSS typed blocks; no change to provider or guardrails."""
from copy import deepcopy
from pathlib import Path
import json
from jsonschema import Draft202012Validator
from .databricks import SingleShotTransport
from .generation_contract_086 import CapturingTransport,write_once,sha
from .json_wrapper_088 import unwrap_json_object


def normalize_response(response,expected_model):
    if not isinstance(response,dict) or response.get('model')!=expected_model:
        raise ValueError('TYPED_MODEL_MISMATCH')
    choices=response.get('choices')
    if not isinstance(choices,list) or len(choices)!=1 or not isinstance(choices[0],dict):
        raise ValueError('TYPED_CHOICES_INVALID')
    choice=choices[0]
    if choice.get('finish_reason')!='stop':raise ValueError('TYPED_FINISH_NOT_STOP')
    message=choice.get('message')
    if not isinstance(message,dict):raise ValueError('TYPED_MESSAGE_INVALID')
    content=message.get('content')
    if not isinstance(content,list) or not content:raise ValueError('TYPED_CONTENT_NOT_BLOCKS')
    texts=[];indices=[];reasoning_count=0
    for index,block in enumerate(content):
        if not isinstance(block,dict):raise ValueError('TYPED_BLOCK_INVALID')
        kind=block.get('type')
        if kind=='text':
            if set(block)!={'type','text'} or not isinstance(block['text'],str):raise ValueError('TYPED_TEXT_INVALID')
            texts.append(block['text']);indices.append(index)
        elif kind=='reasoning':
            if set(block)!={'type','summary'} or not isinstance(block['summary'],list):raise ValueError('TYPED_REASONING_SHAPE_INVALID')
            for summary in block['summary']:
                if not isinstance(summary,dict) or set(summary)!={'type','text'} or summary['type']!='summary_text' or not isinstance(summary['text'],str):
                    raise ValueError('TYPED_REASONING_SHAPE_INVALID')
            reasoning_count+=1
        else:raise ValueError('TYPED_BLOCK_UNSUPPORTED')
    if not texts or not ''.join(texts).strip():raise ValueError('TYPED_TEXT_MISSING')
    # No separator insertion, substring extraction, content repair or reasoning.
    normalized,wrapper=unwrap_json_object(''.join(texts))
    result=deepcopy(response);result['choices'][0]['message']['content']=normalized
    return result,dict(status='normalized_pending_contract_validation',text_block_indices=indices,reasoning_blocks_excluded=reasoning_count,normalization='ordered_text_blocks_only',wrapper=wrapper,quality_accepted=False)


class TypedCaptureTransport(SingleShotTransport):
    def __init__(self,delegate,directory,*,expected_response_model):
        self.capture=CapturingTransport(delegate,directory)
        self.directory=Path(directory);self.expected_model=expected_response_model
        self.last_attempt={}
    def __call__(self,body):
        try:response=self.capture(body)
        finally:self.last_attempt=dict(self.capture.last_attempt)
        self.last_attempt['stage']='typed_content'
        try:normalized,metadata=normalize_response(response,self.expected_model)
        except ValueError as error:
            metadata=dict(status='rejected',code=str(error),quality_accepted=False)
            self.last_attempt['typed_content']=metadata
            write_once(self.directory,'normalization.json',metadata)
            raise
        write_once(self.directory,'normalization.json',metadata)
        self.last_attempt['typed_content']=metadata
        return normalized


def validate_candidate(generated,body):
    """Actual GeneratedClaims, QueryContext, Answer and original quote validators.

    This is technical validation only. It does not measure semantic entailment.
    LocalService loads verified source artifacts but never initializes models.
    """
    from sbs.contracts import validate_contract
    from sbs.guardrails import validate_answer
    from sbs.runtime import LocalService
    schema=json.loads(Path(__file__).with_name('GeneratedClaims.json').read_bytes())
    errors=[dict(path=list(e.absolute_path),validator=e.validator) for e in Draft202012Validator(schema).iter_errors(generated)]
    common=dict(quality_accepted=False,semantic_entailment='not_evaluated',new_embedding_posts=0,e2e=False)
    if errors:return dict(status='generated_contract_rejected',schema_errors=errors,**common)
    data=json.loads(body['messages'][1]['content']);pack=data['evidence'];context=data['context']
    if not validate_contract('QueryContext',context)['valid'] or pack['pair']!=context['pair']:raise ValueError('TYPED_CONTEXT_CONFLICT')
    service=LocalService(mode='local')
    if service.generator is not None or service.embedding is not None:raise ValueError('TYPED_MODEL_INITIALIZED')
    limits=list(dict.fromkeys(data['limitations']+generated['limitations']))
    answer=dict(answer_id='candidate-091-technical-validation',context_id=context['context_id'],evidence=deepcopy(pack),processing_status='partial' if limits else 'ready',review_status='proposed' if data['implications'] else 'unreviewed',text='\n\n'.join(c['text'] for c in generated['material_claims']),material_claims=deepcopy(generated['material_claims']),limitations=limits)
    checked=validate_answer(answer,pack,service.originals)
    return dict(status='technical_answer_candidate' if checked['valid'] else 'answer_contract_rejected',generatedclaims_schema_valid=True,answer_validation=checked,answer=answer if checked['valid'] else None,snapshot=service.snapshot,**common)


def replay(directory,body,expected_model):
    directory=Path(directory)
    raw=(directory/'response.json').read_bytes()
    manifest=json.loads((directory/'response-manifest.json').read_bytes())
    if sha(raw)!=manifest['file_sha256']:raise ValueError('TYPED_RESPONSE_DRIFT')
    normalized,metadata=normalize_response(json.loads(raw),expected_model)
    result=validate_candidate(json.loads(normalized['choices'][0]['message']['content']),body)
    return dict(result,source_response_sha256=sha(raw),normalization=metadata,remote_calls=0,new_inferences=0)
