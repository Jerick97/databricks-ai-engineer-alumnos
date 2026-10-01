"""Current GET observations under an explicit trusted-administrator pilot policy.

No historical continuity, ABA, Delta UUID GET or ABAC absence is inferred here.
The identity resolver is a server capability supplying observed relevant reader
memberships/roles, separate from policy. No SQL or permission/resource mutation.
"""
from dataclasses import dataclass
from copy import deepcopy
import time
from . import digest
from .publication import require

PROFILE='trusted_admin_observed_v1'


def _integer(v):return type(v) is int and v>=0
def _text(v):return isinstance(v,str) and bool(v)
def _obj(v):
    if not hasattr(v,'as_dict'):return v
    out=v.as_dict()
    # Generated SDK as_dict omits empty lists. Preserve typed fields only;
    # a raw dictionary missing required evidence is still incomplete.
    from databricks.sdk.service.catalog import EffectivePermissionsList
    from databricks.sdk.service.iam import ServicePrincipal,User
    if isinstance(v,EffectivePermissionsList) and isinstance(v.privilege_assignments,list):
        out.setdefault('privilege_assignments',[])
    if isinstance(v,(ServicePrincipal,User)) and isinstance(v.groups,list):
        out.setdefault('groups',[])
    return out


def _call(function,*args,**kwargs):
    try:return _obj(function(*args,**kwargs))
    except Exception as exc:
        if isinstance(exc,PermissionError) or getattr(exc,'error_code',None) in ('PERMISSION_DENIED','UNAUTHENTICATED'):
            raise PermissionError('GOVERNANCE_GET_DENIED') from None
        raise ValueError('GOVERNANCE_GET_UNAVAILABLE') from None


@dataclass(frozen=True)
class TrustedAdminPolicy:
    policy_id: str
    namespace: str
    trusted_administrators: tuple
    maintenance_assumption: str
    abac_assumption: str
    issued_at_ms: int
    expires_at_ms: int
    observation_ttl_ms: int
    status_lookup: object

    def __post_init__(self):
        require(_text(self.policy_id) and _text(self.namespace) and self.namespace.endswith('.sbs_radar'),'GOVERNANCE_POLICY_INVALID')
        require(type(self.trusted_administrators) is tuple and bool(self.trusted_administrators) and all(_text(x) for x in self.trusted_administrators)
                and _text(self.maintenance_assumption) and _text(self.abac_assumption),'ADMIN_ASSUMPTIONS_REQUIRED')
        require(_integer(self.issued_at_ms) and _integer(self.expires_at_ms) and self.issued_at_ms<self.expires_at_ms
                and _integer(self.observation_ttl_ms) and self.observation_ttl_ms>0 and callable(self.status_lookup),'GOVERNANCE_POLICY_INVALID')

    def assumptions(self):
        return dict(policy_id=self.policy_id,namespace=self.namespace,trusted_administrators=list(self.trusted_administrators),
                    maintenance=self.maintenance_assumption,abac=self.abac_assumption,
                    basis='server_operational_assumption_not_observed_history')


