"""Offline safety contracts; no provider network or live browser authentication."""
import importlib.util
from pathlib import Path
import io
import contextlib
import pytest

MODULE = Path(__file__).resolve().parents[2] / 'deployment/oauth_session203.py'

def module():
    assert MODULE.exists(), 'session203 implementation is absent'
    spec = importlib.util.spec_from_file_location('oauth_session203', MODULE)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

def test_callback_rejects_duplicate_or_missing_parameters():
    m = module()
    for target in ['/?code=a&code=b&state=x', '/?code=a', '/?state=x', '/wrong?code=a&state=x']:
        with pytest.raises(m.AuthSessionError):
            m.callback_parameters(target)
    assert m.callback_parameters('/?code=a&state=x') == {'code':'a', 'state':'x'}

def test_sdk_rejects_wrong_state_without_token_exchange(monkeypatch, capsys):
    m = module()
    from databricks.sdk.oauth import Consent
    consent = Consent('expected', 'verifier', 'https://example.invalid/auth',
                      m.REDIRECT_URL, 'https://example.invalid/token', m.CLIENT_ID)
    def forbidden(*args, **kwargs):
        pytest.fail('wrong-state callback attempted token exchange')
    monkeypatch.setattr('databricks.sdk.oauth.retrieve_token', forbidden)
    with pytest.raises(m.AuthSessionError) as error:
        m.exchange(consent, {'code':'SENSITIVE_CODE', 'state':'wrong'})
    assert str(error.value) == 'OAuth state mismatch'
    assert error.value.__suppress_context__
    assert 'SENSITIVE_CODE' not in capsys.readouterr().out

def test_authorization_file_is_exclusive_private_and_ephemeral(tmp_path):
    m = module()
    path = tmp_path / 'authorization-url'
    with m.protected_authorization_url(path) as publish:
        publish('https://example.invalid/auth?state=test')
        assert path.stat().st_mode & 0o777 == 0o600
        with pytest.raises(FileExistsError):
            publish('https://example.invalid/other')
    assert not path.exists()

def test_authorization_file_does_not_remove_preexisting_file(tmp_path):
    m = module()
    path = tmp_path / 'existing'
    path.write_text('preserve')
    with pytest.raises(FileExistsError):
        with m.protected_authorization_url(path) as publish:
            publish('https://example.invalid/auth')
    assert path.read_text() == 'preserve'

def test_import_has_no_auth_side_effect_and_constants_match_approved_login():
    m = module()
    assert m.HOST == 'https://dbc-0410b264-20c7.cloud.databricks.com'
    assert m.CLIENT_ID == 'databricks-cli'
    assert set(m.SCOPES) == {'all-apis', 'offline_access'}

def test_callback_handler_does_not_log_query():
    m = module()
    handler = object.__new__(m.CallbackHandler)
    captured = io.StringIO()
    with contextlib.redirect_stderr(captured), contextlib.redirect_stdout(captured):
        handler.log_message('GET /?code=%s&state=%s', 'SENSITIVE_CODE', 'SENSITIVE_STATE')
    assert captured.getvalue() == ''

def test_expired_synthetic_session_refreshes_without_cache_or_disk(monkeypatch):
    from datetime import datetime, timedelta, timezone
    import builtins
    from databricks.sdk.core import Config
    from databricks.sdk.oauth import SessionCredentials, Token, TokenCache
    import os
    for name in list(os.environ):
        if name.startswith(('DATABRICKS_', 'ARM_', 'AZURE_')):
            monkeypatch.delenv(name)
    m = module()
    refresh_calls = []
    def refresh(**kwargs):
        refresh_calls.append(kwargs['params']['grant_type'])
        return Token('synthetic-refreshed', 'Bearer', 'synthetic-refresh',
                     datetime.now() + timedelta(minutes=10))
    def forbidden(*_args, **_kwargs):
        pytest.fail('session provider attempted disk cache access')
    monkeypatch.setattr('databricks.sdk.oauth.retrieve_token', refresh)
    monkeypatch.setattr(TokenCache, 'load', forbidden)
    monkeypatch.setattr(TokenCache, 'save', forbidden)
    monkeypatch.setattr(builtins, 'open', forbidden)
    session = SessionCredentials(
        Token('synthetic-expired', 'Bearer', 'synthetic-refresh',
              datetime.now() - timedelta(minutes=1)),
        m.HOST + '/oidc/v1/token', m.CLIENT_ID, redirect_url=m.REDIRECT_URL)
    cfg = Config(host=m.HOST, credentials_strategy=session)
    assert cfg.authenticate() == {'Authorization': 'Bearer synthetic-refreshed'}
    assert refresh_calls == ['refresh_token']


