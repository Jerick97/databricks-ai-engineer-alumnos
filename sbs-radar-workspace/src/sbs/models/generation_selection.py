"""Server-owned generation selection, independent of frozen embedding bundles."""
import hashlib,json,re
from pathlib import Path

def load_selection(root,path='config/generation-selection-073.json'):
    root=Path(root).resolve();file=(root/path).resolve()
    if not file.is_relative_to(root) or not file.is_file():raise ValueError('generation_unconfigured')
    config=json.loads(file.read_bytes())
    if config.get('status')!='selected_for_controlled_trial':raise ValueError('generation_unconfigured')
    for key in ('endpoint','expected_response_model'):
        if not isinstance(config.get(key),str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,150}',config[key]):raise ValueError('generation_selection_invalid')
    for key,maximum in [('max_requests',4),('max_output_tokens',5000),('max_input_chars',120000)]:
        if type(config.get(key)) is not int or not 0<config[key]<=maximum:raise ValueError('generation_limits_invalid')
    observation=(root/config['observation_path']).resolve()
    if not observation.is_relative_to(root) or not observation.is_file():raise ValueError('generation_observation_missing')
    raw=observation.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=config['observation_sha256']:raise ValueError('generation_observation_changed')
    observed=json.loads(raw)
    if observed.get('http_status')!=200 or observed.get('endpoint')!=config['endpoint'] or observed.get('model')!=config['expected_response_model']:raise ValueError('generation_observation_mismatch')
    return config
