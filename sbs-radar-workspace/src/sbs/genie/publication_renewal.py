"""Server-only, append-only renewal of an expired publication window.

No authorization is generated here. The injected authorize capability must run
normal human-authorization admission and return the admitted WriterConfig.
Hashes record provenance, not authentication. Trusted journal and budget paths
are deployment capabilities, never HTTP input. All operations share writer lock.
"""
from dataclasses import asdict
from pathlib import Path
import fcntl,json,os,uuid
from . import canonical,digest
from .publication import require
from .publication_registry import _directory,_read,_append


def _bound(config):return dict(plan_sha256=config.plan_sha256,config_sha256=digest(asdict(config)))
def _get(fd,name):return json.loads(_read(fd,name))
def _hash(value):return isinstance(value,str) and len(value)==64 and all(c in '0123456789abcdef' for c in value)


def _pair(old,new):
    from .publication_writer import WriterConfig
    require(isinstance(old,WriterConfig) and isinstance(new,WriterConfig),'RENEWAL_CONFIG_REQUIRED')
    # Revalidate even a mutated dict inside the frozen dataclass.
    old=WriterConfig(**asdict(old));new=WriterConfig(**asdict(new))
    a=asdict(old);b=asdict(new)
    for value in (a,b):
        value['policy']={k:v for k,v in value['policy'].items() if k not in ('issued_at_ms','expires_at_ms')}
    require(canonical(a)==canonical(b),'RENEWAL_SCOPE_CHANGED')
    require(new.policy['issued_at_ms']>=old.policy['expires_at_ms'] and new.policy['expires_at_ms']>old.policy['expires_at_ms'],'RENEWAL_WINDOW_INVALID')


def _series(fd,prefix):
    names=sorted(n for n in os.listdir(fd) if n.startswith(prefix))
    require(len(names)<=112,'RENEWAL_CHAIN_CAP')
    require(names==[f'{prefix}{i:06d}.json' for i in range(1,len(names)+1)],'RENEWAL_CHAIN_GAP_OR_BRANCH')
    return [_get(fd,n) for n in names]


def _budget(value):
    require(isinstance(value,dict) and set(value)=={'limit','reserved','prior_sql_evidence','submissions'},'SQL_BUDGET_INVALID')
    require(type(value['limit']) is int and value['limit']==112 and type(value['reserved']) is int
            and 3<=value['reserved']<=112 and isinstance(value['submissions'],list)
            and len(value['submissions'])==value['reserved']-3
            and isinstance(value['prior_sql_evidence'],str) and value['prior_sql_evidence'],'SQL_BUDGET_INVALID')
    require(all(isinstance(s,dict) and _hash(s.get('statement_sha256')) for s in value['submissions']),'SQL_BUDGET_INVALID')
    return value


def effective_binding(fd):
    """Validate full lineage without rewriting the original binding."""
    try:binding=_get(fd,'binding.json')
    except FileNotFoundError:
        require(not _series(fd,'window-renewal-'),'RENEWAL_BINDING_MISSING');return None,None
    records=_series(fd,'window-renewal-');previous=None;first=None
    from .publication_writer import WriterConfig
    for r in records:
        require(set(r)=={'version','old_binding','new_binding','old_config','new_config','previous_sha256','authorization_sha256','at_ms','budget_path','budget','budget_sha256'},'RENEWAL_RECORD_INVALID')
        require(type(r['version']) is int and r['version']==1 and r['previous_sha256']==previous and r['old_binding']==binding,'RENEWAL_CHAIN_CONFLICT')
        old=WriterConfig(**r['old_config']);new=WriterConfig(**r['new_config']);_pair(old,new)
        require(r['old_binding']==_bound(old) and r['new_binding']==_bound(new) and _hash(r['authorization_sha256']),'RENEWAL_RECORD_INVALID')
        require(type(r['at_ms']) is int and new.policy['issued_at_ms']<=r['at_ms']<new.policy['expires_at_ms'],'RENEWAL_RECORD_TIME_INVALID')
        _budget(r['budget']);require(digest(r['budget'])==r['budget_sha256'],'SQL_BUDGET_MISMATCH')
        path=Path(r['budget_path']);require(path.is_absolute() and '..' not in path.parts,'SQL_BUDGET_PATH_INVALID')
        if first is None:first=r
        else:require(r['budget_path']==first['budget_path'],'SQL_BUDGET_PATH_CHANGED')
        binding=r['new_binding'];previous=digest(r)
    if records:
        states=_budget_states(fd,first)
        require(all(r['budget'] in states for r in records),'SQL_BUDGET_LINEAGE_MISMATCH')
        _current_budget(first,states[-1])
    return binding,records[-1] if records else None


