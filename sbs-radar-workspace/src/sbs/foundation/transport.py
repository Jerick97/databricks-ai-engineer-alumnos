"""HTTPS transport: pinned public IP, verified TLS and manual redirects.

No environment proxies, cookies, credentials or permissive TLS fallback. Error
messages contain stable codes only, never URL query strings or response bodies.
"""
import http.client
import ipaddress
import socket
import ssl
import time
import queue
import threading
from urllib.parse import urlsplit, urljoin
from sbs.guardrails import check_source_url

MAX_BYTES = 20 * 1024 * 1024
TIMEOUT = 20
_DNS_SLOTS = threading.BoundedSemaphore(4)
_ERROR_CODES = frozenset({
    'DNS_UNAVAILABLE', 'DNS_TIMEOUT', 'DNS_FAILED', 'DNS_NONPUBLIC',
    'URL_DENIED', 'PEER_DENIED', 'TLS_PEER_DENIED', 'TIMEOUT',
    'REDIRECT_LIMIT', 'HTTP_STATUS', 'SIZE_LIMIT', 'ENCODING_DENIED',
    'TRUNCATED_BODY', 'TRANSPORT_FAILED',
})


class TransportError(ValueError):
    def __init__(self, code):
        self.code = code if isinstance(code, str) and code in _ERROR_CODES else 'TRANSPORT_FAILED'
        super().__init__(self.code)


def _resolve(host, timeout):
    # OS getaddrinfo cannot be cancelled. Bound waiting and concurrent workers;
    # a timed-out worker can only resolve, never connect or send a request.
    if timeout <= 0 or not _DNS_SLOTS.acquire(blocking=False):
        raise TransportError('DNS_UNAVAILABLE')
    output = queue.Queue(maxsize=1)
    def worker():
        try:
            output.put(socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM))
        except Exception:
            output.put(None)
        finally:
            _DNS_SLOTS.release()
    threading.Thread(target=worker, daemon=True).start()
    try:
        answers = output.get(timeout=timeout)
    except queue.Empty:
        raise TransportError('DNS_TIMEOUT') from None
    if not answers:
        raise TransportError('DNS_FAILED')
    return answers


def fetch_pdf(url, *, allowed_hosts):
    """Return (bytes, final_url); reject all unsafe DNS answers/peers.

    A total 20-second deadline covers DNS waiting, redirects and socket I/O.
    URLs (including query) are returned for private provenance, never logged.
    """
    current = url
    deadline = time.monotonic() + TIMEOUT
    for hop in range(6):
        if not check_source_url(current, allowed_hosts)['valid']:
            raise TransportError('URL_DENIED')
        parsed = urlsplit(current)
        connection = None
        raw_socket = None
        watchdog = None
        try:
            answers = _resolve(parsed.hostname, deadline - time.monotonic())
            if not answers or any(not ipaddress.ip_address(a[4][0]).is_global for a in answers):
                raise TransportError('DNS_NONPUBLIC')
            family, kind, proto, _, address = answers[0]
            raw_socket = socket.socket(family, kind, proto)
            def interrupt_socket():
                try:
                    raw_socket.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                raw_socket.close()
            watchdog = threading.Timer(max(0, deadline - time.monotonic()), interrupt_socket)
            watchdog.daemon = True
            watchdog.start()
            raw_socket.settimeout(max(0.001, deadline - time.monotonic()))
            raw_socket.connect(address)
            peer = raw_socket.getpeername()[0]
            if not ipaddress.ip_address(peer).is_global or peer != address[0]:
                raise TransportError('PEER_DENIED')
            raw_socket.settimeout(max(0.001, deadline - time.monotonic()))
            tls = ssl.create_default_context().wrap_socket(raw_socket, server_hostname=parsed.hostname)
            raw_socket = tls
            if tls.getpeername()[0] != peer:
                raise TransportError('TLS_PEER_DENIED')
            connection = http.client.HTTPConnection(parsed.hostname, 443, timeout=TIMEOUT)
            connection.sock = tls
            target = parsed.path or '/'
            if parsed.query:
                target += '?' + parsed.query
            tls.settimeout(max(0.001, deadline - time.monotonic()))
            connection.request('GET', target, headers={'Accept': 'application/pdf',
                                                       'Accept-Encoding': 'identity'})
            response = connection.getresponse()
            if time.monotonic() >= deadline:
                raise TransportError('TIMEOUT')
            if response.status in (301, 302, 303, 307, 308):
                location = response.getheader('Location')
                if hop == 5 or not location:
                    raise TransportError('REDIRECT_LIMIT')
                current = urljoin(current, location)
                continue
            if response.status != 200:
                raise TransportError('HTTP_STATUS')
            length = response.getheader('Content-Length')
            if length and (not length.isdigit() or int(length) > MAX_BYTES):
                raise TransportError('SIZE_LIMIT')
            if response.getheader('Content-Encoding', 'identity').lower() != 'identity':
                raise TransportError('ENCODING_DENIED')
            chunks, size = [], 0
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TransportError('TIMEOUT')
                tls.settimeout(remaining)
                chunk = response.read(min(65536, MAX_BYTES + 1 - size))
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_BYTES:
                    raise TransportError('SIZE_LIMIT')
                chunks.append(chunk)
                # HTTPResponse closes its file at Content-Length/EOF. With
                # Connection: close that also closes the retained TLS socket;
                # a further settimeout would fail despite a complete body.
                if response.isclosed():
                    break
            if length and size != int(length):
                raise TransportError('TRUNCATED_BODY')
            return b''.join(chunks), current
        except TransportError:
            raise
        except Exception:
            raise TransportError('TRANSPORT_FAILED') from None
        finally:
            if watchdog is not None:
                watchdog.cancel()
                watchdog.join()
            if connection is not None:
                connection.close()
            if raw_socket is not None:
                raw_socket.close()
    raise TransportError('REDIRECT_LIMIT')
