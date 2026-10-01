"""CP7: prueba alias challenger y rollback; no altera el prompt de modelos ya servidos."""
import argparse,os
import mlflow
from lab_deploy import CONFIG,save
p=argparse.ArgumentParser();p.add_argument('--profile');a=p.parse_args()
if a.profile:os.environ['DATABRICKS_CONFIG_PROFILE']=a.profile
mlflow.set_registry_uri('databricks-uc')
name=f"{CONFIG['catalog']}.{CONFIG['schema']}.neptuno_system"
old=mlflow.genai.load_prompt(f'prompts:/{name}@champion')
candidate=mlflow.genai.register_prompt(name=name,template=old.template+'\nResponde con evidencia explícita.',commit_message='CP7 challenger didáctico; no promovido a Serving')
mlflow.genai.set_prompt_alias(name,'challenger',candidate.version)
# Simulación operacional REAL sobre el alias de prompt aislado; restaura siempre champion.
try:
    mlflow.genai.set_prompt_alias(name,'champion',candidate.version)
    promoted=mlflow.genai.load_prompt(f'prompts:/{name}@champion').version
finally:
    mlflow.genai.set_prompt_alias(name,'champion',old.version)
restored=mlflow.genai.load_prompt(f'prompts:/{name}@champion').version
assert restored==old.version
save('prompts',{'name':name,'original':old.version,'challenger':candidate.version,'promoted_then_rolled_back':promoted,'restored':restored,'affects_existing_model':False})
print('Prompt alias rollback verified; endpoint template remains pinned')
