"""Prueba HTTP oficial con auth unificada en servidor; jamás inyecta tokens en navegador."""
import argparse,os
import requests
from databricks.sdk import WorkspaceClient
from lab_deploy import CONFIG,save,REPORTS
p=argparse.ArgumentParser();p.add_argument('--profile');p.add_argument('--health-only',action='store_true');a=p.parse_args()
if a.profile:os.environ['DATABRICKS_CONFIG_PROFILE']=a.profile
w=WorkspaceClient();url=w.apps.get(CONFIG['app_name']).url.rstrip('/')
# Credenciales sólo en memoria, no imprimir headers ni Response.request.
headers=w.config.authenticate()
health=requests.get(url+'/health',headers=headers,timeout=30,allow_redirects=False)
result={'url':url,'health_status':health.status_code,'health_ok':health.status_code==200 and health.json().get('status')=='ok' if health.status_code==200 else False}
invalid=requests.post(url+'/',headers=headers,data={'question':'<script>alert(1)</script>'+'a'*2000},timeout=30,allow_redirects=False)
result.update(invalid_status=invalid.status_code,invalid_has_form='<form' in invalid.text,invalid_escaped='&lt;script&gt;' in invalid.text and '<script>alert(1)</script>' not in invalid.text)
if not a.health_only:
    page=requests.post(url+'/',headers=headers,data={'question':'¿Cuánto vendimos de Bebidas en 2026?'},timeout=180,allow_redirects=False)
    (REPORTS/'lab-app-observed.html').write_text(page.text)
    result.update(post_status=page.status_code,has_expected_business_answer='116024.88' in page.text,has_source='gold.ventas_por_categoria_mes' in page.text)
    result['pass']=result['health_ok'] and result['has_expected_business_answer'] and result['has_source'] and result['invalid_status']==400 and result['invalid_has_form'] and result['invalid_escaped']
else:result['pass']=result['health_ok']
save('app-http',result);print(result)
if not result['pass']:raise SystemExit(1)
