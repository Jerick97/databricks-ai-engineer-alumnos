"""Explicit SDK OAuth session, retained in memory; browser interaction belongs to CUA.

Import is inert. authenticate() performs a NEW interactive login only when called.
The URL publisher receives an authorization URL, never the callback or credentials.
"""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
import os
from pathlib import Path
import time
from urllib.parse import parse_qsl, urlsplit

HOST = 'https://dbc-0410b264-20c7.cloud.databricks.com'
CLIENT_ID = 'databricks-cli'
SCOPES = ('offline_access', 'all-apis')
REDIRECT_URL = 'http://localhost:8020'


class AuthSessionError(RuntimeError):
    """Safe message suitable for status output, without provider exception details."""


def callback_parameters(target):
    """Validate callback shape; SDK independently validates state before exchange."""
    try:
        parsed = urlsplit(target)
        if parsed.path != '/' or parsed.scheme or parsed.netloc or parsed.fragment:
            raise ValueError()
        pairs = parse_qsl(parsed.query, keep_blank_values=True, strict_parsing=True,
                          max_num_fields=4)
        query = dict(pairs)
        if len(query) != len(pairs) or set(query) != {'code', 'state'}:
            raise ValueError()
        if not all(query.values()):
            raise ValueError()
        return query
    except Exception:
        raise AuthSessionError('OAuth callback rejected') from None


def exchange(consent, parameters):
    try:
        return consent.exchange_callback_parameters(parameters)
    except Exception:
        raise AuthSessionError('OAuth callback rejected or exchange failed') from None


class CallbackHandler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_GET(self):
        try:
            if self.server.callback is not None:
                raise AuthSessionError('OAuth callback already received')
            self.server.callback = callback_parameters(self.path)
            status = 200
            body = b'Authentication response received. You can close this tab.'
        except AuthSessionError:
            status = 400
            body = b'Authentication response rejected.'
        self.send_response(status)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class CallbackServer(HTTPServer):
    allow_reuse_address = False

    def get_request(self):
        connection, address = super().get_request()
        connection.settimeout(1.0)
        return connection, address

    def handle_error(self, *_args):
        # Base implementation emits tracebacks which may contain callback data.
        pass


@contextmanager
def protected_authorization_url(path):
    """Publish only an authorization URL to a new mode-0600 ephemeral local file."""
    path = Path(path)
    created = False

    def publish(url):
        nonlocal created
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        created = True
        with os.fdopen(descriptor, 'w') as stream:
            stream.write(url)
            stream.flush()
            os.fsync(stream.fileno())

    try:
        yield publish
    finally:
        if created:
            path.unlink(missing_ok=True)


def authenticate(publish_authorization_url, timeout_seconds=180):
    """Return Config backed by a fresh SDK SessionCredentials, without persistence.

    Caller must use CUA to navigate the published URL. Do not print/repr the
    returned Config. Executor must retain/use this instance in the same process.
    No global profile selection is allowed for this explicit-host session.
    """
    if not 0 < timeout_seconds <= 180:
        raise AuthSessionError('OAuth timeout must be between zero and 180 seconds')
    # Fail closed instead of silently consulting the global profile or credentials.
    if any(name.startswith(('DATABRICKS_', 'ARM_', 'AZURE_')) and value
           for name, value in os.environ.items()):
        raise AuthSessionError('Explicit OAuth session requires an isolated authentication environment')
    try:
        from databricks.sdk.core import Config
        from databricks.sdk.oauth import OAuthClient
        with CallbackServer(('127.0.0.1', 8020), CallbackHandler) as server:
            server.callback = None
            client = OAuthClient.from_host(HOST, client_id=CLIENT_ID,
                                            redirect_url=REDIRECT_URL, scopes=list(SCOPES))
            consent = client.initiate_consent()
            deadline = time.monotonic() + timeout_seconds
            publish_authorization_url(consent.authorization_url)
            while server.callback is None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise AuthSessionError('OAuth callback timed out')
                server.timeout = min(1.0, remaining)
                server.handle_request()
            session = exchange(consent, server.callback)
            server.callback = None
        return Config(host=HOST, credentials_strategy=session)
    except AuthSessionError:
        raise
    except Exception:
        raise AuthSessionError('OAuth session initialization failed') from None
