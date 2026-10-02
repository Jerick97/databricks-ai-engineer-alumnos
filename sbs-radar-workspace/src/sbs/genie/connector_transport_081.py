"""Pinned 4.2.6 Thrift transport: no SDK/network work until context entry.

Internal connector hooks are version-pinned and tested against its real classes.
Keep this process single-purpose: patch is serialized for the connection lifetime.
"""
from contextlib import contextmanager
import threading
import time
from .publication import require

CONNECTOR_VERSION='4.2.6'
_LOCK=threading.Lock()

class Budget:
    def __init__(self, *, max_calls=256, max_seconds=240, clock=time.monotonic):
        self.max_calls=max_calls; self.max_seconds=max_seconds; self.clock=clock
        self.started=clock(); self.calls=0
    def check(self):
        require(self.clock()-self.started < self.max_seconds,'FRESH_DEADLINE_EXCEEDED')
    def reserve(self):
        self.check();require(self.calls<self.max_calls,'FRESH_HTTP_CAP');self.calls+=1


def guarded_transport(base, budget, *, max_response_bytes=20_000_000):
    class Guarded(base):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,**kwargs)
            self.retry_policy=False
            self._read_bytes=0
        def open(self):
            super().open()
            pool=self._THttpClient__pool
            original=pool.request
            def once(*a,**kw):
                budget.reserve()
                kw.update(retries=False,redirect=False)
                return original(*a,**kw)
            pool.request=once
        def flush(self):
            budget.check();self._read_bytes=0
            return super().flush()
        def read(self,size):
            budget.check()
            require(type(size) is int and 0<=size<=max_response_bytes-self._read_bytes,'FRESH_HTTP_RESPONSE_CAP')
            result=super().read(size);self._read_bytes+=len(result)
            require(self._read_bytes<=max_response_bytes,'FRESH_HTTP_RESPONSE_CAP')
            return result
        def close(self):
            # Base close drains unread bytes without a cap; close the response.
            response=getattr(self,'_THttpClient__resp',None)
            if response is not None:
                response.close();response.release_conn();self._THttpClient__resp=None
    return Guarded


@contextmanager
def connection(config, warehouse_id, budget):
    import databricks.sql
    from databricks.sql.client import Connection  # initializes pinned Thrift dependencies
    from databricks.sql.auth import thrift_http_client
    require(databricks.sql.__version__==CONNECTOR_VERSION,'CONNECTOR_VERSION_PIN_MISMATCH')
    require(_LOCK.acquire(blocking=False),'CONNECTOR_PROCESS_BUSY')
    base=thrift_http_client.THttpClient
    conn=None
    try:
        thrift_http_client.THttpClient=guarded_transport(base,budget)
        # Normal configured authentication; no reading or printing credential files.
        conn=databricks.sql.connect(server_hostname=config.host.removeprefix('https://').rstrip('/'),http_path='/sql/1.0/warehouses/'+warehouse_id,
            credentials_provider=lambda:config.authenticate,
            use_sea=False, enable_telemetry=False, use_cloud_fetch=False,
            _retry_stop_after_attempts_count=1, _retry_stop_after_attempts_duration=1,
            _socket_timeout=20, session_configuration={'STATEMENT_TIMEOUT':'30'})
        yield conn
    finally:
        try:
            if conn is not None:conn.close()
        finally:
            thrift_http_client.THttpClient=base;_LOCK.release()
