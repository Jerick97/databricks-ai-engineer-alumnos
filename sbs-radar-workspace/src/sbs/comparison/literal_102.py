"""Raw focal 1:1 edit operations. Unicode offsets, no materiality judgment.

Existing SK03 compare classifies provision-level differences but has no opcode
API. This additive view preserves its exact-text principle and hash helper.
"""
from copy import deepcopy
from difflib import SequenceMatcher
import re
from . import _hash

def literal_changes(focus):
    sides={side:[c for c in focus['citations'] if c['role']=='focal' and c['side']==side] for side in ('before','after')}
    if any(len(v)!=1 for v in sides.values()):raise ValueError('LITERAL_UNIQUE_FOCAL_PAIR_REQUIRED')
    before,after=(deepcopy(sides[s][0]) for s in ('before','after'))
    if sum(len(c['text']) for c in (before,after))>120000:raise ValueError('LITERAL_INPUT_LIMIT')
    for side,c in [('before',before),('after',after)]:
        if {k:c[k] for k in ('document_id','version_id')}!=focus['pair'][side] or c['provision_id']!=focus['selected_provision_id'] or c['end']-c['start']!=len(c['text']):raise ValueError('LITERAL_IDENTITY_OR_OFFSETS_INVALID')
    tokens=[re.findall(r'\s+|[^\s]+',c['text']) for c in (before,after)]
    offsets=[]
    for sequence in tokens:
        points=[0]
        for token in sequence:points.append(points[-1]+len(token))
        offsets.append(points)
    operations=[]
    for tag,i,j,k,l in SequenceMatcher(None,*tokens,autojunk=False).get_opcodes():
        a,b,c,d=offsets[0][i],offsets[0][j],offsets[1][k],offsets[1][l]
        operations.append(dict(operation=tag,before_start=a,before_end=b,after_start=c,after_end=d,before_source_start=before['start']+a,before_source_end=before['start']+b,after_source_start=after['start']+c,after_source_end=after['start']+d,before_text=before['text'][a:b],after_text=after['text'][c:d]))
    if ''.join(o['before_text'] for o in operations)!=before['text'] or ''.join(o['after_text'] for o in operations)!=after['text']:raise ValueError('LITERAL_RECONSTRUCTION_FAILED')
    return dict(version=1,algorithm='difflib.SequenceMatcher_lossless_whitespace_tokens_autojunk_false',pair=deepcopy(focus['pair']),before=before,after=after,operations=operations,text_equal=before['text']==after['text'],input_sha256=_hash([before,after]),semantic_materiality='not_evaluated',limits='Literal differences only; no legal applicability, effective-date or materiality inference.')
