"""SBS channel: loopback operator or independently verified cloud principal."""
from pathlib import Path
import secrets
import time
from typing import Protocol
from urllib.parse import urlsplit
from starlette.concurrency import run_in_threadpool
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

class Service(Protocol):
    def catalog(self) -> dict: ...
    def comparison(self, pair_id: str, provision_id: str | None = None) -> dict: ...
    def ask(self, session_id: str, question: str, pair_id: str, provision_id: str | None = None, cross_family: bool = False) -> dict: ...
    def source(self, source_id: str) -> Path | dict: ...

class Question(BaseModel):
    model_config = ConfigDict(extra='forbid')
    question: str = Field(min_length=1,max_length=8000)
    pair_id: str = Field(min_length=1,max_length=200)
    provision_id: str | None = Field(default=None,max_length=200)
    cross_family: bool = False

def create_app(service: Service, mode='local', *, identity_adapter=None, public_origin=None, trusted_proxy=None) -> FastAPI:
    if mode not in ('local','cloud'):raise ValueError('Modo desconocido.')
    if trusted_proxy not in (None,'databricks_apps') or (trusted_proxy and mode!='cloud'):
        raise ValueError('Proxy confiable requiere despliegue cloud explícito.')
    if mode=='cloud':
        origin=urlsplit(public_origin or '')
        if (identity_adapter is None or not callable(getattr(identity_adapter,'authenticate',None))
                or not callable(getattr(service,'for_actor',None)) or getattr(service,'mode',None)!='cloud' or origin.scheme!='https'
                or not origin.hostname or origin.username or origin.password or origin.path
                or origin.query or origin.fragment or origin.port not in (None,443)):
            raise ValueError('Modo cloud requiere identidad verificable, servicio con permisos y origen HTTPS explícito.')
    app=FastAPI(title='SBS Radar',docs_url=None,redoc_url=None)
    sessions={}
    static=Path(__file__).parent/'static'
    app.mount('/static',StaticFiles(directory=static),name='static')

    @app.middleware('http')
    async def protect(request: Request, call_next):
        host=request.url.hostname
        allowed={'127.0.0.1','localhost','::1','testserver'} if mode=='local' else {origin.hostname}
        if trusted_proxy=='databricks_apps':
            # Deployment-owned opt-in: ingress must be the Databricks Apps proxy.
            # Exact single hostname only; never normalize lists, ports or whitespace.
            forwarded=request.headers.getlist('x-forwarded-host')
            host_allowed=len(forwarded)==1 and forwarded[0]==origin.hostname
        else:
            host_allowed=host in allowed
        if not host_allowed:return JSONResponse({'detail':'Host no autorizado.'},status_code=403)
        actor={'subject':'local-operator'}
        request.state.service=service
        if mode=='cloud':
            try:
                actor=await run_in_threadpool(identity_adapter.authenticate,request.headers)
                request.state.service=await run_in_threadpool(service.for_actor,actor)
            except PermissionError:
                return JSONResponse({'detail':'Identidad no autorizada o sesión de Databricks no disponible.'},status_code=401)
        now=time.monotonic()
        for key in list(sessions):
            if sessions[key]['expires'] < now: sessions.pop(key,None)
        sid=request.cookies.get('sbs_session')
        if sid not in sessions or sessions[sid]['subject']!=actor['subject']:
            sid=secrets.token_urlsafe(32)
            sessions[sid]={'csrf':secrets.token_urlsafe(32),'expires':now+28800,'subject':actor['subject']}
        request.state.sid=sid
        if request.method not in {'GET','HEAD','OPTIONS'}:
            supplied_origin=request.headers.get('origin')
            expected=public_origin if mode=='cloud' else str(request.base_url).rstrip('/')
            if supplied_origin and supplied_origin!=expected:
                return JSONResponse({'detail':'Origen no autorizado.'},status_code=403)
            token=request.headers.get('x-csrf-token','')
            if not secrets.compare_digest(token,sessions[sid]['csrf']):
                return JSONResponse({'detail':'Sesión caducada o verificación de seguridad ausente. Recarga la página.'},status_code=403)
        response=await call_next(request)
        response.set_cookie('sbs_session',sid,httponly=True,samesite='strict',secure=mode=='cloud',max_age=28800)
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='no-referrer'
        response.headers['Cache-Control']='no-store'
        return response

    def selected(scoped,pair_id,provision_id):
        pair=next((p for p in scoped.catalog().get('pairs',[]) if p['id']==pair_id),None)
        if pair is None or not provision_id or not any(p['id']==provision_id for p in pair.get('provisions',[])):
            raise HTTPException(404,'La selección no pertenece al catálogo disponible.')

    @app.exception_handler(Exception)
    async def failure(request,exc):
        return JSONResponse({'detail':'La consulta no está disponible. Reintenta o revisa la configuración del servicio.'},status_code=503)

    @app.exception_handler(PermissionError)
    async def denied(request,exc):
        return JSONResponse({'detail':'Acceso no autorizado para este recurso.'},status_code=403)

    from sbs.app133.lifecycle210 import Lifecycle210Error

    @app.exception_handler(Lifecycle210Error)
    async def lifecycle_failure(request, exc):
        return JSONResponse({'detail': str(exc)}, status_code=409)

    @app.get('/api/runtime/status')
    def runtime_status():
        return service.process_budget.status()

    @app.post('/api/runtime/activate')
    def runtime_activate(body: dict):
        return service.process_budget.activate(body)

    @app.get('/')
    def home(): return FileResponse(static/'index.html')

    @app.get('/api/catalog')
    def catalog(request: Request):
        return {**request.state.service.catalog(),'csrf_token':sessions[request.state.sid]['csrf'],'session_mode':('Operador local' if mode=='local' else 'Identidad Databricks verificada')+' · sin aprobación institucional'}

    @app.get('/api/comparison')
    def comparison(request:Request,pair_id: str,provision_id: str | None=None):
        selected(request.state.service,pair_id,provision_id)
        return request.state.service.comparison(pair_id,provision_id)

    @app.post('/api/ask')
    def ask(body: Question,request: Request):
        selected(request.state.service,body.pair_id,body.provision_id)
        if not body.question.strip(): raise HTTPException(422,'Escribe una pregunta.')
        return request.state.service.ask(request.state.sid,body.question,body.pair_id,body.provision_id,body.cross_family)

    @app.get('/api/sources/{source_id}')
    def source(request:Request,source_id: str):
        if not source_id or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.' for c in source_id) or '..' in source_id:
            raise HTTPException(404,'Fuente no disponible.')
        try: value=request.state.service.source(source_id)
        except (KeyError,ValueError,FileNotFoundError): raise HTTPException(404,'Fuente no disponible.')
        # Only server-owned paths from the service mapping; never accept paths or redirects from clients.
        path=value.get('path') if isinstance(value,dict) else value
        if not isinstance(path,Path) or not path.is_file(): raise HTTPException(404,'Original no disponible en esta configuración.')
        return FileResponse(path,media_type='application/pdf',filename=path.name,content_disposition_type='inline')

    return app
