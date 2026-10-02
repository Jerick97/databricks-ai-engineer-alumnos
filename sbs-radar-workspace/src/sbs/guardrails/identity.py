"""SK08: validate a delegated token against fixed workspace current-user API.

Only the resulting immutable user ID selects a server-owned role/family policy.
Forwarded names/roles are not authority. No tokens are retained or logged.
Data/model authorization is separate: this adapter does not claim UC row masking.
"""
from copy import deepcopy
import re
from urllib.parse import urlsplit

FAMILIES=frozenset({'cybersecurity','market_conduct'})
ROLES=frozenset({'reader','reviewer','compliance_owner'})


class RequestsCurrentUserProbe:
    def __init__(self, workspace_host):
        parsed=urlsplit(workspace_host)
        if (parsed.scheme!='https' or parsed.username or parsed.password
                or parsed.path not in ('','/') or parsed.query or parsed.fragment
                or parsed.port not in (None,443)
                or not re.fullmatch(r'[a-z0-9-]+\.cloud\.databricks\.com',parsed.hostname or '')):
            raise ValueError('invalid_pinned_workspace')
        self.url=workspace_host.rstrip('/')+'/api/2.0/preview/scim/v2/Me'

    def __call__(self, token):
        import requests
        session=requests.Session()
        try:
            response=session.get(self.url,headers={'Authorization':'Bearer '+token},
                                 timeout=(5,15),allow_redirects=False)
            if response.status_code!=200:raise PermissionError('identity_rejected')
            payload=response.json()
            if not isinstance(payload,dict):raise PermissionError('identity_rejected')
            return {k:payload.get(k) for k in ('id','active')}
        except Exception:
            raise PermissionError('identity_unavailable') from None
        finally:session.close()


class DatabricksUserIdentity:
    def __init__(self, policy, probe):
        principals=policy.get('principals') if isinstance(policy,dict) else None
        if not isinstance(principals,dict) or not callable(probe):raise ValueError('invalid_identity_policy')
        for subject,rule in principals.items():
            if (not isinstance(subject,str) or not subject or not isinstance(rule,dict)
                    or set(rule)!= {'role','families'} or rule['role'] not in ROLES
                    or not isinstance(rule['families'],list) or not rule['families']
                    or any(f not in FAMILIES for f in rule['families'])):
                raise ValueError('invalid_identity_policy')
        self.principals=deepcopy(principals);self.probe=probe

    def authenticate(self, headers):
        token=headers.get('x-forwarded-access-token')
        if (not isinstance(token,str) or not 1<=len(token)<=16384
                or any(ord(c)<33 or ord(c)>126 for c in token)):
            raise PermissionError('identity_token_required')
        try:identity=self.probe(token)
        except Exception:raise PermissionError('identity_unavailable') from None
        if (not isinstance(identity,dict) or identity.get('active') is not True
                or not isinstance(identity.get('id'),str) or identity['id'] not in self.principals):
            raise PermissionError('identity_not_authorized')
        return {'authenticated':True,'subject':identity['id'],**deepcopy(self.principals[identity['id']])}
