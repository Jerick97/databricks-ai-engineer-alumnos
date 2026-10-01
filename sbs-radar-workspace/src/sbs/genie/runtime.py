"""Server-owned Genie binding. Construction verifies local bytes, never calls cloud.

Injected dependencies are trusted server capabilities, never request payloads.
Artifact/config hashes detect corruption; their trust anchor is the server-owned
project/pinned config digest, not a self-authenticating client manifest.
"""
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import time
from sbs.paths import project_path
from . import TABLES, ScopedCatalog, GenieAdapter, digest
from .provenance import snapshot_inputs,reconcile_snapshots,DatabricksHistoryProbe


@dataclass(frozen=True)
class ServerDependencies:
    genie: object
    query_history: object
    permission_probe: object
    publication_lookup: object
    executor_id: int
    delta_publication: object = None


def _load(root,config_path,expected_config_sha256):
    def read(path):return project_path(root,path).read_bytes()
    raw=read(config_path)
    if expected_config_sha256 is not None and hashlib.sha256(raw).hexdigest()!=expected_config_sha256:raise ValueError('CONFIG_PIN_MISMATCH')
    config=json.loads(raw);directory=project_path(root,config['bundle_path'])
    def artifact(name):
        if Path(name).name!=name:raise ValueError('EXPORT_PATH_INVALID')
        return read(directory/name)
    inventory=json.loads(artifact('artifacts.json'))
    required={'manifest.json','snapshot-map.json','contexts.json','granularity.json','reference-queries.json',*[t+'.jsonl' for t in TABLES]}
    if not required<=set(inventory['sha256']):raise ValueError('EXPORT_INCOMPLETE')
    for name,expected in inventory['sha256'].items():
        if hashlib.sha256(artifact(name)).hexdigest()!=expected:raise ValueError('EXPORT_HASH_MISMATCH')
    bundle=json.loads(artifact('manifest.json'));bundle['tables']={t:[json.loads(line) for line in artifact(t+'.jsonl').splitlines()] for t in TABLES}
    mapping=json.loads(artifact('snapshot-map.json'));contexts=json.loads(artifact('contexts.json'));granularity=json.loads(artifact('granularity.json'))
    if project_path(root,config['snapshot_map_path'])!=directory/'snapshot-map.json':raise ValueError('MAP_PATH_MISMATCH')
    if config['snapshot']!=bundle['snapshot_hash'] or config['contexts']!=contexts or mapping['contexts']!=contexts:raise ValueError('CONFIG_SCOPE_MISMATCH')
    if digest(config['curation_config'])!=bundle['config_hash'] or digest(granularity)!=config['curation_config']['granularity_sha256']:raise ValueError('CURATION_CONFIG_MISMATCH')
    if config['table_prefix']!=config['catalog']+'.'+config['namespace'] or config['namespace']!='sbs_radar':raise ValueError('TABLE_NAMESPACE_MISMATCH')
    if digest({k:v for k,v in mapping.items() if k!='mapping_sha256'})!=mapping['mapping_sha256'] or config['mapping_sha256']!=mapping['mapping_sha256']:raise ValueError('MAP_HASH_MISMATCH')
    if mapping['sk06_snapshot']!=bundle['snapshot_hash'] or mapping['granularity_sha256']!=digest(granularity):raise ValueError('MAP_SNAPSHOT_MISMATCH')
    for name,expected in mapping['input_files'].items():
        if hashlib.sha256(read(name)).hexdigest()!=expected:raise ValueError('SOURCE_INPUT_MISMATCH')
    # Recheck frozen source/raw-page proof, without extraction, comparison,
    # embeddings, curation rebuild or network operations.
    inputs=snapshot_inputs(root);base=reconcile_snapshots(**inputs)
    if any(mapping[k]!=base[k] for k in ('rag_snapshot','rag_index_hash','sources')) or mapping['raw_page_mapping_sha256']!=base['mapping_sha256']:raise ValueError('RAG_MAPPING_MISMATCH')
    if mapping['prior_sk06_snapshot']!=inputs['bundle']['snapshot_hash']:raise ValueError('PRIOR_SNAPSHOT_MISMATCH')
    old=inputs['bundle']['tables'];tables=bundle['tables']
    if [r['payload_json'] for r in tables['documents']]!=[r['payload_json'] for r in old['documents']]:raise ValueError('DOCUMENT_SOURCE_MISMATCH')
    provisions={r['id']:json.loads(r['payload_json']) for r in tables['provisions']}
    raw_ids={r['id'] for r in old['provisions']}
    for row in old['provisions']:
        if provisions.get(row['id'])!=json.loads(row['payload_json']) or granularity[row['id']]['granularity']!='raw_page':raise ValueError('RAW_PAGE_MISMATCH')
    sources={(e['source']['document_id'],e['source']['version_id']):e for e in inputs['source_evidence']}
    structural=mapping['structural_subspans'];seen=set()
    for span in structural:
        p=provisions[span['citation_id']];e=sources[(p['document_id'],p['version_id'])];b=e['extraction']
        if p['citation_id'] in raw_ids or p['citation_id'] in seen:raise ValueError('STRUCTURAL_ID_COLLISION')
        seen.add(p['citation_id'])
        if b['rawtext'][p['start']:p['end']]!=p['text'] or not 0<=p['start']<p['end']<=len(b['rawtext']):raise ValueError('STRUCTURAL_SOURCE_MISMATCH')
        for key in ('citation_id','document_id','version_id','provision_id','start','end'):
            if span[key]!=p[key]:raise ValueError('STRUCTURAL_MAP_MISMATCH')
        if span['original_sha256']!=e['source']['sha256'] or span['rawtext_sha256']!=b['rawtext_sha256'] or span['text_sha256']!=hashlib.sha256(p['text'].encode()).hexdigest():raise ValueError('STRUCTURAL_HASH_MISMATCH')
        label=granularity[p['citation_id']]
        if label['granularity']!='structural_provision' or label['annotation']['parent_citation_id']!=span['parent_citation_id'] or span['human_gold'] is not False:raise ValueError('ANNOTATION_MAPPING_MISMATCH')
    if raw_ids|seen!=set(provisions) or set(granularity)!=set(provisions):raise ValueError('PROVISION_COVERAGE_MISMATCH')
    if (mapping['raw_page_count'],mapping['structural_provision_count'],mapping['total_provisions'])!=(len(raw_ids),len(seen),len(provisions)):raise ValueError('MAPPING_COUNT_MISMATCH')
    catalog=ScopedCatalog(bundle,contexts,table_prefix=config['table_prefix'])
    references=[dict(context_id=c['context_id'],context=c,**p) for c in contexts for p in catalog.references(c).values()]
    if references!=json.loads(artifact('reference-queries.json')):raise ValueError('REFERENCE_QUERY_MISMATCH')
    return config,bundle,mapping,catalog


