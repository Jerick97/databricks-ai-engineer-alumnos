import importlib.util
from pathlib import Path
import pytest
spec=importlib.util.spec_from_file_location('appconfig',Path(__file__).parents[2]/'deployment/prepare_app_config.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
PROBE={'status':'passed_current_user_api','workspace_host':'https://workspace.cloud.databricks.com'}

def test_real_observation_shape_and_no_client_secret_or_profile():
    v=m.build({'name':'sbs-radar-pilot','url':'https://sbs-radar-pilot-123.aws.databricksapps.com'},PROBE)
    assert v['command']==['python','app.py']
    assert {x['name'] for x in v['env']}=={'SBS_MODE','SBS_PUBLIC_ORIGIN','DATABRICKS_HOST'}

@pytest.mark.parametrize('app',[{'name':'ais08-neptuno-ui','url':'https://ais08-neptuno-ui-123.aws.databricksapps.com'},{'name':'sbs-radar-pilot'},{'name':'sbs-radar-pilot','url':'http://sbs-radar-pilot-123.aws.databricksapps.com'},{'name':'sbs-radar-pilot','url':'https://sbs-radar-pilot-123.aws.databricksapps.com.evil.test'}])
def test_rejects_invented_missing_or_other_app(app):
    with pytest.raises(ValueError):m.build(app,PROBE)
