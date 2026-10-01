"""Carga material descargado como archivos y un notebook, sin publicar Git."""
import argparse
import hashlib
from pathlib import Path
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.workspace import ImportFormat,Language

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--profile',required=True)
    p.add_argument('--folder',default='S08-Neptuno')
    p.add_argument('--dry-run',action='store_true')
    p.add_argument('--pull-config',action='store_true',help='Después de CP0, sincroniza config de Workspace a esta copia local')
    a=p.parse_args()
    if not a.folder.replace('-','').replace('_','').isalnum():
        raise ValueError('Folder debe ser un nombre simple, sin rutas')
    root=Path(__file__).resolve().parents[1]
    w=WorkspaceClient(profile=a.profile)
    target=f'/Users/{w.current_user.me().user_name}/{a.folder}'
    if a.pull_config:
        import json
        data=w.workspace.download(target+'/lab/config.json').read()
        config=json.loads(data)
        assert all(k in config for k in ['catalog','schema','warehouse_id','endpoint','model_name','app_name']), 'Configuración incompleta'
        assert str(config['schema']).startswith('ais08_'), 'Schema fuera de laboratorio AIS08'
        (root/'lab/config.json').write_text(json.dumps(config,indent=2))
        print('Configuración sincronizada. Recursos:',config['endpoint'],config['model_name'],config['app_name']);return
    if a.dry_run:
        print('Destino personal:',target,'; source SHA256:',hashlib.sha256((root/'notebook.py').read_bytes()).hexdigest());return
    # No sobrescribe una carpeta existente: usa otro --folder para repetir.
    try:
        w.workspace.get_status(target)
    except Exception as e:
        from databricks.sdk.errors import NotFound
        if not isinstance(e,NotFound):raise
    else:raise ValueError('Destino ya existe. Abre esa copia o elige --folder diferente.')
    w.workspace.mkdirs(target)
    for name in ['lab','app','bundle']:
        for file in sorted((root/name).rglob('*')):
            if not file.is_file() or any(x in file.parts for x in ['__pycache__','.venv','.databricks']):continue
            rel=file.relative_to(root)
            w.workspace.mkdirs(target+'/'+str(rel.parent))
            w.workspace.upload(target+'/'+str(rel),file.read_bytes(),format=ImportFormat.RAW,overwrite=False)
    w.workspace.upload(target+'/notebook',(root/'notebook.py').read_bytes(),format=ImportFormat.SOURCE,language=Language.PYTHON,overwrite=False)
    print('Abre en Workspace:',target+'/notebook')
    print('Completa catálogo, warehouse y sufijo propios en widgets; ejecutar por checkpoints.')
if __name__=='__main__':main()