class RuntimeBinding:
    def __init__(self,config,bundle,mapping,catalog,dependencies):
        self._config=deepcopy(config);self._mapping=deepcopy(mapping);self._catalog=catalog;self._dependencies=dependencies
        self._genie_snapshot=bundle['snapshot_hash'];self._rag_snapshot=mapping['rag_snapshot']
        self._hashes={config['table_prefix']+'.'+t:digest(rows) for t,rows in bundle['tables'].items()}
        self._adapter=None

    @property
    def genie_snapshot(self):return self._genie_snapshot

    @property
    def rag_snapshot(self):return self._rag_snapshot

    @property
    def mapping_sha256(self):return self._mapping['mapping_sha256']

    @property
    def contexts(self):return deepcopy(self._config['contexts'])

    @property
    def snapshot_map(self):return deepcopy(self._mapping)

    def readiness(self):
        missing=[];d=self._dependencies
        for field in ('space_id','warehouse_id'):
            if not isinstance(self._config.get(field),str) or not self._config[field].strip():missing.append(field+'_pending')
        if not isinstance(d,ServerDependencies):missing.append('server_dependencies_pending')
        elif d.genie is None or d.query_history is None or type(d.executor_id) is not int or not callable(d.permission_probe) or (d.delta_publication is None and not callable(d.publication_lookup)):missing.append('server_dependencies_incomplete')
        return {'available':not missing,'status':'unavailable' if missing else 'configured_pending_remote_verification',
                'reasons':missing,'remote_verified':False,'publication_verified':False,'assurance_profile':d.delta_publication.assurance_profile if isinstance(d,ServerDependencies) and d.delta_publication is not None else 'interval_v1','genie_snapshot':self.genie_snapshot,
                'rag_snapshot':self.rag_snapshot,'mapping_sha256':self._mapping['mapping_sha256'],
                'meaning':'Availability describes configured server capabilities; grants, running warehouse and publication require per-request independent checks.'}

    def ask_scoped(self,question,*,context):
        rejected={'status':'unavailable','scope_verified':False,'rows':[],'snapshot':self.genie_snapshot,
                  'rag_snapshot':self.rag_snapshot,'mapping_sha256':self._mapping['mapping_sha256']}
        try:plans=self._catalog.references(context)
        except Exception:return {**rejected,'status':'conflict','reason':'CONTEXT_NOT_REGISTERED'}
        ready=self.readiness()
        if not ready['available']:return {**rejected,'reason':'CONFIGURATION_PENDING','readiness':ready}
        d=self._dependencies
        delta=d.delta_publication.for_request() if d.delta_publication is not None else None
        # No Genie call until an independent store proves current publication.
        # Hash profile is digest(sorted curated row objects); publishing backend
        # must calculate it from actual full-table readback, never echo this map.
        table=next(iter(plans.values()))['source_tables'];stamp=int(time.time()*1000)
        try:
            if delta is not None:
                delta.verify(source_tables=table,started_at_ms=stamp,ended_at_ms=stamp,
                    executor_id=d.executor_id,warehouse_id=self._config['warehouse_id'],space_id=self._config['space_id'])
            else:
                cert=d.publication_lookup(source_tables=deepcopy(table),started_at_ms=stamp,ended_at_ms=stamp)
                if (not isinstance(cert,dict) or cert.get('snapshot')!=self.genie_snapshot or cert.get('source_tables')!=table
                    or cert.get('table_content_sha256')!={t:self._hashes[t] for t in table}
                    or not isinstance(cert.get('attestation_id'),str) or not cert['attestation_id']
                    or type(cert.get('valid_from_ms')) is not int or type(cert.get('valid_until_ms')) is not int
                    or not cert['valid_from_ms']<=stamp<=cert['valid_until_ms']):return {**rejected,'reason':'PUBLICATION_NOT_VERIFIED'}
            if self._adapter is None or (delta is not None and delta.assurance_profile=='trusted_admin_observed_v1'):
                probe=DatabricksHistoryProbe(d.query_history,warehouse_id=self._config['warehouse_id'],space_id=self._config['space_id'],
                    executor_id=d.executor_id,snapshot=self.genie_snapshot,table_content_sha256=self._hashes,publication_lookup=d.publication_lookup,delta_publication=delta)
                adapter=GenieAdapter(d.genie,self._config,d.permission_probe,scope_catalog=self._catalog,execution_probe=probe)
                if delta is None or delta.assurance_profile!='trusted_admin_observed_v1':self._adapter=adapter
            else:adapter=self._adapter
            result=adapter.ask_scoped(question,context=context)
            if delta is not None and delta.assurance_profile=='trusted_admin_observed_v1':
                result={**result,'assurance_profile':delta.assurance_profile,
                    'assurance':deepcopy(result.get('execution_provenance',{}).get('access_assurance')),
                    'limitations':result.get('limitations',[])+['Trusted administrators and supervised maintenance are operational assumptions; observed pre/post equality does not prove continuity or prevent ABA.']}
            return {**result,'rag_snapshot':self.rag_snapshot,'mapping_sha256':self._mapping['mapping_sha256']}
        except PermissionError:return {**rejected,'status':'denied','reason':'SERVER_EVIDENCE_ACCESS_DENIED'}
        except Exception:return {**rejected,'reason':'SERVER_EVIDENCE_UNAVAILABLE'}


def load_runtime_binding(root,config_path='config/genie-pilot-002.json',*,dependencies=None,expected_config_sha256=None):
    """Verify local export once. No SDK, permission or certificate calls on load.

    expected_config_sha256 is an optional independently pinned deployment digest.
    Without it config trust is the controlled server filesystem, never a request.
    """
    root=Path(root).resolve()
    try:config,bundle,mapping,catalog=_load(root,config_path,expected_config_sha256)
    except Exception as exc:
        if isinstance(exc,ValueError) and str(exc) in {'CONFIG_PIN_MISMATCH'}:raise
        raise ValueError('GENIE_LOCAL_EXPORT_INVALID') from None
    if isinstance(dependencies,ServerDependencies) and dependencies.delta_publication is not None:
        from .delta import DeltaPublication
        if not isinstance(dependencies.delta_publication,DeltaPublication):raise ValueError('DELTA_CAPABILITY_REQUIRED')
        dependencies.delta_publication.validate_local(config,bundle,mapping)
        catalog=ScopedCatalog(bundle,config['contexts'],table_prefix=config['table_prefix'],delta_versions=dependencies.delta_publication.versions)
    return RuntimeBinding(config,bundle,mapping,catalog,dependencies)
