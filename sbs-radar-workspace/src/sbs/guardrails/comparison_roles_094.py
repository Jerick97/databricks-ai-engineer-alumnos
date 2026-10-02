"""Additive deterministic citation roles; no semantic entailment claim."""
from pathlib import Path
import json
from jsonschema import Draft202012Validator
SCHEMA=Path(__file__).resolve().parents[1]/'conversation/GeneratedClaims.json'

def validate_roles(generated,focus):
    errors=[]
    if not Draft202012Validator(json.loads(SCHEMA.read_bytes())).is_valid(generated):
        return dict(valid=False,errors=[{'code':'GENERATED_SCHEMA_INVALID'}],semantic_entailment='not_evaluated')
    by_id={c['citation_id']:c for c in focus['citations']}
    for index,claim in enumerate(generated['material_claims']):
        ids=claim['citation_ids'];label=claim['text'].split(':',1)[0]
        if any(cid not in by_id for cid in ids):
            errors.append(dict(claim=index,code='CLAIM_CITATION_OUTSIDE_FOCUS'));continue
        sides={by_id[cid]['side'] for cid in ids}
        expected={'Antes':{'before'},'Después':{'after'},'Cambio':{'before','after'}}.get(label)
        if expected is not None and sides!=expected:
            errors.append(dict(claim=index,code='CLAIM_CITATION_ROLE_MISMATCH',label=label,expected_sides=sorted(expected),observed_sides=sorted(sides)))
        if label=='Cambio' and {by_id[cid]['side'] for cid in ids if by_id[cid]['role']=='focal'}!={'before','after'}:
            errors.append(dict(claim=index,code='COMPARISON_FOCAL_CITATIONS_REQUIRED'))
        if label=='Cambio' and not focus['comparison_available']:
            errors.append(dict(claim=index,code='COMPARISON_COUNTERPART_MISSING'))
    return dict(valid=not errors,errors=errors,semantic_entailment='not_evaluated')
