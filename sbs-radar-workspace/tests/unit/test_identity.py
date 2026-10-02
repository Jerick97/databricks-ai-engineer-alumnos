import pytest
from sbs.guardrails.identity import DatabricksUserIdentity, RequestsCurrentUserProbe

POLICY={'principals':{'u1':{'role':'reader','families':['cybersecurity']}}}

def test_verified_identity_not_forwarded_name_or_role():
    seen=[]
    identity=DatabricksUserIdentity(POLICY,lambda token: seen.append(token) or {'id':'u1','active':True})
    actor=identity.authenticate({'x-forwarded-access-token':'opaque','x-forwarded-user':'admin','actor_role':'reviewer'})
    assert seen==['opaque'] and actor=={'authenticated':True,'subject':'u1','role':'reader','families':['cybersecurity']}
    assert 'opaque' not in repr(identity)

@pytest.mark.parametrize('headers,payload',[
    ({}, {'id':'u1','active':True}),
    ({'x-forwarded-access-token':'x'}, {'id':'u1','active':False}),
    ({'x-forwarded-access-token':'x'}, {'id':'other','active':True}),
    ({'x-forwarded-access-token':'x'}, {'id':'u1'}),
    ({'x-forwarded-access-token':'x\nAuth: y'}, {'id':'u1','active':True})])
def test_auth_fails_closed(headers,payload):
    with pytest.raises(PermissionError):DatabricksUserIdentity(POLICY,lambda token:payload).authenticate(headers)

def test_probe_error_and_policy_misconfiguration_fail_closed():
    def unavailable(token):raise RuntimeError('provider-secret')
    with pytest.raises(PermissionError,match='identity_unavailable'):
        DatabricksUserIdentity(POLICY,unavailable).authenticate({'x-forwarded-access-token':'opaque'})
    with pytest.raises(ValueError):DatabricksUserIdentity({'principals':{'u1':{'role':'superadmin','families':['cybersecurity']}}},lambda t:{})

def test_fixed_https_probe_rejects_untrusted_origin():
    for host in ['http://workspace.cloud.databricks.com','https://workspace.cloud.databricks.com/a','https://workspace.cloud.databricks.com@evil.test']:
        with pytest.raises(ValueError):RequestsCurrentUserProbe(host)


def test_probe_never_redirects_retries_or_logs_credentials(monkeypatch):
    import requests
    calls=[]
    class Response:
        status_code=302
        def json(self):raise AssertionError('Do not parse redirect')
    class Session:
        def get(self,url,**kwargs):calls.append((url,kwargs));return Response()
        def close(self):pass
    monkeypatch.setattr(requests,'Session',Session)
    probe=RequestsCurrentUserProbe('https://workspace.cloud.databricks.com')
    with pytest.raises(PermissionError):probe('opaque')
    assert len(calls)==1 and calls[0][1]['allow_redirects'] is False
    assert calls[0][0].endswith('/api/2.0/preview/scim/v2/Me')
    assert 'opaque' not in repr(probe)
