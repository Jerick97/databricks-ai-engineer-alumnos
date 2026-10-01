"""Runtime210 boots inactive until a signed epoch allocation is accepted."""
import json
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
from sbs.webapp import create_app
try:
    from sbs.runtime import create_service
except ImportError as exc:
    raise RuntimeError('SBS Radar requiere el runtime real y su configuración. No hay datos de demostración como respaldo.') from exc
mode=os.environ.get('SBS_MODE','local')
options={}
if mode=='cloud':
    from sbs.guardrails.identity import DatabricksUserIdentity, RequestsCurrentUserProbe
    policy_path=ROOT/'config/cloud-identity-policy.json'
    host=os.environ.get('DATABRICKS_HOST')
    origin=os.environ.get('SBS_PUBLIC_ORIGIN')
    if not host or not origin:raise RuntimeError('Cloud requiere DATABRICKS_HOST y SBS_PUBLIC_ORIGIN observados; no se usan valores de demostración.')
    options={'identity_adapter':DatabricksUserIdentity(json.loads(policy_path.read_text()),RequestsCurrentUserProbe(host)),
             'public_origin':origin,'trusted_proxy':os.environ.get('SBS_TRUSTED_PROXY')}
from sbs.app133.lifecycle210 import create_service210
app=create_app(create_service210(os.environ,root=ROOT),mode=mode,**options)
if __name__=='__main__':
    import uvicorn
    port=int(os.environ['DATABRICKS_APP_PORT']) if mode=='cloud' else 8090
    uvicorn.run(app,host='0.0.0.0' if mode=='cloud' else '127.0.0.1',port=port)