class UcAccessCollector:
    """SDK adapters: tables.get, grants.get_effective, warehouses.get_permissions.

    subject_resolver(executor_id=...) must observe relevant reader principal/group
    closure and roles, with provenance; it must never echo names from the request.
    Filtering grants by principal alone does not establish group closure.
    """
    def __init__(self,*,table_get,catalog_get,schema_get,effective_grants_get,warehouse_permissions_get,subject_resolver,clock=None,max_pages=4):
        require(all(callable(x) for x in (table_get,catalog_get,schema_get,effective_grants_get,warehouse_permissions_get,subject_resolver)),'UC_CAPABILITIES_REQUIRED')
        require(type(max_pages) is int and 1<=max_pages<=8,'UC_PAGINATION_CAP_INVALID')
        self.catalog_get=catalog_get;self.schema_get=schema_get
        self.table_get=table_get;self.grants=effective_grants_get;self.warehouse_permissions=warehouse_permissions_get
        self.subject_resolver=subject_resolver;self.clock=clock or (lambda:int(time.time()*1000));self.max_pages=max_pages

    def _grants(self,kind,name,subjects):
        token=None;seen=set();assignments=[]
        for _ in range(self.max_pages):
            kw=dict(securable_type=kind,full_name=name,max_results=0)
            if token is not None:kw['page_token']=token
            response=_call(self.grants,**kw)
            require(isinstance(response,dict) and isinstance(response.get('privilege_assignments'),list),'UC_GRANTS_INCOMPLETE')
            require(len(response['privilege_assignments'])<=1000,'UC_GRANTS_LIMIT')
            assignments.extend(response['privilege_assignments'])
            token=response.get('next_page_token')
            if token is None:break
            require(_text(token) and token not in seen,'UC_GRANTS_PAGINATION_INVALID');seen.add(token)
        else:raise ValueError('UC_GRANTS_PAGINATION_LIMIT')
        relevant=[];allowed={'CATALOG':{'USE_CATALOG','USE_SCHEMA','SELECT','BROWSE'},'SCHEMA':{'USE_SCHEMA','SELECT','BROWSE'},'TABLE':{'SELECT','BROWSE'}}[kind]
        found=set()
        for a in assignments:
            require(isinstance(a,dict) and _text(a.get('principal')) and isinstance(a.get('privileges'),list),'UC_GRANTS_INCOMPLETE')
            if a['principal'] not in subjects:continue
            for p in a['privileges']:
                require(isinstance(p,dict) and _text(p.get('privilege')),'UC_GRANTS_INCOMPLETE')
                privilege=p['privilege'];require(privilege in allowed,'READER_NOT_SELECT_ONLY')
                found.add(privilege)
            relevant.append(a)
        require({'CATALOG':'USE_CATALOG','SCHEMA':'USE_SCHEMA','TABLE':'SELECT'}[kind] in found,'UC_READER_GRANT_MISSING')
        return sorted(relevant,key=lambda a:digest(a))

    def collect(self,*,source_tables,executor_id,warehouse_id):
        start=self.clock();require(_integer(start) and type(executor_id) is int,'OBSERVATION_IDENTITY_INVALID')
        subject=_call(self.subject_resolver,executor_id=executor_id)
        require(isinstance(subject,dict) and type(subject.get('executor_id')) is int and subject['executor_id']==executor_id
                and subject.get('active') is True and subject.get('membership_complete') is True
                and isinstance(subject.get('principals'),list) and bool(subject['principals']) and all(_text(p) for p in subject['principals'])
                and isinstance(subject.get('roles'),list) and subject['roles']==[] and _text(subject.get('evidence_id'))
                and _integer(subject.get('observed_at_ms')) and subject.get('membership_scope')=='full_scim_resource_reported_groups', 'READER_MEMBERSHIP_NOT_VERIFIED')
        subjects=set(subject['principals']);require(not subjects.intersection({'admins','account admins'}),'ADMIN_READER_UNSUPPORTED')
        metadata=[];grants=[]
        for name in source_tables:
            parts=name.split('.');require(len(parts)==3,'UC_TABLE_NAME_INVALID')
            for parent,key,expected in ((_call(self.catalog_get,parts[0]),'name',parts[0]),(_call(self.schema_get,'.'.join(parts[:2])),'full_name','.'.join(parts[:2]))):
                require(isinstance(parent,dict) and parent.get(key)==expected and _text(parent.get('owner')) and parent['owner'] not in subjects,'PARENT_OWNER_NOT_VERIFIED')
            table=_call(self.table_get,name,include_delta_metadata=True,include_browse=False)
            require(isinstance(table,dict) and table.get('full_name')==name and table.get('table_type')=='MANAGED'
                    and table.get('data_source_format')=='DELTA' and table.get('browse_only') is not True
                    and all(_text(table.get(k)) for k in ('table_id','metastore_id','storage_location','owner')),'UC_BASE_TABLE_NOT_VERIFIED')
            require(table['owner'] not in subjects,'ADMIN_READER_UNSUPPORTED')
            require('columns' in table and isinstance(table['columns'],list) and table['columns']
                    and not table.get('row_filter') and all(isinstance(c,dict) and not c.get('mask') for c in table['columns']),'VISIBLE_TABLE_POLICY_UNSUPPORTED')
            metadata.append(dict(full_name=name,uc_table_id=table['table_id'],metastore_id=table['metastore_id'],location_sha256=__import__('hashlib').sha256(table['storage_location'].encode()).hexdigest(),
                table_type=table['table_type'],data_source_format=table['data_source_format'],owner=table['owner'],
                visible_policy_state='no_table_filter_or_mask_observed',metadata_sha256=digest(table)))
            for kind,full in [('CATALOG',parts[0]),('SCHEMA','.'.join(parts[:2])),('TABLE',name)]:
                grants.append(dict(kind=kind,name=full,assignments=self._grants(kind,full,subjects)))
        acl=_call(self.warehouse_permissions,warehouse_id);require(isinstance(acl,dict) and acl.get('object_id')=='/sql/warehouses/'+warehouse_id and acl.get('object_type')=='warehouses' and isinstance(acl.get('access_control_list'),list),'WAREHOUSE_ACL_INCOMPLETE')
        permissions=[]
        for a in acl['access_control_list']:
            require(isinstance(a,dict),'WAREHOUSE_ACL_INCOMPLETE')
            principal=next((a[k] for k in ('user_name','service_principal_name','group_name') if a.get(k)),None)
            if principal not in subjects:continue
            require(isinstance(a.get('all_permissions'),list),'WAREHOUSE_ACL_INCOMPLETE')
            for grant in a['all_permissions']:
                require(isinstance(grant,dict) and grant.get('permission_level')=='CAN_USE','READER_WAREHOUSE_PRIVILEGE_UNSUPPORTED')
                permissions.append(grant)
        require(bool(permissions),'WAREHOUSE_CAN_USE_NOT_VERIFIED')
        end=self.clock();require(_integer(end) and end>=start and subject['observed_at_ms']<=end,'OBSERVATION_CLOCK_INVALID')
        return dict(observed_from_ms=start,observed_until_ms=end,subject=deepcopy(subject),tables=metadata,grants=grants,
                    warehouse_permissions=permissions,warehouse_acl_sha256=digest(acl),source='databricks_current_get',
                    policy_visibility='table_filters_and_masks_only_abac_not_observed')


