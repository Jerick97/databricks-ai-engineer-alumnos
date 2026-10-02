"""Server-only Delta publication capability. No remote implementation or SQL calls.

Registry and governance callbacks must read independently provisioned evidence.
They are trust boundaries, not factories for echoing expected values. A certificate
hash identifies bytes, not a trusted publisher or permission grant.
"""
from dataclasses import dataclass, replace
from copy import deepcopy
from . import TABLES, digest
from .publication import Certificate, validate_certificate, require, STRICT_IDENTITY_PROFILE, NAMED_IDENTITY_PROFILE, REPLAY_IDENTITY_PROFILE, identity_profile_check


@dataclass(frozen=True)
class DeltaPublication:
    certificate: Certificate
    certificate_sha256: str
    mapping_sha256: str
    registry_lookup: object
    identity_access_probe: object
    assurance_profile: str = 'strict_interval_v1'
    certificate_identity_profile: str = STRICT_IDENTITY_PROFILE

    def __post_init__(self):
        from .governance import PROFILE,TrustedAdminObservedProbe
        identity_profile_check(self.certificate_identity_profile)
        if self.certificate_identity_profile in (NAMED_IDENTITY_PROFILE,REPLAY_IDENTITY_PROFILE):require(self.assurance_profile==PROFILE,'NAMED_IDENTITY_ASSURANCE_REQUIRED')
        require(self.assurance_profile in ('strict_interval_v1',PROFILE),'ASSURANCE_PROFILE_INVALID')
        if self.assurance_profile==PROFILE:require(isinstance(self.identity_access_probe,TrustedAdminObservedProbe),'OBSERVED_PROFILE_CAPABILITY_REQUIRED')
        p=validate_certificate(self.certificate,identity_profile=self.certificate_identity_profile)
        require(p['evidence_mode']=='real','REAL_PUBLICATION_REQUIRED')
        require(self.certificate.sha256==self.certificate_sha256,'CERTIFICATE_PIN_MISMATCH')
        require(isinstance(self.mapping_sha256,str) and len(self.mapping_sha256)==64
                and all(c in '0123456789abcdef' for c in self.mapping_sha256),'MAPPING_PIN_REQUIRED')
        require(callable(self.registry_lookup) and callable(self.identity_access_probe),'DELTA_SERVER_CAPABILITIES_REQUIRED')

    def for_request(self):
        if self.assurance_profile=='trusted_admin_observed_v1':
            return replace(self,identity_access_probe=self.identity_access_probe.new_session())
        return self

    @property
    def versions(self):return {t['full_name']:t['delta_version'] for t in self.certificate.as_dict()['tables']}

    def validate_local(self,config,bundle,mapping):
        p=validate_certificate(self.certificate,identity_profile=self.certificate_identity_profile)
        require(p['snapshot']==bundle['snapshot_hash'] and p['config_hash']==bundle['config_hash']
                and self.mapping_sha256==mapping['mapping_sha256'],'DELTA_LOCAL_PIN_MISMATCH')
        expected={config['table_prefix']+'.'+t:(digest(bundle['tables'][t]),len(bundle['tables'][t])) for t in TABLES}
        observed={t['full_name']:(t['content_sha256'],t['row_count']) for t in p['tables']}
        require(expected==observed,'DELTA_LOCAL_CONTENT_MISMATCH')

    def verify(self,*,source_tables,started_at_ms,ended_at_ms,executor_id,warehouse_id,space_id):
        p=self.certificate.as_dict()
        require(type(started_at_ms) is int and type(ended_at_ms) is int and 0<=started_at_ms<=ended_at_ms,'DELTA_INTERVAL_INVALID')
        selected=[t for t in p['tables'] if t['full_name'] in source_tables]
        require(len(source_tables)==1 and [t['full_name'] for t in selected]==source_tables,'DELTA_TABLE_OUTSIDE_PUBLICATION')
        # Registry checks trust/revocation separately from immutable certificate.
        r=self.registry_lookup(certificate_sha256=self.certificate_sha256)
        require(isinstance(r,dict) and r.get('certificate_sha256')==self.certificate_sha256
                and r.get('mapping_sha256')==self.mapping_sha256 and r.get('status')=='active'
                and r.get('evidence_mode')=='real' and r.get('readback_execution_verified') is True
                and isinstance(r.get('publisher_identity'),str) and bool(r['publisher_identity'])
                and isinstance(r.get('attestation_id'),str) and bool(r['attestation_id']), 'DELTA_REGISTRY_NOT_VERIFIED')
        require(r.get('identity_profile',STRICT_IDENTITY_PROFILE)==self.certificate_identity_profile,'DELTA_REGISTRY_IDENTITY_PROFILE_MISMATCH')
        # Temporal coverage here attests identity/access governance, NOT no DML.
        def covers(value):
            return (type(value.get('valid_from_ms')) is int and type(value.get('valid_until_ms')) is int
                    and value['valid_from_ms']<=started_at_ms<=ended_at_ms<=value['valid_until_ms'])
        require(covers(r),'DELTA_REGISTRY_EXPIRED')
        # The v2 reader records submitted SQL, not observed execution identity.
        # Require the trusted registry to supply independently observed history
        # for every readback statement before that certificate is usable live.
        executions=r.get('readback_executions')
        proofs=[proof for t in p['tables'] for proof in t['evidence']]
        require(isinstance(r.get('publisher_warehouse_id'),str) and bool(r['publisher_warehouse_id'])
                and type(r.get('publisher_executor_id')) is int
                and isinstance(executions,list) and len(executions)==len(proofs),'DELTA_READBACK_HISTORY_REQUIRED')
        seen=set()
        for proof,observed in zip(proofs,executions):
            require(isinstance(observed,dict) and observed.get('statement_id')==proof['statement_id']
                    and observed.get('statement_id') not in seen
                    and observed.get('observed_sql_sha256')==proof['sql_sha256']
                    and observed.get('warehouse_id')==r['publisher_warehouse_id']
                    and type(observed.get('executor_id')) is int and observed['executor_id']==r['publisher_executor_id']
                    and observed.get('status')=='FINISHED' and observed.get('is_final') is True
                    and not observed.get('cache_query_id') and not observed.get('error_message')
                    and type(observed.get('started_at_ms')) is int and type(observed.get('ended_at_ms')) is int
                    and 0<=observed['started_at_ms']<=observed['ended_at_ms']<=r['valid_from_ms']
                    and isinstance(observed.get('history_record_sha256'),str) and len(observed['history_record_sha256'])==64
                    and all(c in '0123456789abcdef' for c in observed['history_record_sha256']), 'DELTA_READBACK_HISTORY_NOT_VERIFIED')
            seen.add(observed['statement_id'])
        evidence=self.identity_access_probe(source_tables=deepcopy(source_tables),executor_id=executor_id,
            warehouse_id=warehouse_id,space_id=space_id,started_at_ms=started_at_ms,ended_at_ms=ended_at_ms)
        if self.assurance_profile=='trusted_admin_observed_v1':
            expected=[{k:t[k] for k in ('full_name','uc_table_id','metastore_id','location_sha256')} for t in selected]
            observed=[{k:t.get(k) for k in expected[0]} for t in evidence['observation']['tables']]
            require(digest(expected)==digest(observed),'DELTA_IDENTITY_NOT_VERIFIED')
            return dict(publication_mode='delta_version',publication_certificate_sha256=self.certificate_sha256,
                publication_attestation_id=r['attestation_id'],publication_registry_sha256=digest(r),
                identity_access_evidence_sha256=digest(evidence),assurance_profile=self.assurance_profile,
                access_assurance=evidence,publication_table_bindings=selected,
                identity_continuity='not_proven',aba_prevented=False,**({'publication_evidence_origin':'replay_existing_statements','select_bracketed_by_detail':False} if self.certificate_identity_profile==REPLAY_IDENTITY_PROFILE else {}),**({'certificate_identity_profile':self.certificate_identity_profile,'physical_location_relation_observed':False} if self.certificate_identity_profile in (NAMED_IDENTITY_PROFILE,REPLAY_IDENTITY_PROFILE) else {}))
        require(isinstance(evidence,dict) and evidence.get('evidence_mode')=='real' and covers(evidence)
                and evidence.get('executor_id')==executor_id and type(evidence.get('executor_id')) is int
                and evidence.get('warehouse_id')==warehouse_id and evidence.get('space_id')==space_id
                and isinstance(evidence.get('evidence_id'),str) and bool(evidence['evidence_id'])
                and all(evidence.get(k) is True for k in ('select_authorized','backend_select_only','ddl_identity_controlled','retention_controlled','policies_absent')),
                'DELTA_GOVERNANCE_NOT_VERIFIED')
        fields=('full_name','uc_table_id','metastore_id','delta_table_id','location_sha256','delta_version','schema_sha256')
        expected=[{k:t[k] for k in fields} for t in selected]
        observed=evidence.get('tables')
        # Dict equality treats bool as int; canonical JSON preserves their type.
        require(digest(observed)==digest(expected),'DELTA_IDENTITY_NOT_VERIFIED')
        return dict(publication_mode='delta_version',publication_certificate_sha256=self.certificate_sha256,
            publication_attestation_id=r['attestation_id'],publication_registry_sha256=digest(r),
            identity_access_evidence_sha256=digest(evidence),table_bindings=expected,aba_prevented=False)