def test_auth_rejects_inherited_profile_before_sdk_or_network(monkeypatch):
    m = module()
    monkeypatch.setenv('DATABRICKS_CONFIG_PROFILE', 'synthetic-profile')
    with pytest.raises(m.AuthSessionError, match='isolated authentication environment'):
        m.authenticate(lambda _url: pytest.fail('must not publish URL'))


def test_supported_cli_fallback_port():
    m = module()
    assert m.REDIRECT_URL == 'http://localhost:8023'
    assert m.CALLBACK_PORT == 8023


def test_bind_failure_reports_only_stage_errno(monkeypatch):
    import os
    m = module()
    for name in list(os.environ):
        if name.startswith(('DATABRICKS_', 'ARM_', 'AZURE_')):
            monkeypatch.delenv(name)
    def occupied(*_args, **_kwargs):
        raise OSError(48, 'synthetic-private-detail')
    monkeypatch.setattr(m, 'CallbackServer', occupied)
    with pytest.raises(m.AuthSessionError) as error:
        m.authenticate(lambda _url: pytest.fail('bind failure must not publish'))
    assert str(error.value) == 'OAuth session initialization failed; stage=callback-bind; errno=48'
    assert error.value.__suppress_context__


def test_issuer_metadata_matches_approved_workspace():
    from urllib.parse import urlencode
    m = module()
    query = urlencode({'code': 'synthetic-code', 'state': 'synthetic-state',
                       'iss': m.HOST + '/oidc'})
    assert m.callback_parameters('/?' + query) == {
        'code': 'synthetic-code', 'state': 'synthetic-state'}
    for issuer in ['https://other.invalid/oidc', m.HOST + '/oidc/', '']:
        query = urlencode({'code': 'synthetic-code', 'state': 'synthetic-state', 'iss': issuer})
        with pytest.raises(m.AuthSessionError):
            m.callback_parameters('/?' + query)


def test_issuer_does_not_relax_duplicate_missing_state_or_unknown_keys():
    from urllib.parse import urlencode
    m = module()
    base = urlencode({'code': 'synthetic-code', 'state': 'synthetic-state', 'iss': m.HOST + '/oidc'})
    for query in [base + '&iss=anything', base + '&unexpected=anything',
                  urlencode({'code':'synthetic-code', 'iss':m.HOST + '/oidc'})]:
        with pytest.raises(m.AuthSessionError):
            m.callback_parameters('/?' + query)


@pytest.mark.parametrize('port', [True, '8023', 8019, 8041, None])
def test_invalid_callback_port_fails_before_sdk(monkeypatch, port):
    m = module()
    with pytest.raises(m.AuthSessionError, match='callback port'):
        m.authenticate(lambda _url: pytest.fail('must not publish'), callback_port=port)


def test_callback_port_binding_and_redirect_are_consistent(monkeypatch):
    import os
    from databricks.sdk.oauth import OAuthClient
    m = module()
    for name in list(os.environ):
        if name.startswith(('DATABRICKS_', 'ARM_', 'AZURE_')):
            monkeypatch.delenv(name)
    observed = {}
    class Server:
        def __init__(self, address, handler):
            observed['bind'] = address
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
    def discovery(host, **kwargs):
        observed['redirect'] = kwargs['redirect_url']
        raise RuntimeError('stop before discovery network')
    monkeypatch.setattr(m, 'CallbackServer', Server)
    monkeypatch.setattr(OAuthClient, 'from_host', discovery)
    with pytest.raises(m.AuthSessionError, match='stage=oauth-discovery'):
        m.authenticate(lambda _url: pytest.fail('must not publish'), callback_port=8024)
    assert observed == {'bind': ('127.0.0.1', 8024), 'redirect': 'http://localhost:8024'}