class TrustedAdminObservedProbe:
    """Factory/session for exactly one pre/post request, no lease or epochs.

    new_session isolates concurrent requests. Equality detects observed drift;
    it does not prove continuity between observations or prevent ABA.
    """
    def __init__(self,collector,policy,*,_session=False):
        require(isinstance(collector,UcAccessCollector) and isinstance(policy,TrustedAdminPolicy),'OBSERVED_PROFILE_CAPABILITIES_REQUIRED')
        self.collector=collector;self.policy=policy;self._session=_session;self._before=None

    def new_session(self):return TrustedAdminObservedProbe(self.collector,self.policy,_session=True)

    def __call__(self,*,source_tables,executor_id,warehouse_id,space_id,started_at_ms,ended_at_ms):
        require(self._session,'OBSERVED_REQUEST_SESSION_REQUIRED')
        require(_integer(started_at_ms) and _integer(ended_at_ms) and started_at_ms<=ended_at_ms,'OBSERVED_INTERVAL_INVALID')
        require(len(source_tables)==1 and source_tables[0].rsplit('.',1)[0]==self.policy.namespace,'OBSERVED_NAMESPACE_MISMATCH')
        now=self.collector.clock();require(_integer(now) and self.policy.issued_at_ms<=now<=self.policy.expires_at_ms,'ADMIN_POLICY_EXPIRED')
        require(_call(self.policy.status_lookup,policy_id=self.policy.policy_id)=='active','ADMIN_POLICY_REVOKED')
        observation=self.collector.collect(source_tables=source_tables,executor_id=executor_id,warehouse_id=warehouse_id)
        end=observation['observed_until_ms']
        require(_call(self.policy.status_lookup,policy_id=self.policy.policy_id)=='active','ADMIN_POLICY_REVOKED')
        require(end<=self.policy.expires_at_ms and end-observation['subject']['observed_at_ms']<=self.policy.observation_ttl_ms
                and end-observation['observed_from_ms']<=self.policy.observation_ttl_ms,'OBSERVATION_EXPIRED')
        # Stable values only; current schema hash is retained as observation but
        # is not compared against historical schema from the publication.
        stable={k:observation[k] for k in ('tables','grants','warehouse_permissions')}
        stable['principals']=sorted(observation['subject']['principals']);stable['roles']=observation['subject']['roles']
        current=digest(stable);phase='before' if self._before is None else 'after'
        if self._before is None:self._before=(current,source_tables,executor_id,warehouse_id,space_id,end)
        else:
            require(self._before[:5]==(current,source_tables,executor_id,warehouse_id,space_id),'OBSERVED_PRE_POST_CHANGED')
            require(self._before[5]<=started_at_ms<=ended_at_ms<=observation['observed_from_ms'],'OBSERVATIONS_DO_NOT_BRACKET_EXECUTION')
            require(end-self._before[5]<=self.policy.observation_ttl_ms,'OBSERVATION_EXPIRED')
        return dict(assurance_profile=PROFILE,evidence_mode='real',evidence_id=digest(observation),executor_id=executor_id,
            warehouse_id=warehouse_id,space_id=space_id,phase=phase,observation=observation,assumptions=self.policy.assumptions(),
            select_authorized_observed=True,backend_select_only_observed=True,identity_continuity='not_proven',aba_prevented=False,
            limitations=['Current GET observations and trusted administrator assumptions, not historical continuity.',
                         'ABAC absence is an administrative assumption; table policy observation is narrower.',
                         'TTL is freshness policy, not retention guarantee.'])