def _budget_states(fd,first):
    states=[first['budget']]
    for r in _series(fd,'sql-reservation-'):
        require(set(r)=={'before_sha256','after'} and r['before_sha256']==digest(states[-1]),'SQL_BUDGET_CHAIN_CONFLICT')
        after=_budget(r['after']);before=states[-1]
        require(after['limit']==before['limit'] and after['prior_sql_evidence']==before['prior_sql_evidence']
                and after['reserved']==before['reserved']+1 and after['submissions'][:-1]==before['submissions'],'SQL_BUDGET_RESET_OR_DRIFT')
        states.append(after)
    return states


def _current_budget(first,expected):
    path=Path(first['budget_path']);fd=_directory(path.parent,False)
    try:require(_budget(_get(fd,path.name))==expected,'SQL_BUDGET_RESET_OR_DRIFT')
    finally:os.close(fd)


def renew_policy_window(plan,old_config,new_config,journal,*,budget_path,expected_budget_sha256,authorize,authorization_sha256,clock):
    """Local migration only; explicit admitted new config, same plan and budget.

    Returns persisted lineage; repeat/branch attempts reject. Does not alter
    binding, mutation records, budget, table state, or authorization files.
    """
    from .publication_writer import preflight
    _pair(old_config,new_config);preflight(plan,old_config);preflight(plan,new_config)
    require(callable(authorize) and callable(clock) and _hash(authorization_sha256),'RENEWAL_ADMISSION_REQUIRED')
    path=Path(budget_path).absolute();require('..' not in path.parts,'SQL_BUDGET_PATH_INVALID')
    fd=_directory(journal,False)
    try:
        fcntl.flock(fd,fcntl.LOCK_EX)
        binding,prior=effective_binding(fd)
        require(binding==_bound(old_config),'JOURNAL_BINDING_MISMATCH')
        if prior:require(str(path)==prior['budget_path'],'SQL_BUDGET_PATH_CHANGED')
        bf=_directory(path.parent,False)
        try:budget=_budget(_get(bf,path.name))
        finally:os.close(bf)
        require(digest(budget)==expected_budget_sha256,'SQL_BUDGET_MISMATCH')
        admitted=authorize()
        require(type(admitted) is type(new_config) and canonical(asdict(admitted))==canonical(asdict(new_config)),'RENEWAL_ADMISSION_MISMATCH')
        now=clock();require(type(now) is int and new_config.policy['issued_at_ms']<=now<new_config.policy['expires_at_ms'],'RENEWAL_WINDOW_EXPIRED')
        records=_series(fd,'window-renewal-')
        r=dict(version=1,old_binding=binding,new_binding=_bound(new_config),old_config=asdict(old_config),new_config=asdict(new_config),previous_sha256=digest(prior) if prior else None,authorization_sha256=authorization_sha256,at_ms=now,budget_path=str(path),budget=budget,budget_sha256=digest(budget))
        _append(fd,f'window-renewal-{len(records)+1:06d}.json',canonical(r).encode())
        return r
    finally:
        fcntl.flock(fd,fcntl.LOCK_UN);os.close(fd)


class CumulativeStatements:
    """Reserve before every SQL under the writer's journal lock. No retries.

    Durable reservation precedes ledger replacement. A crash between them blocks
    rather than guessing or refunding; manual reviewed reconciliation is required.
    Initial three observed050 SQL and cap112 remain fixed across renewals.
    """
    def __init__(self,delegate,journal_fd):self.delegate=delegate;self.fd=journal_fd
    def execute_statement(self,**kwargs):
        _,latest=effective_binding(self.fd);require(latest is not None,'RENEWAL_BINDING_MISSING')
        records=_series(self.fd,'window-renewal-');states=_budget_states(self.fd,records[0]);before=states[-1]
        require(before['reserved']<before['limit'],'TOTAL_SQL_CAP')
        after=json.loads(canonical(before));after['reserved']+=1
        import hashlib
        after['submissions'].append({'statement_sha256':hashlib.sha256(kwargs['statement'].encode()).hexdigest()})
        _append(self.fd,f'sql-reservation-{len(states):06d}.json',canonical(dict(before_sha256=digest(before),after=after)).encode())
        path=Path(latest['budget_path']);fd=_directory(path.parent,False);temp='.pending-budget-'+uuid.uuid4().hex
        try:
            f=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=fd)
            with os.fdopen(f,'wb') as stream:stream.write(canonical(after).encode());stream.flush();os.fsync(stream.fileno())
            os.replace(temp,path.name,src_dir_fd=fd,dst_dir_fd=fd);os.fsync(fd)
        finally:os.close(fd)
        return self.delegate.execute_statement(**kwargs)
    def __getattr__(self,name):return getattr(self.delegate,name)
