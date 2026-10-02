"""SK01 v0.1.0: local structure and consistency; never authentication.

Schema IDs pin the contract revision. Payloads cannot select schemas or resolve
remote references. IDs/approval history require immutable persistence in the
backend. No network, citation-text verification, legal conclusions or permission
checks are performed here. The caller must use SK08 before accepting a review.
"""
import json
import re
from datetime import datetime
from urllib.parse import urlsplit
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker

_CONTRACT_ROOT = Path(__file__).resolve().parents[2] / 'contracts'
_KINDS = frozenset({'SourceDocument', 'Provision', 'VersionPair', 'ChangeSet',
                    'EvidencePack', 'QueryContext', 'Answer', 'ReviewDecision',
                    'RunRecord', 'ModelBundle', 'ValidationResult'})


_FORMATS = FormatChecker()


@_FORMATS.checks('date-time', raises=(ValueError,))
def _date_time(value):
    # Explicit RFC3339 profile: offset required, seconds required, no leap seconds.
    if not isinstance(value, str):
        return True
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[Zz]|[+-]\d{2}:\d{2})', value):
        return False
    if value[-1] not in 'Zz':
        if int(value[-5:-3]) > 23 or int(value[-2:]) > 59:
            return False
    datetime.fromisoformat(value.upper().replace('Z', '+00:00'))
    return True


@_FORMATS.checks('uri', raises=(ValueError,))
def _source_uri(value):
    # SourceDocument uses an intentionally narrow absolute HTTP(S) URI profile.
    # Syntax validation does not allowlist or fetch this destination.
    if not isinstance(value, str):
        return True
    if re.search(r'[^\x21-\x7e]|[<>"{}|\\^`]', value) or re.search(r'%(?![0-9A-Fa-f]{2})', value):
        return False
    parsed = urlsplit(value)
    return (parsed.scheme in ('http', 'https') and bool(parsed.hostname)
            and parsed.username is None and parsed.password is None
            and (parsed.port is None or 0 < parsed.port <= 65535))


def _pointer(parts):
    return ''.join('/' + str(part).replace('~', '~0').replace('/', '~1') for part in parts)


def validate_contract(kind: str, payload: dict) -> dict:
    """Return {valid, errors}; errors use JSON Pointer paths and validation phase.

    A declared reviewer role may form a valid record but grants no authority.
    Only bundled, versioned schemas are loaded; user $ref values are data and
    are rejected by closed schemas, never followed as schema references.
    """
    errors = []

    def fail(path, message, phase='semantic'):
        errors.append({'path': path, 'phase': phase, 'message': message})

    if not isinstance(kind, str) or kind not in _KINDS:
        fail('', 'Unknown contract kind', 'structural')
        return {'valid': False, 'errors': errors}
    schema = json.loads((_CONTRACT_ROOT / (kind + '.json')).read_text())
    validator = Draft202012Validator(schema, format_checker=_FORMATS)
    for error in sorted(validator.iter_errors(payload), key=lambda e: str(list(e.absolute_path))):
        fail(_pointer(error.absolute_path), error.message, 'structural')
    if errors:
        return {'valid': False, 'errors': errors}

    def identity(reference):
        return reference['document_id'], reference['version_id']

    def check_pair(pair, path):
        if identity(pair['before']) == identity(pair['after']):
            fail(path + '/after', 'Comparison requires distinct version identities')

    def check_citation(citation, path):
        if citation['end'] <= citation['start']:
            fail(path + '/end', 'End offset must follow start offset')

    def check_pack(pack, path):
        check_pair(pack['pair'], path + '/pair')
        expected = {identity(pack['pair']['before']), identity(pack['pair']['after'])}
        found, ids = set(), set()
        for index, citation in enumerate(pack['citations']):
            cp = path + '/citations/' + str(index)
            check_citation(citation, cp)
            if citation['citation_id'] in ids:
                fail(cp + '/citation_id', 'Duplicate citation identity')
            ids.add(citation['citation_id'])
            if citation['source_kind'] != 'normative':
                fail(cp + '/source_kind', 'Comparison evidence must be normative; fictitious processes are separate')
            if identity(citation) not in expected:
                fail(cp + '/version_id', 'Citation document/version is outside comparison pair')
            found.add(identity(citation))
        if pack['coverage'] == 'complete' and not expected.issubset(found):
            fail(path + '/citations', 'Complete comparison requires both version counterparts')
        if pack['coverage'] == 'partial' and not pack['limitations']:
            fail(path + '/limitations', 'Partial evidence must state its limitations')

    if kind == 'SourceDocument':
        for field in ('published_on', 'effective_on'):
            if payload[field] is None and field not in payload['date_unknown_reasons']:
                fail('/date_unknown_reasons/' + field, 'Unknown date requires an explicit reason; capture is not publication or effect')
    elif kind == 'Provision':
        check_citation(payload, '')
    elif kind == 'VersionPair':
        check_pair(payload, '')
    elif kind == 'EvidencePack':
        check_pack(payload, '')
    elif kind == 'QueryContext':
        check_pair(payload['pair'], '/pair')
        if payload['family'] != payload['pair']['family']:
            fail('/family', 'Context family differs from comparison pair')
    elif kind in ('Answer', 'ChangeSet'):
        pack = payload['evidence']
        check_pack(pack, '/evidence')
        if kind == 'ChangeSet':
            check_pair(payload['pair'], '/pair')
            if payload['pair'] != pack['pair']:
                fail('/pair', 'Change set and evidence must use the same comparison pair')
        else:
            ids = {c['citation_id'] for c in pack['citations']}
            for index, claim in enumerate(payload['material_claims']):
                if not set(claim['citation_ids']).issubset(ids):
                    fail('/material_claims/' + str(index) + '/citation_ids', 'Claim refers to an absent citation')
            if payload['processing_status'] == 'partial' and not payload['limitations']:
                fail('/limitations', 'Partial answer must state its limitations')
        if payload['review_status'] == 'approved' and 'review' not in payload:
            fail('/review', 'Approved result requires a linked review record')
        if 'review' in payload:
            record = payload['review']
            subject_key = 'answer_id' if kind == 'Answer' else 'change_set_id'
            if record['subject_id'] != payload[subject_key]:
                fail('/review/subject_id', 'Review refers to a different subject')
            if record['review_status'] != payload['review_status']:
                fail('/review/review_status', 'Review status differs from result')
            if 'evidence_id' in record and (record['evidence_id'] != pack['evidence_id'] or record['evidence_version'] != pack['evidence_version']):
                fail('/review/evidence_version', 'Review cannot be inherited by different evidence or version')
    return {'valid': not errors, 'errors': errors}
