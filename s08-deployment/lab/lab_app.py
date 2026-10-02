"""CP4: crea App aislada y sube el código, sin tokens en archivos/browser."""
import os, json, argparse
from pathlib import Path
from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import NotFound
from databricks.sdk.service import apps
from databricks.sdk.service.workspace import ImportFormat
from lab_deploy import CONFIG, save

def main():
    p=argparse.ArgumentParser();p.add_argument('--profile');a=p.parse_args()
    if a.profile:os.environ['DATABRICKS_CONFIG_PROFILE']=a.profile
    w=WorkspaceClient();c=CONFIG
    assert c['app_name'].startswith('ais08-')
    try: app=w.apps.get(c['app_name'])
    except NotFound:
        app=w.apps.create(app=apps.App(name=c['app_name'],description='S08 Neptuno: UI sobre Serving',resources=[apps.AppResource(name='neptuno-endpoint',serving_endpoint=apps.AppResourceServingEndpoint(name=c['endpoint'],permission=apps.AppResourceServingEndpointServingEndpointPermission.CAN_QUERY))])).result()
    source=f"/Users/{w.current_user.me().user_name}/AIS08-labfiles/app"
    w.workspace.mkdirs(source)
    for path in (Path(__file__).resolve().parents[1]/'app').iterdir():
        if path.is_file():w.workspace.upload(source+'/'+path.name,path.read_bytes(),format=ImportFormat.AUTO,overwrite=True)
    deployment=w.apps.deploy(c['app_name'],app_deployment=apps.AppDeployment(source_code_path="/Workspace"+source))
    save('app',{'name':app.name,'url':app.url,'source_code_path':source,'submitted':True})
    print('App deployment submitted:',app.name)
if __name__=='__main__':main()