class ScimReaderResolver:
    """Observe a full SCIM reader resource and resolve its reported groups.

    No selected attributes or list truncation. Scope is groups reported by that
    resource, including reported indirect memberships; not all account roles or
    a claim that no hidden administrator exists. Never alias group names.
    """
    def __init__(self,identity_get,group_get,*,kind='service_principal',clock=None,max_groups=100):
        require(callable(identity_get) and callable(group_get) and kind in ('service_principal','user'),'SCIM_CAPABILITIES_REQUIRED')
        require(type(max_groups) is int and 1<=max_groups<=1000,'SCIM_GROUP_CAP_INVALID')
        self.identity_get=identity_get;self.group_get=group_get;self.kind=kind;self.clock=clock or (lambda:int(time.time()*1000));self.max_groups=max_groups

    def __call__(self,*,executor_id):
        require(_integer(executor_id),'SCIM_ID_INVALID')
        identity=_call(self.identity_get,str(executor_id))
        require(isinstance(identity,dict) and identity.get('id')==str(executor_id) and identity.get('active') is True
                and isinstance(identity.get('groups'),list) and len(identity['groups'])<=self.max_groups,'SCIM_READER_INCOMPLETE')
        key='application_id' if self.kind=='service_principal' else 'user_name'
        rawkey='applicationId' if self.kind=='service_principal' else 'userName'
        name=identity.get(key,identity.get(rawkey));require(_text(name),'SCIM_PRINCIPAL_NAME_REQUIRED')
        names=[name];groups=[];ids=set()
        for ref in identity['groups']:
            require(isinstance(ref,dict) and _text(ref.get('value')) and ref['value'] not in ids,'SCIM_GROUP_REFERENCE_INVALID');ids.add(ref['value'])
            group=_call(self.group_get,ref['value'])
            require(isinstance(group,dict) and group.get('id')==ref['value'],'SCIM_GROUP_UNRESOLVED')
            display=group.get('display_name',group.get('displayName'))
            require(_text(display) and (not ref.get('display') or ref['display']==display),'SCIM_GROUP_NAME_MISMATCH')
            names.append(display);groups.append(group)
        roles=identity.get('roles',[])
        require(isinstance(roles,list) and all(isinstance(r,dict) and _text(r.get('value')) for r in roles),'SCIM_ROLE_INVALID')
        now=self.clock();require(_integer(now),'SCIM_CLOCK_INVALID')
        return dict(executor_id=executor_id,active=True,principals=names,roles=[r['value'] for r in roles],
            role_visibility='reported_roles_only' if 'roles' in identity else 'roles_not_reported',
            membership_complete=True,membership_scope='full_scim_resource_reported_groups',observed_at_ms=now,
            evidence_id=digest(dict(identity=identity,resolved_reported_groups=groups)),
            source='databricks_scim_full_resource_get',limitations=['Reported memberships only; no hidden-account-role absence claim.'])
