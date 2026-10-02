"""Pinned notebook delivery of additive Jobs projection, sealed105 unchanged."""
from pathlib import Path
import base64,hashlib
from .provision_106 import notebook_source as source105

def notebook_source146(**kwargs):
 overlay=Path(__file__).with_name('job_defaults_146.py').read_bytes()
 encoded=base64.b64encode(overlay).decode();pin=hashlib.sha256(overlay).hexdigest()
 source=source105(**kwargs)
 old='    from sbs.operations.cloud_driver import load_config,preflight,execute_from_config\n'
 new='    from sbs.operations.cloud_driver import load_config,preflight\n'
 new+='    import base64\n    overlay_raw=base64.b64decode('+repr(encoded)+')\n'
 new+='    checked(hashlib.sha256(overlay_raw).hexdigest()=='+repr(pin)+',"OVERLAY146_PIN_MISMATCH")\n'
 new+='    overlay_namespace={"__name__":"sbs_writer_overlay146"}\n    exec(compile(overlay_raw,"writer-overlay146","exec"),overlay_namespace)\n'
 new+='    execute_from_config=overlay_namespace["execute_from_config146"]\n'
 assert source.count(old)==1
 return source.replace(old,new)
