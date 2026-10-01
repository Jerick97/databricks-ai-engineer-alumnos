"""Render cloud app config from an observed app record; never create/deploy an app."""
import argparse,json
from pathlib import Path
from urllib.parse import urlsplit
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))


def build(app, workspace_probe):
    if app.get('name')!='sbs-radar-pilot':raise ValueError('unexpected_app_name')
    raw=app.get('url');u=urlsplit(raw or '')
    if (u.scheme!='https' or not u.hostname or not u.hostname.endswith('.aws.databricksapps.com')
            or not u.hostname.startswith('sbs-radar-pilot-') or u.username or u.password
            or u.port not in (None,443) or u.path not in ('','/') or u.query or u.fragment):
        raise ValueError('observed_app_url_required')
    host=workspace_probe.get('workspace_host','')
    from sbs.guardrails.identity import RequestsCurrentUserProbe
    RequestsCurrentUserProbe(host)
    if workspace_probe.get('status')!='passed_current_user_api':raise ValueError('verified_workspace_required')
    return {'command':['python','app.py'],'env':[{'name':'SBS_MODE','value':'cloud'},
            {'name':'SBS_PUBLIC_ORIGIN','value':raw.rstrip('/')},{'name':'DATABRICKS_HOST','value':host}]}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--app-metadata',required=True)
    parser.add_argument('--workspace-probe',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args()
    value=build(json.loads(Path(args.app_metadata).read_text()),json.loads(Path(args.workspace_probe).read_text()))
    with Path(args.output).open('x') as f:json.dump(value,f,indent=2);f.write('\n')
