"""SK08 v0.1.0 deterministic local policy, not authentication or legal review.

`actor` MUST come exclusively from a verified server adapter (SK10). Copying
client fields into it invalidates this trust boundary. Resource fields are
server-resolved metadata; any client_payload / actor_role / corpus text is data.
Apply authorization before retrieval/model/reranker and again before source
opening or writes. Cache keys must retain that server authorization scope.

Permission to approve is only a role/family check; saving approval additionally
requires exact evidence validation, authorized transition and immutable record
binding in SK10. This module does not persist or approve anything.
"""
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import TypedDict
from urllib.parse import urlsplit

from sbs.contracts import validate_contract


class ValidationResult(TypedDict):
    valid: bool
    errors: list[dict[str, str]]


_POLICY = json.loads((Path(__file__).resolve().parents[3] / 'config/permissions.json').read_text())


def _result(code=None, path='') -> ValidationResult:
    # SK01's closed ValidationResult has no code field; message is a stable code.
    return {'valid': code is None, 'errors': [] if code is None else [
        {'path': path, 'phase': 'semantic', 'message': code}
    ]}


def authorize(actor: dict, action: str, resource: dict) -> ValidationResult:
    """Check server principal role and family; never read identity from resource.

    Actor shape: authenticated literal True, role, families list. No wildcard
    role/family exists. This is policy permission, not a saved review decision.
    """
    if not isinstance(actor, dict) or actor.get('authenticated') is not True:
        return _result('AUTHENTICATION_REQUIRED', '/actor/authenticated')
    role = actor.get('role')
    if not isinstance(role, str) or role not in _POLICY['roles']:
        return _result('ROLE_DENIED', '/actor/role')
    if not isinstance(action, str) or action not in _POLICY['roles'][role]:
        return _result('ACTION_DENIED', '/action')
    families = actor.get('families')
    family = resource.get('family') if isinstance(resource, dict) else None
    if (not isinstance(families, list) or not isinstance(family, str)
            or family not in _POLICY['families'] or family not in families):
        return _result('FAMILY_DENIED', '/resource/family')
    if (action in _POLICY['query_actions']
            and resource.get('processing_status') not in _POLICY['query_processing_statuses']):
        return _result('PROCESSING_NOT_QUERYABLE', '/resource/processing_status')
    return _result()


def check_tool_call(actor: dict, tool: str, resource: dict) -> ValidationResult:
    """Allow only configured tool/action pairs; corpus instructions grant nothing.

    Caller supplies a structured tool identifier separately from untrusted text.
    No lexical prompt-injection detector or model compliance claim is made.
    """
    if not isinstance(tool, str) or tool not in _POLICY['tools']:
        return _result('TOOL_DENIED', '/tool')
    return authorize(actor, _POLICY['tools'][tool], resource)


def check_source_url(url: str, allowed_hosts) -> ValidationResult:
    """Check one URL; every redirect must call this function independently.

    Exact ASCII hosts, HTTPS, absent/default 443 port, no userinfo. Hosts are
    trusted caller configuration, not payload. No network occurs. DNS/IP checks,
    rebinding resistance and connection/redirect enforcement remain SK02 work;
    URL validation alone does NOT establish SSRF protection.
    """
    if (not isinstance(url, str) or re.search(r'[^\x21-\x7e]|[<>"{}|\\^`]', url)
            or re.search(r'%(?![0-9A-Fa-f]{2})', url)):
        return _result('URL_SYNTAX_DENIED', '/url')
    if (not isinstance(allowed_hosts, (list, tuple, set, frozenset))
            or not all(isinstance(host, str) for host in allowed_hosts)):
        return _result('HOST_POLICY_INVALID', '/allowed_hosts')
    try:
        parsed = urlsplit(url)
        if parsed.scheme != 'https' or not parsed.hostname:
            return _result('HTTPS_REQUIRED', '/url')
        if parsed.username is not None or parsed.password is not None:
            return _result('USERINFO_DENIED', '/url')
        if parsed.port not in (None, 443) or parsed.netloc.endswith(':'):
            return _result('PORT_DENIED', '/url')
        if parsed.hostname.lower() not in {host.lower() for host in allowed_hosts}:
            return _result('HOST_DENIED', '/url')
        # Avoid encoded hosts and ambiguous non-DNS forms even if misconfigured.
        if not re.fullmatch(r'[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?)*', parsed.hostname):
            return _result('HOST_SYNTAX_DENIED', '/url')
    except ValueError:
        return _result('URL_SYNTAX_DENIED', '/url')
    return _result()


def validate_answer(answer: dict, evidence: dict, originals: Mapping) -> ValidationResult:
    """Validate SK01 and literal quotes at Python string [start:end] offsets.

    Originals maps (document_id, version_id) tuples to trusted raw Unicode text;
    no whitespace normalization or version fallback. The caller must establish
    original provenance. Neither exact quotes nor complete coverage prove that
    prose entails a legal conclusion, that a rule is in force, or that a human
    approved institutional impact. Page and provision metadata need an SK02
    source map; raw character offsets alone cannot verify those fields. This
    check does not establish exhaustive material claims. Inputs are not mutated.
    """
    errors = []
    for kind, payload, prefix in [('Answer', answer, '/answer'), ('EvidencePack', evidence, '/evidence')]:
        checked = validate_contract(kind, payload)
        errors.extend({**error, 'path': prefix + error['path'],
                       'message': 'CONTRACT_INVALID: ' + error['message']} for error in checked['errors'])
    if errors:
        return {'valid': False, 'errors': errors}
    if answer['evidence'] != evidence:
        return _result('EVIDENCE_MISMATCH', '/answer/evidence')
    if evidence['coverage'] == 'partial' and not answer['limitations']:
        return _result('PARTIAL_EVIDENCE_LIMITATIONS_REQUIRED', '/answer/limitations')
    if not isinstance(originals, Mapping):
        return _result('ORIGINALS_REQUIRED', '/originals')
    for index, citation in enumerate(evidence['citations']):
        original = originals.get((citation['document_id'], citation['version_id']))
        path = '/evidence/citations/' + str(index)
        if not isinstance(original, str):
            errors.extend(_result('ORIGINAL_VERSION_MISSING', path)['errors'])
        elif citation['end'] > len(original) or original[citation['start']:citation['end']] != citation['text']:
            errors.extend(_result('QUOTE_OFFSET_MISMATCH', path)['errors'])
    return {'valid': not errors, 'errors': errors}
